# FICHIER: app/api/mcp_routes.py
from fastapi import APIRouter, Request, Depends, HTTPException, BackgroundTasks, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse
from pydantic import ValidationError, BaseModel
from sqlalchemy.orm import Session
import logging
import time
from typing import Optional, Dict, Any, List, Union
import copy
import asyncio
import uuid
import random
import json
from pathlib import Path
from urllib.parse import urlparse
import aiohttp
import base64

from ..schemas import (
    JsonRpcRequest, JsonRpcResponse, JsonRpcError, ToolCallParams,
    GenerateImageParams, UpscaleImageParams, DescribeImageParams, GeneratePromptParams,
    GENERATE_IMAGE_TOOL_SCHEMA, UPSCALE_IMAGE_TOOL_SCHEMA, DESCRIBE_IMAGE_TOOL_SCHEMA,
    PROMPT_GENERATOR_TOOL_SCHEMA,
    JsonRpcId, GenerationLogCreate
)
from ..services.comfyui_client import ComfyUIClient, ComfyUIError, ComfyUIConnectionError
from ..services.ollama_client import OllamaClient, OllamaError
from ..database.session import get_db, SessionLocal
from ..database import crud
from ..config import settings
from ..database.models import ComfyUIInstance, Style

logger = logging.getLogger(__name__)
router = APIRouter()

ASPECT_RATIOS = {
    "1:1": (1024, 1024), "16:9": (1344, 768), "9:16": (768, 1344),
    "4:3": (1152, 896), "3:4": (896, 1152)
}
DEFAULT_ASPECT_RATIO = (1024, 1024)

# --- WebSocket Connection Manager ---

class WebSocketManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
    async def connect(self, stream_id: str, websocket: WebSocket):
        await websocket.accept()
        self.active_connections[stream_id] = websocket
    def disconnect(self, stream_id: str):
        if stream_id in self.active_connections: del self.active_connections[stream_id]
    async def send_mcp_message(self, stream_id: str, message: dict):
        if stream_id in self.active_connections:
            try:
                await self.active_connections[stream_id].send_json(message)
            except Exception as e:
                logger.error(f"Failed to send WS message to {stream_id}: {e}")
                self.disconnect(stream_id)

manager = WebSocketManager()

@router.websocket("/ws/stream/{stream_id}")
async def websocket_endpoint(websocket: WebSocket, stream_id: str):
    await manager.connect(stream_id, websocket)
    try:
        while True: await websocket.receive_text()
    except WebSocketDisconnect:
        logger.info(f"Client for stream_id {stream_id} disconnected.")
    finally:
        manager.disconnect(stream_id)

# --- Helper Functions for Background Tasks ---

def _find_node_id_by_title(workflow: dict, title: str) -> Optional[str]:
    for node_id, node_data in workflow.items():
        if node_data.get("_meta", {}).get("title") == title: return node_id
    return None

async def _select_best_comfyui_instance(db: Session, render_type_name: Optional[str]) -> ComfyUIInstance:
    active_instances = crud.get_all_active_comfyui_instances(db)
    if not active_instances: raise ValueError("No active ComfyUI servers configured.")
    
    compatible_instances = [
        inst for inst in active_instances 
        if not render_type_name or any(rt.name == render_type_name for rt in inst.compatible_render_types)
    ]
    if not compatible_instances: raise ValueError(f"No active server is compatible with '{render_type_name}'.")

    async def get_queue_size(instance):
        client = ComfyUIClient(api_url=instance.base_url, generation_timeout=10)
        try:
            return (instance, await client.get_queue_size())
        except ComfyUIConnectionError:
            return (instance, float('inf'))

    queue_sizes = await asyncio.gather(*(get_queue_size(inst) for inst in compatible_instances))
    valid_queues = [qs for qs in queue_sizes if qs[1] != float('inf')]
    if not valid_queues: raise ValueError("Could not connect to any compatible ComfyUI servers.")
    
    selected_instance, _ = min(valid_queues, key=lambda item: item[1])
    logger.info(f"Selected instance '{selected_instance.name}' for the task.")
    return selected_instance

