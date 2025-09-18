####
# app/api/mcp_routes.py
####
from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import JSONResponse
from pydantic import ValidationError, BaseModel
from sqlalchemy.orm import Session
import logging
import time
from typing import Optional, Dict, Any
import copy
import asyncio

from ..schemas import (
    JsonRpcRequest,
    JsonRpcResponse,
    JsonRpcError,
    ToolCallParams,
    GenerateImageParams,
    GENERATE_IMAGE_TOOL_DEF,
    JsonRpcId,
    GenerationLogCreate
)
# Import the client classes, not global instances
from ..services.comfyui_client import ComfyUIClient, ComfyUIError, ComfyUIConnectionError
from ..services.ollama_client import OllamaClient, OllamaError
from ..database.session import get_db
from ..database import crud
from ..config import settings  # Import the settings object

logger = logging.getLogger(__name__)
router = APIRouter()


async def _process_prompts(args: GenerateImageParams, db: Session) -> tuple[str, str, Optional[str]]:
    """
    Helper function to process prompts.
    1. Checks for and applies default styles if none are provided.
    2. Checks render type compatibility with styles and updates render type if needed.
    3. Applies styles to prompts.
    4. Optionally enhances prompts with an LLM, using render type examples as context.
    Returns a tuple of (final_prompt, final_negative_prompt, final_render_type).
    Raises OllamaError on failure.
    """
    logger.info("Starting prompt processing...")

    # --- 1. Determine which styles to apply (user-provided or default) ---
    style_names_to_apply = args.style_names
    if not style_names_to_apply:
        logger.info("No styles provided by user. Checking for default styles.")
        default_styles = crud.get_default_styles(db)
        if default_styles:
            style_names_to_apply = [s.name for s in default_styles]
            logger.info(f"Applying default styles: {style_names_to_apply}")

    # --- 2. Determine final render type based on style compatibility ---
    final_render_type = args.render_type
    if style_names_to_apply:
        logger.info(f"Analyzing styles for render type compatibility: {style_names_to_apply}")
        for style_name in style_names_to_apply:
            style = crud.get_style_by_name(db, name=style_name)
            if not style:
                continue

            # Case A: A render type is set, check for incompatibility
            if final_render_type:
                compatible_names = [rt.name for rt in style.compatible_render_types]
                if final_render_type not in compatible_names:
                    logger.warning(f"Style '{style_name}' is not compatible with render type '{final_render_type}'. Compatible: {compatible_names}")
                    if style.recommended_render_type:
                        new_render_type = style.recommended_render_type.name
                        logger.info(f"Switching to recommended render type from style '{style_name}': '{new_render_type}'")
                        final_render_type = new_render_type
                        # A switch has occurred, the next style in the list will be checked against this new render_type
            
            # Case B: No render type is set yet, check for a recommendation to adopt
            else:
                if style.recommended_render_type:
                    new_render_type = style.recommended_render_type.name
                    logger.info(f"No render type specified. Adopting recommended type '{new_render_type}' from style '{style_name}'.")
                    final_render_type = new_render_type

    # --- 3. Apply styles ---
    positive_parts = [args.prompt]
    negative_parts = [args.negative_prompt]

    if style_names_to_apply:
        logger.info(f"Applying styles: {style_names_to_apply}")
        for style_name in style_names_to_apply:
            style = crud.get_style_by_name(db, name=style_name)
            if style:
                if style.prompt_template: positive_parts.append(style.prompt_template)
                if style.negative_prompt_template: negative_parts.append(style.negative_prompt_template)
            else:
                logger.warning(f"Style '{style_name}' not found, skipping.")

    final_prompt = ", ".join(filter(None, positive_parts))
    final_negative_prompt = ", ".join(filter(None, negative_parts))
    logger.debug(f"Prompt after styles: '{final_prompt}'")

    # --- 4. Enhance with LLM (if requested) ---
    if args.enhance_prompt:
        logger.info("Enhancing prompts with Ollama.")
        db_settings = crud.get_all_settings(db)
        ollama_url = db_settings.get("OLLAMA_API_URL")
        ollama_model = db_settings.get("OLLAMA_MODEL_NAME")

        if not ollama_url or not ollama_model:
            logger.warning("Ollama enhancement requested, but Ollama is not configured in settings. Skipping.")
            return final_prompt, final_negative_prompt, final_render_type
        
        keep_alive = db_settings.get("OLLAMA_KEEP_ALIVE", "5m")
        context_window_str = db_settings.get("OLLAMA_CONTEXT_WINDOW", "0")
        try:
            context_window = int(context_window_str)
        except (ValueError, TypeError):
            context_window = 0
        
        ollama_client = OllamaClient(
            api_url=ollama_url,
            model_name=ollama_model,
            keep_alive=keep_alive,
            context_window=context_window
        )
        
        # --- Get Render Type Examples ---
        prompt_examples = None
        if final_render_type:
            render_type_obj = crud.get_render_type_by_name(db, name=final_render_type)
            if render_type_obj and render_type_obj.prompt_examples:
                prompt_examples = render_type_obj.prompt_examples
                logger.info(f"Found prompt examples for render type '{final_render_type}'.")

        # --- Call Ollama with examples ---
        enhanced_prompt = await ollama_client.enhance_positive_prompt(
            base_prompt=final_prompt,
            examples=prompt_examples
        )
        logger.debug(f"Enhanced positive prompt: '{enhanced_prompt}'")

        enhanced_negative = await ollama_client.enhance_negative_prompt(
            base_negative=final_negative_prompt,
            positive_context=enhanced_prompt
        )
        logger.debug(f"Enhanced negative prompt: '{enhanced_negative}'")
        
        final_prompt = enhanced_prompt
        final_negative_prompt = enhanced_negative
    
    return final_prompt, final_negative_prompt, final_render_type


