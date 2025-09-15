# app/api/mcp_routes.py
from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import JSONResponse
from pydantic import ValidationError, BaseModel
from sqlalchemy.orm import Session
import logging
import time
from typing import Optional

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
from ..services.comfyui_client import ComfyUIClient, ComfyUIError
from ..services.ollama_client import OllamaClient, OllamaError
from ..database.session import get_db
from ..database import crud

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


# --- Web UI Helper API Endpoints ---

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
        return JsonRpcResponse(result={"tools": [GENERATE_IMAGE_TOOL_DEF]}, id=request_id)

    if rpc_request.method == "tools/call":
        response_to_send = None
        
        # Variables for the generation log, initialized with defaults
        log_status = "FAILED"
        log_duration_ms = None
        log_error_message = None
        log_image_filename = None
        comfyui_instance_id = None
        final_prompt = ""
        final_negative_prompt = ""
        log_render_type = None
        log_style_names = None
        log_aspect_ratio = None
        log_llm_enhanced = False
        start_time = None

        try:
            params = ToolCallParams.model_validate(rpc_request.params)
            args = params.arguments

            # As soon as we have args, populate the log variables
            log_aspect_ratio = args.aspect_ratio
            log_llm_enhanced = args.enhance_prompt
            log_style_names = ", ".join(args.style_names) if args.style_names else None

            # Store original prompts for logging in case processing fails
            final_prompt = args.prompt
            final_negative_prompt = args.negative_prompt

            if params.name != "generate_image":
                raise ValueError(f"Tool '{params.name}' not found.")

            final_prompt, final_negative_prompt, final_render_type = await _process_prompts(args, db)
            log_render_type = final_render_type

            final_args = args.model_copy(update={
                'prompt': final_prompt,
                'negative_prompt': final_negative_prompt
            })

            db_settings = crud.get_all_settings(db)
            output_url_base = db_settings.get("OUTPUT_URL_BASE")
            if not output_url_base:
                raise ValueError("OUTPUT_URL_BASE is not configured in settings.")

            active_instance = crud.get_active_comfyui_instance(db)
            if not active_instance:
                raise ValueError("No active ComfyUI server is configured.")
            comfyui_instance_id = active_instance.id
            
            workflow_to_use = None
            default_workflow_path_from_db = None

            if final_render_type: # Use the potentially updated render type
                render_type_obj = crud.get_render_type_by_name(db, name=final_render_type)
                if not render_type_obj:
                    raise ValueError(f"Render type '{final_render_type}' not found.")
                workflow_to_use = render_type_obj.workflow_filename
                logger.info(f"Using workflow: '{workflow_to_use}' for render type '{final_render_type}'")
            else:
                # If no render type is specified, find the default one in the database
                default_render_type = crud.get_default_render_type(db)
                if not default_render_type:
                    raise ValueError("No default workflow is configured in the Render Types settings.")
                default_workflow_path_from_db = default_render_type.workflow_filename
                logger.info(f"Using default workflow from database: '{default_workflow_path_from_db}'")

            # The default_workflow_path in the client is now a fallback for a fallback.
            # The primary default is determined here.
            comfyui_client = ComfyUIClient(
                api_url=active_instance.base_url,
                default_workflow_path=f"/app/workflows/{default_workflow_path_from_db}" if default_workflow_path_from_db else "/app/workflows/workflow_api.json"
            )
            
            start_time = time.monotonic()
            logger.info("Calling ComfyUI client to generate image.")
            image_url = await comfyui_client.generate_image(
                args=final_args,
                output_dir_path="/app/outputs",
                output_url_base=output_url_base,
                workflow_filename=workflow_to_use
            )
            
            log_status = "SUCCESS"
            log_image_filename = image_url.split('/')[-1]
            # Revert to the standard MCP format. The result is an array of content parts.
            content_result = {"content": [{"type": "text", "text": image_url}]}
            response_to_send = JsonRpcResponse(result=content_result, id=request_id)

        except ValidationError as e:
            log_error_message = f"Invalid parameters: {e}"
            response_to_send = create_error_response(request_id, -32602, log_error_message)
        except ValueError as e:
            log_error_message = str(e)
            response_to_send = create_error_response(request_id, -32000, log_error_message)
        except (OllamaError, ComfyUIError) as e:
            logger.error(f"Service error during 'tools/call': {e}")
            log_error_message = f"Service error: {e}"
            response_to_send = create_error_response(request_id, -32000, log_error_message)
        except Exception as e:
            logger.exception("Unexpected internal server error during 'tools/call'.")
            log_error_message = f"Internal server error: {str(e)}"
            response_to_send = create_error_response(request_id, -32603, "Internal server error.")
        finally:
            if start_time:
                log_duration_ms = int((time.monotonic() - start_time) * 1000)
            
            log_entry = GenerationLogCreate(
                positive_prompt=final_prompt,
                negative_prompt=final_negative_prompt,
                render_type_name=log_render_type,
                style_names=log_style_names,
                aspect_ratio=log_aspect_ratio,
                seed=None, # Seed is not yet retrievable from ComfyUI client
                llm_enhanced=log_llm_enhanced,
                status=log_status,
                duration_ms=log_duration_ms,
                error_message=log_error_message,
                image_filename=log_image_filename,
                comfyui_instance_id=comfyui_instance_id
            )
            crud.create_generation_log(db, log=log_entry)
            
            return response_to_send
    
    return create_error_response(request_id, -32601, f"Method '{rpc_request.method}' not found.")