def _log_generation_result(db: Session, log_data: Dict[str, Any]):
    try:
        crud.create_generation_log(db, log=GenerationLogCreate(**log_data))
    except Exception as e:
        logger.error(f"!!! CRITICAL: FAILED TO SAVE GENERATION LOG: {e} !!!", exc_info=True)

async def run_generation_task(
    tool_name: str,
    args: Union[GenerateImageParams, UpscaleImageParams],
    request_id: JsonRpcId,
    stream_id: str,
    self_base_url: str
):
    db = SessionLocal()
    start_time = time.monotonic()
    log_data = {
        "positive_prompt": getattr(args, 'prompt', None) or '',
        "negative_prompt": getattr(args, 'negative_prompt', None) or '',
        "status": "FAILED", "render_type_name": args.render_type, "style_names": ", ".join(getattr(args, 'style_names', [])),
        "aspect_ratio": getattr(args, 'aspect_ratio', None), "seed": args.seed,
        "llm_enhanced": False
    }

    try:
        final_seed = args.seed if args.seed is not None else random.randint(0, 2**32 - 1)
        log_data["seed"] = final_seed
        
        render_type_name = args.render_type
        
        if tool_name == "generate_image":
            enhanced_positive_prompt = args.prompt
            enhanced_negative_prompt = args.negative_prompt

            if args.enhance_prompt:
                all_db_settings = crud.get_all_settings(db)
                instance_id_str = all_db_settings.get("PROMPT_ENHANCEMENT_OLLAMA_INSTANCE_ID")
                model_name = all_db_settings.get("PROMPT_ENHANCEMENT_MODEL_NAME")
                
                if instance_id_str and model_name:
                    instance_id = int(instance_id_str)
                    instance = crud.get_ollama_instance_by_id(db, instance_id)
                    if instance and instance.is_active:
                        try:
                            logger.info(f"Enhancing prompt with model '{model_name}' on instance '{instance.name}'.")
                            async with OllamaClient(api_url=instance.base_url, model_name=model_name) as ollama_client:
                                enhanced_positive_prompt = await ollama_client.enhance_positive_prompt(args.prompt)
                                enhanced_negative_prompt = await ollama_client.enhance_negative_prompt(args.negative_prompt, enhanced_positive_prompt)
                            log_data["llm_enhanced"] = True
                        except OllamaError as e:
                            logger.warning(f"Ollama prompt enhancement failed: {e}. Proceeding without enhancement.")
                    else:
                        logger.warning("Prompt enhancement is enabled but the configured Ollama instance is inactive or not found. Skipping.")
                else:
                    logger.warning("Prompt enhancement is enabled but not fully configured in General Settings. Skipping.")

            style_names_to_apply = args.style_names
            if not style_names_to_apply:
                default_styles = crud.get_default_styles(db)
                if default_styles: style_names_to_apply = [s.name for s in default_styles]
            
            if style_names_to_apply:
                for style_name in style_names_to_apply:
                    style = crud.get_style_by_name(db, name=style_name)
                    if not style: continue
                    if render_type_name and not any(rt.name == render_type_name for rt in style.compatible_render_types):
                        if style.default_render_type: render_type_name = style.default_render_type.name
                    elif not render_type_name and style.default_render_type:
                        render_type_name = style.default_render_type.name

            positive_parts = [enhanced_positive_prompt]
            negative_parts = [enhanced_negative_prompt]
            if style_names_to_apply:
                for style_name in style_names_to_apply:
                    style = crud.get_style_by_name(db, name=style_name)
                    if style:
                        positive_parts.append(style.prompt_template)
                        negative_parts.append(style.negative_prompt_template)
            
            final_prompt = ", ".join(filter(None, positive_parts))
            final_negative_prompt = ", ".join(filter(None, negative_parts))
        else:
            final_prompt = getattr(args, 'prompt', '')
            final_negative_prompt = getattr(args, 'negative_prompt', '')

        log_data.update({"positive_prompt": final_prompt or '', "negative_prompt": final_negative_prompt or ''})

        if not render_type_name:
            if tool_name == "generate_image":
                default_rt = crud.get_default_render_type_for_generation(db)
            else:
                default_rt = crud.get_default_render_type_for_upscale(db)
            if not default_rt: raise ValueError(f"No default render type configured for '{tool_name}'.")
            render_type_name = default_rt.name
        
        log_data["render_type_name"] = render_type_name
        render_type_obj = crud.get_render_type_by_name(db, name=render_type_name)
        if not render_type_obj: raise ValueError(f"Render type '{render_type_name}' not found.")

        selected_instance = await _select_best_comfyui_instance(db, render_type_name)
        log_data["comfyui_instance_id"] = selected_instance.id
        comfyui_client = ComfyUIClient(api_url=selected_instance.base_url, generation_timeout=settings.comfyui_generation_timeout)

        workflow_path = Path("/app/workflows") / render_type_obj.workflow_filename
        if not workflow_path.is_file(): raise ValueError(f"Workflow file '{render_type_obj.workflow_filename}' not found.")
        workflow = json.loads(workflow_path.read_text())

        def set_prompt(node_id, text):
            inputs = workflow[node_id]["inputs"]
            if "Text" in inputs: inputs["Text"] = text
            elif "text" in inputs: inputs["text"] = text
        
        if final_prompt and (node_id := _find_node_id_by_title(workflow, "MCP_INPUT_PROMPT")): set_prompt(node_id, final_prompt)
        if final_negative_prompt and (node_id := _find_node_id_by_title(workflow, "MCP_INPUT_NEGATIVE_PROMPT")): set_prompt(node_id, final_negative_prompt)

        if node_id := _find_node_id_by_title(workflow, "MCP_SEED"):
            if "Value" in workflow[node_id]["inputs"]: workflow[node_id]["inputs"]["Value"] = final_seed
            else: workflow[node_id]["inputs"]["value"] = final_seed

        if tool_name == "generate_image":
            if args.aspect_ratio and (node_id := _find_node_id_by_title(workflow, "MCP_RESOLUTION")):
                width, height = ASPECT_RATIOS.get(args.aspect_ratio, DEFAULT_ASPECT_RATIO)
                workflow[node_id]["inputs"].update({"width": width, "height": height})
        
        elif tool_name == "upscale_image":
            db_settings = crud.get_all_settings(db)
            denoise = args.denoise if args.denoise is not None else float(db_settings.get("DEFAULT_UPSCALE_DENOISE", 0.2))
            if (node_id := _find_node_id_by_title(workflow, "MCP_DENOISE")):
                workflow[node_id]["inputs"]["value"] = denoise
            
            # Use the dynamically determined self_base_url for the local check
            image_filename = await comfyui_client.upload_image_from_url(
                image_url=args.input_image_url,
                server_public_url_base=self_base_url 
            )
            if not (node_id := _find_node_id_by_title(workflow, "MCP_INPUT_IMAGE")):
                raise ValueError("Upscale workflow missing node 'MCP_INPUT_IMAGE'.")
            workflow[node_id]["inputs"]["image"] = image_filename
        
        output_url_base = crud.get_all_settings(db).get("OUTPUT_URL_BASE")
        if not output_url_base: raise ValueError("OUTPUT_URL_BASE is not configured.")

        image_url = await comfyui_client.run_workflow_and_get_image(
            workflow=workflow, output_node_title="MCP_OUTPUT_IMAGE",
            output_dir_path="/app/outputs", output_url_base=output_url_base
        )
        
        log_data.update({"status": "SUCCESS", "image_filename": image_url.split('/')[-1]})

        structured_output = {
            "image_url": image_url,
            "seed": final_seed,
            "human_readable_summary": f"Image generated successfully: {image_url}"
        }
        result_payload = {
            "structured_output": structured_output,
            "content": [{"type": "image", "source": image_url}]
        }
        await manager.send_mcp_message(stream_id, {"jsonrpc": "2.0", "method": "stream/chunk", "params": {"stream_id": stream_id, "result": result_payload}})

    except Exception as e:
        error_message = str(e)
        logger.error(f"Error for stream {stream_id}: {error_message}", exc_info=True)
        log_data["error_message"] = error_message
        await manager.send_mcp_message(stream_id, {"jsonrpc": "2.0", "method": "stream/chunk", "params": {"stream_id": stream_id, "error": {"code": -32000, "message": error_message}}})
    
    finally:
        log_data["duration_ms"] = int((time.monotonic() - start_time) * 1000)
        _log_generation_result(db, log_data)
        await manager.send_mcp_message(stream_id, {"jsonrpc": "2.0", "method": "stream/end", "params": {"stream_id": stream_id}})
        manager.disconnect(stream_id)
        db.close()