def _log_generation_result(db: Session, log_data: Dict[str, Any]):
    """
    Safely creates a generation log entry. This function must not raise exceptions.
    """
    try:
        log_entry = GenerationLogCreate(**log_data)
        crud.create_generation_log(db, log=log_entry)
    except Exception as e:
        logger.error("!!! CRITICAL: FAILED TO SAVE GENERATION LOG TO DATABASE !!!")
        logger.error(f"Logging data was: {log_data}")
        logger.error(f"Database error: {e}", exc_info=True)


# --- Web UI Helper API Endpoints ---
# ... (contenu inchangé)

@router.post("/api/v1/process-prompts", response_model=dict)
async def process_prompts_endpoint(params: GenerateImageParams, db: Session = Depends(get_db)):
    """
    API endpoint for the test UI to process prompts without generating an image.
    """
    try:
        final_prompt, final_negative_prompt, final_render_type = await _process_prompts(params, db)
        return {
            "final_prompt": final_prompt,
            "final_negative_prompt": final_negative_prompt,
            "final_render_type": final_render_type
        }
    except OllamaError as e:
        logger.error(f"Ollama service error during prompt processing test: {e}")
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        logger.exception("Unexpected error during prompt processing test.")
        raise HTTPException(status_code=500, detail="An unexpected internal server error occurred.")


class OllamaConnectionParams(BaseModel):
    ollama_api_url: str

@router.post("/api/v1/ollama/list-models")
async def list_ollama_models(params: OllamaConnectionParams):
    """
    Connects to a given Ollama server URL and fetches the list of available models.
    Acts as a proxy to avoid CORS issues and exposing the Ollama server directly.
    """
    if not params.ollama_api_url:
        raise HTTPException(status_code=400, detail="Ollama API URL cannot be empty.")
    
    # We instantiate a temporary client just for this check
    try:
        # We provide a dummy model name, it's not used for listing models
        client = OllamaClient(api_url=params.ollama_api_url, model_name="dummy")
        models = await client.list_models()
        await client.close()
        return {"models": models}
    except OllamaError as e:
        logger.error(f"Failed to connect to Ollama at {params.ollama_api_url}: {e}")
        raise HTTPException(status_code=503, detail=f"Failed to connect or list models: {e}")
    except ValueError:
            raise HTTPException(status_code=400, detail="Invalid Ollama API URL provided.")


