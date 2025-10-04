#### Fichier: app/api/mcp_routes.py
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
    stream_id: str
):
    db = SessionLocal()
    start_time = time.monotonic()
    log_data = {
        "positive_prompt": getattr(args, 'prompt', None) or '',
        "negative_prompt": getattr(args, 'negative_prompt', None) or '',
        "status": "FAILED", "render_type_name": args.render_type, "style_names": ", ".join(getattr(args, 'style_names', [])),
        "aspect_ratio": getattr(args, 'aspect_ratio', None), "seed": args.seed,
        "llm_enhanced": False # Default to False
    }

    try:
        final_seed = args.seed if args.seed is not None else random.randint(0, 2**32 - 1)
        log_data["seed"] = final_seed
        
        render_type_name = args.render_type
        
        # --- Prompt Processing (for generate_image only) ---
        if tool_name == "generate_image":
            enhanced_positive_prompt = args.prompt
            enhanced_negative_prompt = args.negative_prompt

            # 1. LLM Enhancement (if requested and configured)
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

            # 2. Style selection and Render Type override
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

            # 3. Assemble final prompts
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
        else: # For upscale_image
            final_prompt = getattr(args, 'prompt', '')
            final_negative_prompt = getattr(args, 'negative_prompt', '')

        log_data.update({"positive_prompt": final_prompt or '', "negative_prompt": final_negative_prompt or ''})

        # --- Determine Render Type ---
        if not render_type_name:
            if tool_name == "generate_image":
                default_rt = crud.get_default_render_type_for_generation(db)
            else: # upscale_image
                default_rt = crud.get_default_render_type_for_upscale(db)
            if not default_rt: raise ValueError(f"No default render type configured for '{tool_name}'.")
            render_type_name = default_rt.name
        
        log_data["render_type_name"] = render_type_name
        render_type_obj = crud.get_render_type_by_name(db, name=render_type_name)
        if not render_type_obj: raise ValueError(f"Render type '{render_type_name}' not found.")

        # --- Select Instance and Load Workflow ---
        selected_instance = await _select_best_comfyui_instance(db, render_type_name)
        log_data["comfyui_instance_id"] = selected_instance.id
        comfyui_client = ComfyUIClient(api_url=selected_instance.base_url, generation_timeout=settings.comfyui_generation_timeout)

        workflow_path = Path("/app/workflows") / render_type_obj.workflow_filename
        if not workflow_path.is_file(): raise ValueError(f"Workflow file '{render_type_obj.workflow_filename}' not found.")
        workflow = json.loads(workflow_path.read_text())

        # --- Inject Parameters into Workflow ---
        def set_prompt(node_id, text):
            inputs = workflow[node_id]["inputs"]
            if "Text" in inputs: inputs["Text"] = text
            elif "text" in inputs: inputs["text"] = text
        
        if final_prompt and (node_id := _find_node_id_by_title(workflow, "MCP_INPUT_PROMPT")): set_prompt(node_id, final_prompt)
        if final_negative_prompt and (node_id := _find_node_id_by_title(workflow, "MCP_INPUT_NEGATIVE_PROMPT")): set_prompt(node_id, final_negative_prompt)

        if node_id := _find_node_id_by_title(workflow, "MCP_SEED"):
            if "Value" in workflow[node_id]["inputs"]: workflow[node_id]["inputs"]["Value"] = final_seed
            else: workflow[node_id]["inputs"]["value"] = final_seed

        # --- Mode-Specific Logic ---
        if tool_name == "generate_image":
            if args.aspect_ratio and (node_id := _find_node_id_by_title(workflow, "MCP_RESOLUTION")):
                width, height = ASPECT_RATIOS.get(args.aspect_ratio, DEFAULT_ASPECT_RATIO)
                workflow[node_id]["inputs"].update({"width": width, "height": height})
        
        elif tool_name == "upscale_image":
            db_settings = crud.get_all_settings(db)
            denoise = args.denoise if args.denoise is not None else float(db_settings.get("DEFAULT_UPSCALE_DENOISE", 0.2))
            if (node_id := _find_node_id_by_title(workflow, "MCP_DENOISE")):
                workflow[node_id]["inputs"]["value"] = denoise
            
            image_filename = await comfyui_client.upload_image_from_url(args.input_image_url)
            if not (node_id := _find_node_id_by_title(workflow, "MCP_INPUT_IMAGE")):
                raise ValueError("Upscale workflow missing node 'MCP_INPUT_IMAGE'.")
            workflow[node_id]["inputs"]["image"] = image_filename
        
        # --- Execute and Send Result ---
        output_url_base = crud.get_all_settings(db).get("OUTPUT_URL_BASE")
        if not output_url_base: raise ValueError("OUTPUT_URL_BASE is not configured.")

        image_url = await comfyui_client.run_workflow_and_get_image(
            workflow=workflow, output_node_title="MCP_OUTPUT_IMAGE",
            output_dir_path="/app/outputs", output_url_base=output_url_base
        )
        
        log_data.update({"status": "SUCCESS", "image_filename": image_url.split('/')[-1]})
        await manager.send_mcp_message(stream_id, {"jsonrpc": "2.0", "method": "stream/chunk", "params": {"stream_id": stream_id, "result": {"content": [{"type": "image", "source": image_url}]}}})

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
        # --- Configuration validation ---
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

        # --- Image Processing ---
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(args.input_image_url) as response:
                    response.raise_for_status()
                    image_data = await response.read()
                    image_base64 = base64.b64encode(image_data).decode('utf-8')
        except Exception as e:
            raise ValueError(f"Failed to download or process image from URL: {e}")

        # --- Execute and Send Result ---
        async with OllamaClient(api_url=instance.base_url, model_name=desc_settings.model_name) as ollama_client:
            description = await ollama_client.describe_image(prompt=prompt_template, image_base64=image_base64)
        
        await manager.send_mcp_message(stream_id, {"jsonrpc": "2.0", "method": "stream/chunk", "params": {"stream_id": stream_id, "result": {"content": [{"type": "text", "text": description}]}}})

    except Exception as e:
        error_message = str(e)
        logger.error(f"Error for stream {stream_id}: {error_message}", exc_info=True)
        await manager.send_mcp_message(stream_id, {"jsonrpc": "2.0", "method": "stream/chunk", "params": {"stream_id": stream_id, "error": {"code": -32000, "message": error_message}}})
    
    finally:
        await manager.send_mcp_message(stream_id, {"jsonrpc": "2.0", "method": "stream/end", "params": {"stream_id": stream_id}})
        manager.disconnect(stream_id)
        db.close()