async def run_description_task(
    args: DescribeImageParams,
    request_id: JsonRpcId,
    stream_id: str
):
    db = SessionLocal()
    try:
        desc_settings = crud.get_description_settings(db)
        if not desc_settings or not desc_settings.ollama_instance_id or not desc_settings.model_name:
            raise ValueError("The 'describe_image' tool is not configured.")

        instance = crud.get_ollama_instance_by_id(db, desc_settings.ollama_instance_id)
        if not instance or not instance.is_active:
            raise ValueError("The configured Ollama instance for the describe tool is inactive or does not exist.")

        template_key = f"{args.description_type}_prompt_template_{args.language}"
        prompt_template = getattr(desc_settings, template_key, None)
        if not prompt_template:
            raise ValueError(f"Invalid description type or language. Could not find template '{template_key}'.")

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(args.input_image_url) as response:
                    response.raise_for_status()
                    image_data = await response.read()
                    image_base64 = base64.b64encode(image_data).decode('utf-8')
        except Exception as e:
            raise ValueError(f"Failed to download or process image from URL: {e}")

        async with OllamaClient(api_url=instance.base_url, model_name=desc_settings.model_name) as ollama_client:
            description = await ollama_client.describe_image(prompt=prompt_template, image_base_64=image_base64)
        
        structured_output = {
            "description": description,
            "human_readable_summary": description
        }
        result_payload = {
            "structured_output": structured_output,
            "content": [{"type": "text", "text": description}]
        }
        await manager.send_mcp_message(stream_id, {"jsonrpc": "2.0", "method": "stream/chunk", "params": {"stream_id": stream_id, "result": result_payload}})

    except Exception as e:
        error_message = str(e)
        logger.error(f"Error for stream {stream_id}: {error_message}", exc_info=True)
        await manager.send_mcp_message(stream_id, {"jsonrpc": "2.0", "method": "stream/chunk", "params": {"stream_id": stream_id, "error": {"code": -32000, "message": error_message}}})
    
    finally:
        await manager.send_mcp_message(stream_id, {"jsonrpc": "2.0", "method": "stream/end", "params": {"stream_id": stream_id}})
        manager.disconnect(stream_id)
        db.close()