# --- MCP JSON-RPC Endpoint ---

def create_error_response(request_id: JsonRpcId, code: int, message: str) -> JSONResponse:
    """Creates a JSON-RPC 2.0 error response."""
    error = JsonRpcError(code=code, message=message)
    response_model = JsonRpcResponse(error=error, id=request_id)
    return JSONResponse(status_code=200, content=response_model.model_dump(exclude_none=True))

@router.post("/mcp")
async def mcp_endpoint(request: Request, db: Session = Depends(get_db)):
    try:
        rpc_request = JsonRpcRequest.model_validate(await request.json())
    except Exception:
        return create_error_response(None, -32700, "Invalid JSON received.")

    request_id = rpc_request.id

    if rpc_request.method == "tools/list":
        # ... (contenu inchangé)
        tool_def = copy.deepcopy(GENERATE_IMAGE_TOOL_DEF)
        styles = crud.get_styles(db)
        render_types = crud.get_render_types(db)
        style_names = [s.name for s in styles]
        render_type_names = [rt.name for rt in render_types]
        if style_names:
            tool_def["inputSchema"]["properties"]["style_names"]["enum"] = style_names
        if render_type_names:
            tool_def["inputSchema"]["properties"]["render_type"]["enum"] = render_type_names
        return JsonRpcResponse(result={"tools": [tool_def]}, id=request_id)

    if rpc_request.method == "tools/call":
        start_time = time.monotonic()
        log_data = {
            "positive_prompt": "", "negative_prompt": "", "render_type_name": None,
            "style_names": None, "aspect_ratio": None, "seed": None, "llm_enhanced": False,
            "status": "FAILED", "duration_ms": None, "error_message": None,
            "image_filename": None, "comfyui_instance_id": None
        }

        try:
            params = ToolCallParams.model_validate(rpc_request.params)
            args = params.arguments

            log_data.update({
                "aspect_ratio": args.aspect_ratio,
                "llm_enhanced": args.enhance_prompt,
                "style_names": ", ".join(args.style_names) if args.style_names else None,
                "positive_prompt": args.prompt,
                "negative_prompt": args.negative_prompt
            })

            if params.name != "generate_image":
                raise ValueError(f"Tool '{params.name}' not found.")

            final_prompt, final_negative_prompt, final_render_type = await _process_prompts(args, db)
            log_data.update({
                "positive_prompt": final_prompt,
                "negative_prompt": final_negative_prompt,
                "render_type_name": final_render_type
            })

            final_args = args.model_copy(update={'prompt': final_prompt, 'negative_prompt': final_negative_prompt})

            db_settings = crud.get_all_settings(db)
            output_url_base = db_settings.get("OUTPUT_URL_BASE")
            if not output_url_base:
                raise ValueError("OUTPUT_URL_BASE is not configured in settings.")

            # --- Load Balancing Logic ---
            active_instances = crud.get_all_active_comfyui_instances(db)
            if not active_instances:
                raise ValueError("No active ComfyUI servers are configured.")

            target_render_type_name = final_render_type
            if not target_render_type_name:
                default_rt = crud.get_default_render_type(db)
                if default_rt: target_render_type_name = default_rt.name
            
            compatible_instances = []
            if target_render_type_name:
                for inst in active_instances:
                    if any(rt.name == target_render_type_name for rt in inst.compatible_render_types):
                        compatible_instances.append(inst)
                logger.info(f"Found {len(compatible_instances)} active instances compatible with '{target_render_type_name}'.")
            else:
                compatible_instances = active_instances
                logger.info(f"No specific render type. Considering all {len(compatible_instances)} active instances.")

            if not compatible_instances:
                raise ValueError(f"No active ComfyUI server is compatible with render type '{target_render_type_name}'.")
            
            async def get_instance_queue_size(instance):
                client = ComfyUIClient(api_url=instance.base_url, default_workflow_path="dummy", generation_timeout=10)
                try:
                    size = await client.get_queue_size()
                    return (instance, size)
                except ComfyUIConnectionError:
                    logger.warning(f"Failed to check queue for instance '{instance.name}'. Skipping.")
                    return (instance, float('inf'))

            tasks = [get_instance_queue_size(inst) for inst in compatible_instances]
            queue_sizes = await asyncio.gather(*tasks)

            valid_queues = [qs for qs in queue_sizes if qs[1] != float('inf')]
            if not valid_queues:
                raise ValueError("Could not connect to any compatible ComfyUI servers to check status.")

            selected_instance, min_queue = min(valid_queues, key=lambda item: item[1])
            
            logger.info(
                f"Selected instance '{selected_instance.name}' ({selected_instance.base_url}) "
                f"with queue size: {min_queue} for the task."
            )
            
            log_data["comfyui_instance_id"] = selected_instance.id
            
            workflow_to_use = None
            default_workflow_path_from_db = None

            if final_render_type:
                render_type_obj = crud.get_render_type_by_name(db, name=final_render_type)
                if not render_type_obj: raise ValueError(f"Render type '{final_render_type}' not found.")
                workflow_to_use = render_type_obj.workflow_filename
                logger.info(f"Using workflow: '{workflow_to_use}' for render type '{final_render_type}'")
            else:
                default_render_type = crud.get_default_render_type(db)
                if not default_render_type: raise ValueError("No default workflow is configured.")
                default_workflow_path_from_db = default_render_type.workflow_filename
                logger.info(f"Using default workflow from database: '{default_workflow_path_from_db}'")

            comfyui_client = ComfyUIClient(
                api_url=selected_instance.base_url,
                default_workflow_path=f"/app/workflows/{default_workflow_path_from_db}" if default_workflow_path_from_db else "/app/workflows/workflow_api.json",
                generation_timeout=settings.comfyui_generation_timeout
            )
            
            logger.info(f"Calling ComfyUI client to generate image on {selected_instance.base_url}.")
            image_url = await comfyui_client.generate_image(
                args=final_args, output_dir_path="/app/outputs",
                output_url_base=output_url_base, workflow_filename=workflow_to_use
            )
            
            log_data.update({
                "status": "SUCCESS",
                "image_filename": image_url.split('/')[-1],
                "duration_ms": int((time.monotonic() - start_time) * 1000)
            })
            _log_generation_result(db, log_data)
            
            # REVERT FIX: Return a list containing a single content object. This is the correct format.
            content_result = {"content": [{"type": "image", "source": image_url}]}
            return JsonRpcResponse(result=content_result, id=request_id)

        except ValidationError as e:
            error_message = f"Invalid parameters: {e}"
            log_data.update({
                "error_message": error_message,
                "duration_ms": int((time.monotonic() - start_time) * 1000)
            })
            _log_generation_result(db, log_data)
            return create_error_response(request_id, -32602, error_message)
        except ValueError as e:
            error_message = str(e)
            log_data.update({
                "error_message": error_message,
                "duration_ms": int((time.monotonic() - start_time) * 1000)
            })
            _log_generation_result(db, log_data)
            return create_error_response(request_id, -32000, error_message)
        except (OllamaError, ComfyUIError) as e:
            logger.error(f"Service error during 'tools/call': {e}", exc_info=True)
            error_message = f"Service error: {e}"
            log_data.update({
                "error_message": error_message,
                "duration_ms": int((time.monotonic() - start_time) * 1000)
            })
            _log_generation_result(db, log_data)
            return create_error_response(request_id, -32000, error_message)
        except Exception as e:
            logger.exception("Unexpected internal server error during 'tools/call'.")
            error_message = f"Internal server error: {str(e)}"
            log_data.update({
                "error_message": error_message,
                "duration_ms": int((time.monotonic() - start_time) * 1000)
            })
            _log_generation_result(db, log_data)
            return create_error_response(request_id, -32603, "Internal server error.")
    
    return create_error_response(request_id, -32601, f"Method '{rpc_request.method}' not found.")