def _extract_json_list(text: str) -> List[Any]:
    """Robustly extracts a JSON list from a string that may contain other text."""
    try:
        start_index = text.find('[')
        end_index = text.rfind(']')
        if start_index != -1 and end_index != -1 and end_index > start_index:
            json_str = text[start_index:end_index+1]
            return json.loads(json_str)
        else:
            raise ValueError("No JSON list found in the text.")
    except (json.JSONDecodeError, ValueError) as e:
        logger.error(f"Failed to decode or extract JSON from LLM response: {text}")
        raise ValueError(f"LLM returned malformed data that could not be parsed as a list.") from e


class GeneratePromptResult(BaseModel):
    positive_prompt: str
    negative_prompt: str

async def run_prompt_generator_task(
    args: GeneratePromptParams, db: Session
) -> GeneratePromptResult:
    """Executes the complete workflow for the 'generate_prompt' tool."""
    DEFAULT_SUBJECTS = [
        "a majestic dragon flying over a mountain range",
        "a futuristic cityscape at night with flying vehicles",
        "an enchanted forest with glowing mushrooms and mythical creatures",
        "a lone astronaut discovering an alien artifact on a desolate planet",
        "a steampunk-inspired inventor in their cluttered workshop"
    ]

    # 0. Get Configuration
    settings = crud.get_prompt_generator_settings(db)
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
        # 1. Determine Subject
        subject = args.subject
        if not subject:
            try:
                prompt = (
                    f"Generate {settings.subjects_to_propose} creative and diverse subjects for an image. "
                    "Your response MUST be a valid JSON list of strings, and nothing else. "
                    'Example: ["a majestic lion", "a futuristic city at night", "a peaceful enchanted forest"]'
                )
                response_str = await ollama_client.generate_text(prompt)
                subject = random.choice(_extract_json_list(response_str))
            except Exception as e:
                logger.warning(f"LLM subject generation failed: {e}. Using a fallback subject.")
                subject = random.choice(DEFAULT_SUBJECTS)
        
        # 2. Determine Elements
        elements = args.elements
        if not elements:
            prompt = f"Generate {settings.elements_to_propose} generic categories for describing an image (e.g., 'lighting', 'clothing', 'background', 'mood', 'setting'). Provide the output as a single JSON list of strings, and nothing else."
            response_str = await ollama_client.generate_text(prompt)
            elements = random.sample(_extract_json_list(response_str), settings.elements_to_select)

        # 3. Determine Render Style
        render_style_name = args.render_style
        if not render_style_name:
            allowed_style_names = [s.name for s in allowed_styles]
            prompt = f"Given the subject '{subject}', which of the following render styles is most appropriate? Styles: {allowed_style_names}. Respond with only the name of the style from the list, and nothing else."
            render_style_name = await ollama_client.generate_text(prompt)
            render_style_name = render_style_name.strip().replace('"', '')
        
        chosen_style = next((s for s in allowed_styles if s.name == render_style_name), None)
        if not chosen_style:
            logger.warning(f"LLM chose style '{render_style_name}' which is not in the allowed list. Picking a random allowed style.")
            chosen_style = random.choice(allowed_styles)

        # 4. Iterative Refinement
        context = [subject]
        for element in elements:
            prompt = f"Context: {', '.join(context)}. Generate {settings.variations_to_propose} specific variations for the element '{element}'. Provide the output as a single JSON list of strings, and nothing else."
            response_str = await ollama_client.generate_text(prompt)
            choice = random.choice(_extract_json_list(response_str))
            context.append(choice)

        # 5. Assemble and Enhance
        base_prompt = ", ".join(context)
        final_positive_prompt = ", ".join(filter(None, [base_prompt, chosen_style.prompt_template]))
        final_negative_prompt = chosen_style.negative_prompt_template

        enhanced_positive = await ollama_client.enhance_positive_prompt(final_positive_prompt)
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
            tools.append(tool_def)
        
        upscale_render_types = [rt for rt in visible_render_types if rt.generation_mode == 'upscale']
        if upscale_render_types:
            tool_def = copy.deepcopy(UPSCALE_IMAGE_TOOL_SCHEMA)
            upscale_type_names = [rt.name for rt in upscale_render_types]
            tool_def["inputSchema"]["properties"]["render_type"]["enum"] = upscale_type_names
            tool_def["inputSchema"]["properties"]["upscale_type"]["enum"] = upscale_type_names
            tools.append(tool_def)

        desc_settings = crud.get_description_settings(db)
        if desc_settings and desc_settings.ollama_instance_id and desc_settings.model_name:
            tools.append(DESCRIBE_IMAGE_TOOL_SCHEMA)

        allowed_styles = crud.get_allowed_styles_for_generator(db)
        if allowed_styles:
            tool_def = copy.deepcopy(PROMPT_GENERATOR_TOOL_SCHEMA)
            tool_def["inputSchema"]["properties"]["render_style"]["enum"] = [s.name for s in allowed_styles]
            tools.append(tool_def)

        # --- START OF FIX: Ensure proper JSON serialization ---
        response_model = JsonRpcResponse(result={"tools": tools}, id=request_id)
        return JSONResponse(content=response_model.model_dump(exclude_none=True))
        # --- END OF FIX ---

    if rpc_request.method == "tools/call":
        try:
            params = ToolCallParams.model_validate(rpc_request.params)
            tool_name = params.name
            arguments = params.arguments
            
            if tool_name == "generate_prompt":
                validated_args = GeneratePromptParams.model_validate(arguments)
                result = await run_prompt_generator_task(validated_args, db)
                formatted_text = (
                    f"**Positive Prompt:**\n```\n{result.positive_prompt}\n```\n"
                    f"**Negative Prompt:**\n```\n{result.negative_prompt}\n```"
                )
                result_content = {"content": [{"type": "text", "text": formatted_text}]}
                # --- START OF FIX: Ensure proper JSON serialization ---
                response_model = JsonRpcResponse(result=result_content, id=request_id)
                return JSONResponse(content=response_model.model_dump(exclude_none=True))
                # --- END OF FIX ---

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
            
            task_kwargs = {"args": validated_args, "request_id": request_id, "stream_id": stream_id}
            if tool_name in ["generate_image", "upscale_image"]:
                task_kwargs["tool_name"] = tool_name

            background_tasks.add_task(task_function, **task_kwargs)

            response = {"jsonrpc": "2.0", "method": "stream/start", "params": {"stream_id": stream_id, "ws_url": ws_url}, "id": request_id}
            return JSONResponse(content=response)

        except ValidationError as e: return create_error_response(request_id, -32602, f"Invalid parameters: {e}")
        except ValueError as e: return create_error_response(request_id, -32000, str(e))
        except Exception:
            logger.exception("Internal error during 'tools/call' setup.")
            return create_error_response(request_id, -32603, "Internal server error.")
    
    return create_error_response(request_id, -32601, f"Method '{rpc_request.method}' not found.")