class GeneratePromptResult(BaseModel):
    positive_prompt: str
    negative_prompt: str

async def _translate_to_english_if_needed(text: str, client: OllamaClient) -> str:
    if not text or not text.strip():
        return text
    try:
        prompt = (
            "Your task is to ensure the following text is in English. "
            "If it is already in English, return it verbatim. "
            "If it is in another language, translate it to English. "
            "Respond with ONLY the resulting English text, without any quotes or explanations. "
            f"Text: \"{text}\""
        )
        translated_text = await client.generate_text(prompt)
        return translated_text.strip().replace('"', '')
    except Exception as e:
        logger.warning(f"Could not translate text '{text}': {e}. Using original text.")
        return text

async def run_prompt_generator_task(
    args: GeneratePromptParams, db: Session
) -> GeneratePromptResult:
    SUBJECT_THEMES = [
        "a dramatic close-up portrait of a character", "a full body shot of a character in a dynamic action pose",
        "an intimate scene focusing on a character's emotions", "a character interacting with a fantastical creature",
        "a character set against a vast, breathtaking landscape", "a mysterious figure in a dark, moody environment",
        "a sci-fi character with advanced technology", "a fantasy hero preparing for battle",
        "an epic, panoramic view of a mountain range at sunrise", "an enchanted forest with glowing flora and a mystical river",
        "a desolate, alien desert under a sky with two moons", "a storm-swept coastline with crashing waves against dramatic cliffs",
        "a sprawling, futuristic cityscape with flying vehicles and towering megastructures", "the intricate, gothic interior of a grand cathedral with stained glass windows",
        "the overgrown ruins of an ancient, forgotten temple in the jungle", "a cozy, detailed cutaway of a hobbit-style burrow built into a hillside",
    ]
    
    config = crud.get_prompt_generator_settings(db)
    allowed_styles = crud.get_allowed_styles_for_generator(db)
    if not allowed_styles:
        raise ValueError("Prompt Generator tool is not configured: no allowed styles.")

    all_db_settings = crud.get_all_settings(db)
    instance_id_str = all_db_settings.get("PROMPT_ENHANCEMENT_OLLAMA_INSTANCE_ID")
    model_name = all_db_settings.get("PROMPT_ENHANCEMENT_MODEL_NAME")
    if not instance_id_str or not model_name:
        raise ValueError("Prompt Generator requires a configured Prompt Enhancement LLM in General Settings.")
    
    instance_id = int(instance_id_str)
    instance = crud.get_ollama_instance_by_id(db, instance_id)
    if not instance or not instance.is_active:
        raise ValueError("The configured Prompt Enhancement LLM is inactive or not found.")

    async with OllamaClient(api_url=instance.base_url, model_name=model_name) as ollama_client:
        initial_theme = ""
        if args.subject:
            initial_theme = await _translate_to_english_if_needed(args.subject, ollama_client)
        else:
            initial_theme = random.choice(SUBJECT_THEMES)
        
        chosen_style = None
        if args.render_style:
            chosen_style = next((s for s in allowed_styles if s.name == args.render_style), None)
        
        if not chosen_style:
            try:
                allowed_style_names = [s.name for s in allowed_styles]
                prompt = f"Given the theme '{initial_theme}', which of the following visual styles is most appropriate? Styles: {allowed_style_names}. Respond with only the name of the style from the list, and nothing else."
                render_style_name = await ollama_client.generate_text(prompt)
                render_style_name = render_style_name.strip().replace('"', '')
                chosen_style = next((s for s in allowed_styles if s.name == render_style_name), None)
            except Exception as e:
                logger.warning(f"LLM style selection failed: {e}. A random style will be chosen.")
        
        if not chosen_style:
            logger.warning(f"LLM-chosen style not in allowed list or selection failed. Picking a random allowed style.")
            chosen_style = random.choice(allowed_styles)

        subject = initial_theme
        try:
            prompt = ""
            if args.subject:
                # If user provides a subject, ask for variations of IT.
                prompt = (
                    f"Based on the core subject '{initial_theme}', generate a list of {config.subjects_to_propose} creative and specific variations for an image. "
                    "Each variation MUST be a direct elaboration of the original subject, adding context, action, or details. Do not replace the core subject. "
                    "Feel free to place the subject in diverse settings (realistic, fantasy, sci-fi, etc.) unless the subject itself implies a specific universe. "
                    "Your response MUST be a single valid JSON list of strings."
                )
            else:
                # If no subject is provided, ask for brand new ideas based on the random theme.
                enriched_theme = f"{initial_theme}, in the style of {chosen_style.name}"
                prompt = (
                    f"Based on the theme '{enriched_theme}', generate a list of {config.subjects_to_propose} different, specific, and creative subjects for a visual image. "
                    "Focus on concrete scenes, characters, or objects. Avoid abstract concepts. "
                    "Your response MUST be a single valid JSON list of strings, and nothing else. "
                    'Example: ["a majestic griffon...", "a clever kitsune...", "a terrifying chimera..."]'
                )

            raw_response = await ollama_client.generate_json(prompt)
            logger.info(f"LLM raw response for subjects: {raw_response}")

            subject_list = []
            if isinstance(raw_response, list):
                subject_list = raw_response
            elif isinstance(raw_response, dict):
                # Find the first value in the dict that is a list
                for value in raw_response.values():
                    if isinstance(value, list):
                        subject_list = value
                        break

            if subject_list:
                subject = random.choice(subject_list)
            else:
                logger.warning("Could not extract a valid list of subjects from LLM response. Falling back to the initial theme.")
        except Exception as e:
            logger.warning(f"LLM subject list generation failed: {e}. Using the initial theme as subject.")

        elements = []
        if args.elements:
            elements = await asyncio.gather(*[_translate_to_english_if_needed(e, ollama_client) for e in args.elements])
        else:
            element_prompt = (
                f"You are an assistant for creating image prompts. Your task is to propose {config.elements_to_propose} categories of visual details "
                f"relevant to the subject '{subject}'. Focus on concrete, visual attributes. "
                "Good examples: 'Character's Pose', 'Facial Expression', 'Clothing Style', 'Hairstyle', 'Key Accessory', 'Lighting', 'Background Environment', 'Color Palette', 'Mood'. "
                "Bad examples: 'Symbolism', 'Narrative', 'Motivation'. "
                "Your response MUST be a single JSON list of strings, and nothing else."
            )
            raw_elements = await ollama_client.generate_json(element_prompt)
            logger.info(f"LLM raw response for proposed elements: {raw_elements}")
            
            proposed_elements = []
            if isinstance(raw_elements, list):
                proposed_elements = raw_elements
            elif isinstance(raw_elements, dict):
                for value in raw_elements.values():
                    if isinstance(value, list):
                        proposed_elements = value
                        break
            
            if proposed_elements:
                elements = random.sample(proposed_elements, min(config.elements_to_select, len(proposed_elements)))

        context = [subject]
        for element in elements:
            try:
                refinement_prompt = (
                    f"Current prompt context: '{', '.join(context)}'. "
                    f"Propose {config.variations_to_propose} specific, visual, and concrete variations for the element '{element}'. "
                    "Avoid abstract ideas. For 'Lighting', suggest 'dramatic Rembrandt lighting' not 'sad lighting'. For 'Clothing', suggest 'tattered leather armor' not 'adventurous attire'. "
                    "Your response MUST be a single JSON list of strings, and nothing else."
                )
                raw_choices = await ollama_client.generate_json(refinement_prompt)
                logger.info(f"LLM raw response for element '{element}': {raw_choices}")

                choices = []
                if isinstance(raw_choices, list):
                    choices = raw_choices
                elif isinstance(raw_choices, dict):
                    for value in raw_choices.values():
                        if isinstance(value, list):
                            choices = value
                            break

                if choices:
                    choice = random.choice(choices)
                    context.append(choice)
                else:
                    logger.warning(f"LLM returned no valid choices for element '{element}'. Skipping.")
            except Exception as e:
                logger.warning(f"LLM failed to provide choices for element '{element}': {e}. Skipping it.")

        base_prompt_list = context
        final_positive_prompt_template = ", ".join(filter(None, ["{prompt}", chosen_style.prompt_template]))
        final_negative_prompt = chosen_style.negative_prompt_template

        enhancement_instruction = (
            f"You are an expert prompt engineer. Transform the following list of visual concepts into a single, cohesive, and highly descriptive prompt for an image generation AI. "
            "Combine the ideas into a flowing sentence or two. Focus on what is *seen* in the image. Do not use abstract terms. "
            f"Concepts to combine: {base_prompt_list}"
        )
        
        enhanced_positive_raw = await ollama_client.generate_text(enhancement_instruction)
        enhanced_positive = final_positive_prompt_template.format(prompt=enhanced_positive_raw.strip())
        
        enhanced_negative = await ollama_client.enhance_negative_prompt(final_negative_prompt, enhanced_positive)

        return GeneratePromptResult(positive_prompt=enhanced_positive, negative_prompt=enhanced_negative)


# --- MCP JSON-RPC Endpoint ---

def create_error_response(request_id: JsonRpcId, code: int, message: str) -> JSONResponse:
    error = JsonRpcError(code=code, message=message)
    return JSONResponse(status_code=200, content=JsonRpcResponse(error=error, id=request_id).model_dump(exclude_none=True))

@router.post("/mcp")
async def mcp_endpoint(request: Request, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    try:
        rpc_request = JsonRpcRequest.model_validate(await request.json())
    except Exception:
        return create_error_response(None, -32700, "Invalid JSON received.")

    request_id = rpc_request.id

    if rpc_request.method == "tools/list":
        tools = []
        visible_render_types = crud.get_render_types(db, visible_only=True)
        styles = crud.get_styles(db)
        style_names = [s.name for s in styles]

        gen_render_types = [rt for rt in visible_render_types if rt.generation_mode == 'image_generation']
        if gen_render_types:
            tool_def = copy.deepcopy(GENERATE_IMAGE_TOOL_SCHEMA)
            if style_names: tool_def["inputSchema"]["properties"]["style_names"]["enum"] = style_names
            tool_def["inputSchema"]["properties"]["render_type"]["enum"] = [rt.name for rt in gen_render_types]
            tool_def["outputSchema"] = {
                "type": "object",
                "properties": {
                    "image_url": {"type": "string", "description": "The URL of the generated image."},
                    "seed": {"type": "integer", "description": "The seed used for the generation."},
                    "human_readable_summary": {"type": "string", "description": "A summary of the result."}
                },
                "required": ["image_url", "seed", "human_readable_summary"]
            }
            tools.append(tool_def)
        
        upscale_render_types = [rt for rt in visible_render_types if rt.generation_mode == 'upscale']
        if upscale_render_types:
            tool_def = copy.deepcopy(UPSCALE_IMAGE_TOOL_SCHEMA)
            upscale_type_names = [rt.name for rt in upscale_render_types]
            tool_def["inputSchema"]["properties"]["render_type"]["enum"] = upscale_type_names
            tool_def["inputSchema"]["properties"]["upscale_type"]["enum"] = upscale_type_names
            tool_def["outputSchema"] = {
                "type": "object",
                "properties": {
                    "image_url": {"type": "string", "description": "The URL of the upscaled image."},
                    "seed": {"type": "integer", "description": "The seed used for the generation."},
                    "human_readable_summary": {"type": "string", "description": "A summary of the result."}
                },
                "required": ["image_url", "seed", "human_readable_summary"]
            }
            tools.append(tool_def)

        desc_settings = crud.get_description_settings(db)
        if desc_settings and desc_settings.ollama_instance_id and desc_settings.model_name:
            tool_def = copy.deepcopy(DESCRIBE_IMAGE_TOOL_SCHEMA)
            tool_def["outputSchema"] = {
                "type": "object",
                "properties": {
                    "description": {"type": "string", "description": "The generated textual description of the image."},
                    "human_readable_summary": {"type": "string", "description": "A summary of the result."}
                },
                "required": ["description", "human_readable_summary"]
            }
            tools.append(tool_def)

        allowed_styles = crud.get_allowed_styles_for_generator(db)
        if allowed_styles:
            tool_def = copy.deepcopy(PROMPT_GENERATOR_TOOL_SCHEMA)
            tool_def["inputSchema"]["properties"]["render_style"]["enum"] = [s.name for s in allowed_styles]
            tool_def["outputSchema"] = {
                "type": "object",
                "properties": {
                    "positive_prompt": {"type": "string", "description": "The generated positive prompt."},
                    "negative_prompt": {"type": "string", "description": "The generated negative prompt."},
                    "human_readable_summary": {"type": "string", "description": "A formatted summary of the generated prompts."}
                },
                "required": ["positive_prompt", "negative_prompt", "human_readable_summary"]
            }
            tools.append(tool_def)

        response_model = JsonRpcResponse(result={"tools": tools}, id=request_id)
        return JSONResponse(content=response_model.model_dump(exclude_none=True))

    if rpc_request.method == "tools/call":
        try:
            params = ToolCallParams.model_validate(rpc_request.params)
            tool_name = params.name
            arguments = params.arguments
            
            if tool_name == "generate_prompt":
                validated_args = GeneratePromptParams.model_validate(arguments)
                result_obj = await run_prompt_generator_task(validated_args, db)
                
                human_readable_summary = (
                    f"**Positive Prompt:**\n```\n{result_obj.positive_prompt}\n```\n"
                    f"**Negative Prompt:**\n```\n{result_obj.negative_prompt}\n```"
                )
                
                structured_json_payload = {
                    "positive_prompt": result_obj.positive_prompt,
                    "negative_prompt": result_obj.negative_prompt,
                    "human_readable_summary": human_readable_summary
                }
                
                result_content = {
                    "content": [{"type": "json", "json": structured_json_payload}]
                }
                
                response_model = JsonRpcResponse(result=result_content, id=request_id)
                return JSONResponse(content=response_model.model_dump(exclude_none=True))

            task_function = None
            validated_args = None

            if tool_name == "generate_image":
                validated_args = GenerateImageParams.model_validate(arguments)
                task_function = run_generation_task
            elif tool_name == "upscale_image":
                validated_args = UpscaleImageParams.model_validate(arguments)
                task_function = run_generation_task
            elif tool_name == "describe_image":
                validated_args = DescribeImageParams.model_validate(arguments)
                task_function = run_description_task
            else:
                raise ValueError(f"Tool '{tool_name}' not found.")

            stream_id = str(uuid.uuid4())
            public_url_base = crud.get_all_settings(db).get("OUTPUT_URL_BASE")
            
            if public_url_base:
                parsed_url = urlparse(public_url_base)
                scheme = "ws" if parsed_url.scheme == "http" else "wss"
                ws_url = f"{scheme}://{parsed_url.netloc}/ws/stream/{stream_id}"
            else:
                scheme = "ws" if request.url.scheme == "http" else "wss"
                ws_url = f"{scheme}://{request.url.hostname}:{request.url.port}/ws/stream/{stream_id}"
            
            # Dynamically determine the server's own base URL from the request
            self_base_url = f"{request.url.scheme}://{request.url.netloc}"

            task_kwargs = {"args": validated_args, "request_id": request_id, "stream_id": stream_id}
            if tool_name in ["generate_image", "upscale_image"]:
                task_kwargs["tool_name"] = tool_name
                task_kwargs["self_base_url"] = self_base_url # Pass it to the background task

            background_tasks.add_task(task_function, **task_kwargs)

            response = {"jsonrpc": "2.0", "method": "stream/start", "params": {"stream_id": stream_id, "ws_url": ws_url}, "id": request_id}
            return JSONResponse(content=response)

        except ValidationError as e: return create_error_response(request_id, -32602, f"Invalid parameters: {e}")
        except ValueError as e: return create_error_response(request_id, -32000, str(e))
        except Exception:
            logger.exception("Internal error during 'tools/call' setup.")
            return create_error_response(request_id, -32603, "Internal server error.")
    
    return create_error_response(request_id, -32601, f"Method '{rpc_request.method}' not found.")