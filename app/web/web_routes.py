# app/web/web_routes.py
from pathlib import Path
from typing import List, Optional
from fastapi import APIRouter, Request, Depends, Form, HTTPException, Body
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
import logging
import collections
import aiohttp
import base64

from ..database import crud
from ..database.session import get_db
from .. import schemas
from ..services.ollama_client import OllamaClient, OllamaError

# Setup logger
logger = logging.getLogger(__name__)

router = APIRouter()

# Define the absolute path to the templates directory for robustness.
TEMPLATE_DIR = Path(__file__).parent / "templates"
templates = Jinja2Templates(directory=TEMPLATE_DIR)


@router.get("/", response_class=HTMLResponse)
async def read_root():
    """
    Redirects the root URL to the new test generation page.
    """
    return RedirectResponse(url="/test-generation")


# --- Test Generation Page ---

@router.get("/test-generation", response_class=HTMLResponse)
async def test_generation_page(request: Request, db: Session = Depends(get_db)):
    """
    Displays the main interface for testing the image generation process.
    """
    styles = crud.get_styles(db)
    # For the test page, fetch ALL render types, including non-visible ones.
    render_types = crud.get_render_types(db)
    render_types_gen = [rt for rt in render_types if rt.generation_mode == 'image_generation']
    render_types_upscale = [rt for rt in render_types if rt.generation_mode == 'upscale']
    prompt_generator_styles = crud.get_allowed_styles_for_generator(db)

    return templates.TemplateResponse(
        "test_generation.html",
        {
            "request": request,
            "title": "Test Tools",
            "styles": styles,
            "render_types_gen": render_types_gen,
            "render_types_upscale": render_types_upscale,
            "prompt_generator_styles": prompt_generator_styles,
            "active_page": "test_generation"
        }
    )


# --- Statistics Page ---

@router.get("/statistics", response_class=HTMLResponse)
async def statistics_page(request: Request, db: Session = Depends(get_db)):
    """
    Displays the generation history and statistics.
    """
    total_count = crud.get_total_successful_generations_count(db)
    enhanced_count = crud.get_prompt_enhancement_count(db)
    render_type_usage = crud.get_usage_count_by_render_type(db)
    
    style_names_list = crud.get_all_style_names_from_logs(db)
    all_styles = [style.strip() for styles_str in style_names_list for style in styles_str.split(',')]
    style_usage = collections.Counter(all_styles)
    
    logs = crud.get_generation_logs(db, limit=100)
    
    return templates.TemplateResponse(
        "statistics.html",
        {
            "request": request,
            "title": "Generation Statistics",
            "logs": logs,
            "total_count": total_count,
            "enhanced_count": enhanced_count,
            "render_type_usage": render_type_usage,
            "style_usage": sorted(style_usage.items(), key=lambda item: item[1], reverse=True),
            "active_page": "statistics"
        }
    )


# --- Render Types Management ---

@router.get("/render-types", response_class=HTMLResponse)
async def manage_render_types(request: Request, db: Session = Depends(get_db)):
    """
    Displays the page for managing render types.
    """
    render_types = crud.get_render_types(db)
    return templates.TemplateResponse(
        "manage_render_types.html",
        {
            "request": request,
            "title": "Manage Render Types",
            "render_types": render_types,
            "active_page": "render_types"
        }
    )


@router.post("/render-types/add", response_class=RedirectResponse)
async def handle_add_render_type(
    name: str = Form(...),
    workflow_filename: str = Form(...),
    prompt_examples: str = Form(""),
    is_visible: bool = Form(False),
    generation_mode: str = Form(...),
    db: Session = Depends(get_db)
):
    """
    Handles the creation of a new render type.
    """
    if crud.get_render_type_by_name(db, name=name):
        logger.warning(f"Attempted to create a duplicate render type: {name}")
    else:
        render_type_data = schemas.RenderTypeCreate(
            name=name,
            workflow_filename=workflow_filename,
            prompt_examples=prompt_examples,
            is_visible=is_visible,
            generation_mode=generation_mode
        )
        crud.create_render_type(db, render_type=render_type_data)
    return RedirectResponse(url="/render-types", status_code=303)


@router.post("/render-types/update/{render_type_id}", response_class=RedirectResponse)
async def handle_update_render_type(
    render_type_id: int,
    name: str = Form(...),
    workflow_filename: str = Form(...),
    prompt_examples: str = Form(""),
    is_visible: bool = Form(False),
    generation_mode: str = Form(...),
    db: Session = Depends(get_db)
):
    """
    Handles updating an existing render type.
    """
    render_type_data = schemas.RenderTypeCreate(
        name=name,
        workflow_filename=workflow_filename,
        prompt_examples=prompt_examples,
        is_visible=is_visible,
        generation_mode=generation_mode
    )
    crud.update_render_type(
        db,
        render_type_id=render_type_id,
        render_type=render_type_data
    )
    return RedirectResponse(url="/render-types", status_code=303)


@router.post("/render-types/delete/{render_type_id}", response_class=RedirectResponse)
async def handle_delete_render_type(
    render_type_id: int,
    db: Session = Depends(get_db)
):
    """
    Handles the deletion of a render type.
    """
    crud.delete_render_type(db, render_type_id=render_type_id)
    return RedirectResponse(url="/render-types", status_code=303)


@router.post("/render-types/set-default/{render_type_id}/{mode}", response_class=RedirectResponse)
async def handle_set_default_render_type_for_mode(
    render_type_id: int,
    mode: str,
    db: Session = Depends(get_db)
):
    """
    Handles setting a render type as the default for a specific mode.
    """
    if mode not in ["generation", "upscale"]:
        raise HTTPException(status_code=400, detail="Invalid mode specified.")
    crud.set_default_render_type_for_mode(db, render_type_id=render_type_id, mode=mode)
    return RedirectResponse(url="/render-types", status_code=303)


# --- Styles Management ---

@router.get("/styles", response_class=HTMLResponse)
async def manage_styles(request: Request, db: Session = Depends(get_db)):
    """
    Displays the page for managing styles.
    """
    styles = crud.get_styles(db)
    render_types = crud.get_render_types(db)
    return templates.TemplateResponse(
        "manage_styles.html",
        {
            "request": request,
            "title": "Manage Styles",
            "styles": styles,
            "render_types": render_types,
            "active_page": "styles"
        }
    )


@router.post("/styles/add", response_class=RedirectResponse)
async def handle_add_style(
    db: Session = Depends(get_db),
    name: str = Form(...),
    category: str = Form(...),
    prompt_template: str = Form(...),
    negative_prompt_template: str = Form(""),
    compatible_render_types: List[int] = Form([]),
    default_render_type: Optional[int] = Form(None)
):
    """
    Handles the creation of a new style.
    """
    if crud.get_style_by_name(db, name=name):
        logger.warning(f"Attempted to create a duplicate style: {name}")
    else:
        style_data = schemas.StyleCreate(
            name=name, category=category, prompt_template=prompt_template,
            negative_prompt_template=negative_prompt_template,
            compatible_render_type_ids=compatible_render_types,
            default_render_type_id=default_render_type
        )
        crud.create_style(db=db, style=style_data)
    return RedirectResponse(url="/styles", status_code=303)


@router.post("/styles/update/{style_id}", response_class=RedirectResponse)
async def handle_update_style(
    style_id: int,
    db: Session = Depends(get_db),
    name: str = Form(...),
    category: str = Form(...),
    prompt_template: str = Form(...),
    negative_prompt_template: str = Form(""),
    compatible_render_types: List[int] = Form([]),
    default_render_type: Optional[int] = Form(None)
):
    """
    Handles updating an existing style.
    """
    style_data = schemas.StyleCreate(
        name=name, category=category, prompt_template=prompt_template,
        negative_prompt_template=negative_prompt_template,
        compatible_render_type_ids=compatible_render_types,
        default_render_type_id=default_render_type
    )
    crud.update_style(db=db, style_id=style_id, style=style_data)
    return RedirectResponse(url="/styles", status_code=303)


@router.post("/styles/delete/{style_id}", response_class=RedirectResponse)
async def handle_delete_style(
    style_id: int,
    db: Session = Depends(get_db)
):
    """
    Handles the deletion of a style.
    """
    crud.delete_style(db, style_id=style_id)
    return RedirectResponse(url="/styles", status_code=303)


@router.post("/styles/toggle-default/{style_id}", response_class=RedirectResponse)
async def handle_toggle_style_default(
    style_id: int,
    db: Session = Depends(get_db)
):
    """
    Handles toggling the is_default status of a style.
    """
    crud.toggle_style_default_status(db, style_id=style_id)
    return RedirectResponse(url="/styles", status_code=303)


# --- ComfyUI Settings Management ---

@router.get("/settings/comfyui", response_class=HTMLResponse)
async def manage_comfyui_settings(request: Request, db: Session = Depends(get_db)):
    """
    Displays the page for managing ComfyUI server instances.
    """
    instances = crud.get_comfyui_instances(db)
    all_render_types = crud.get_render_types(db)
    return templates.TemplateResponse(
        "manage_comfyui.html",
        {
            "request": request, "title": "Manage ComfyUI Instances",
            "active_page": "comfyui_settings", "instances": instances,
            "all_render_types": all_render_types
        }
    )

@router.post("/settings/comfyui/add", response_class=RedirectResponse)
async def handle_add_comfyui_instance(
    name: str = Form(...),
    base_url: str = Form(...),
    compatible_render_types: List[int] = Form([]),
    db: Session = Depends(get_db)
):
    """
    Handles adding a new ComfyUI instance.
    """
    instance_data = schemas.ComfyUIInstanceCreate(
        name=name, base_url=base_url.strip(),
        compatible_render_type_ids=compatible_render_types
    )
    if not crud.create_comfyui_instance(db, comfyui_instance=instance_data):
        logger.warning(f"Duplicate ComfyUI instance name or URL: {name} / {base_url}")
    return RedirectResponse(url="/settings/comfyui", status_code=303)


@router.post("/settings/comfyui/update/{instance_id}", response_class=RedirectResponse)
async def handle_update_comfyui_instance(
    instance_id: int,
    name: str = Form(...),
    base_url: str = Form(...),
    compatible_render_types: List[int] = Form([]),
    db: Session = Depends(get_db)
):
    """
    Handles updating an existing ComfyUI instance.
    """
    instance_data = schemas.ComfyUIInstanceCreate(
        name=name, base_url=base_url.strip(),
        compatible_render_type_ids=compatible_render_types
    )
    crud.update_comfyui_instance(
        db, instance_id=instance_id,
        comfyui_instance=instance_data
    )
    return RedirectResponse(url="/settings/comfyui", status_code=303)


@router.post("/settings/comfyui/toggle-active/{instance_id}", response_class=RedirectResponse)
async def handle_toggle_comfyui_active(
    instance_id: int,
    db: Session = Depends(get_db)
):
    """
    Handles toggling the is_active status of a ComfyUI instance.
    """
    crud.toggle_comfyui_instance_active_status(db, instance_id=instance_id)
    return RedirectResponse(url="/settings/comfyui", status_code=303)


@router.post("/settings/comfyui/delete/{instance_id}", response_class=RedirectResponse)
async def handle_delete_comfyui_instance(
    instance_id: int,
    db: Session = Depends(get_db)
):
    """
    Handles deleting a ComfyUI instance.
    """
    crud.delete_comfyui_instance(db, instance_id=instance_id)
    return RedirectResponse(url="/settings/comfyui", status_code=303)


# --- Ollama Instance Management ---

@router.get("/settings/ollama", response_class=HTMLResponse)
async def manage_ollama_settings(request: Request, db: Session = Depends(get_db)):
    """
    Displays the page for managing Ollama server instances.
    """
    instances = crud.get_ollama_instances(db)
    return templates.TemplateResponse(
        "manage_ollama.html",
        {
            "request": request, "title": "Manage Ollama Instances",
            "active_page": "ollama_settings", "instances": instances
        }
    )

@router.post("/settings/ollama/add", response_class=RedirectResponse)
async def handle_add_ollama_instance(
    name: str = Form(...),
    base_url: str = Form(...),
    db: Session = Depends(get_db)
):
    """Handles adding a new Ollama instance."""
    instance_data = schemas.OllamaInstanceCreate(name=name, base_url=base_url.strip())
    if not crud.create_ollama_instance(db, instance=instance_data):
        logger.warning(f"Duplicate Ollama instance name or URL: {name} / {base_url}")
    return RedirectResponse(url="/settings/ollama", status_code=303)

@router.post("/settings/ollama/update/{instance_id}", response_class=RedirectResponse)
async def handle_update_ollama_instance(
    instance_id: int,
    name: str = Form(...),
    base_url: str = Form(...),
    db: Session = Depends(get_db)
):
    """Handles updating an existing Ollama instance."""
    instance_data = schemas.OllamaInstanceUpdate(name=name, base_url=base_url.strip())
    crud.update_ollama_instance(db, instance_id=instance_id, instance=instance_data)
    return RedirectResponse(url="/settings/ollama", status_code=303)

@router.post("/settings/ollama/toggle-active/{instance_id}", response_class=RedirectResponse)
async def handle_toggle_ollama_active(
    instance_id: int,
    db: Session = Depends(get_db)
):
    """Handles toggling the is_active status of an Ollama instance."""
    crud.toggle_ollama_instance_active_status(db, instance_id=instance_id)
    return RedirectResponse(url="/settings/ollama", status_code=303)

@router.post("/settings/ollama/delete/{instance_id}", response_class=RedirectResponse)
async def handle_delete_ollama_instance(
    instance_id: int,
    db: Session = Depends(get_db)
):
    """Handles deleting an Ollama instance."""
    crud.delete_ollama_instance(db, instance_id=instance_id)
    return RedirectResponse(url="/settings/ollama", status_code=303)


# --- Description Tool Settings Management ---

@router.get("/settings/description", response_class=HTMLResponse)
async def manage_description_settings(request: Request, db: Session = Depends(get_db)):
    settings = crud.get_description_settings(db)
    ollama_instances = crud.get_ollama_instances(db)
    return templates.TemplateResponse(
        "manage_description.html",
        {
            "request": request, "title": "Describe Tool Settings",
            "active_page": "description_settings",
            "settings": settings,
            "ollama_instances": ollama_instances
        }
    )

@router.post("/settings/description", response_class=RedirectResponse)
async def handle_update_description_settings(
    db: Session = Depends(get_db),
    ollama_instance_id: Optional[int] = Form(None),
    model_name: str = Form(""),
    natural_prompt_template_en: str = Form(""),
    optimized_prompt_template_en: str = Form(""),
    natural_prompt_template_fr: str = Form(""),
    optimized_prompt_template_fr: str = Form("")
):
    settings_data = schemas.DescriptionSettingsUpdate(
        ollama_instance_id=ollama_instance_id, model_name=model_name,
        natural_prompt_template_en=natural_prompt_template_en,
        optimized_prompt_template_en=optimized_prompt_template_en,
        natural_prompt_template_fr=natural_prompt_template_fr,
        optimized_prompt_template_fr=optimized_prompt_template_fr
    )
    crud.update_description_settings(db, settings_data=settings_data)
    return RedirectResponse(url="/settings/description", status_code=303)


# --- Prompt Generator Settings Management ---

@router.get("/settings/prompt-generator", response_class=HTMLResponse)
async def manage_prompt_generator_settings(request: Request, db: Session = Depends(get_db)):
    """
    Displays the page for managing the prompt generator settings.
    """
    settings = crud.get_prompt_generator_settings(db)
    all_styles = crud.get_styles(db)
    allowed_style_ids = crud.get_prompt_generator_allowed_style_ids(db)
    return templates.TemplateResponse(
        "manage_prompt_generator.html",
        {
            "request": request,
            "title": "Prompt Generator Settings",
            "active_page": "prompt_generator_settings",
            "settings": settings,
            "all_styles": all_styles,
            "allowed_style_ids": allowed_style_ids,
        }
    )

@router.post("/settings/prompt-generator", response_class=RedirectResponse)
async def handle_update_prompt_generator_settings(
    db: Session = Depends(get_db),
    subjects_to_propose: int = Form(...),
    elements_to_propose: int = Form(...),
    elements_to_select: int = Form(...),
    variations_to_propose: int = Form(...),
    allowed_style_ids: List[int] = Form([])
):
    """
    Handles updating the prompt generator settings.
    """
    # Update numerical settings
    numerical_settings = schemas.PromptGeneratorSettingsUpdate(
        subjects_to_propose=subjects_to_propose,
        elements_to_propose=elements_to_propose,
        elements_to_select=elements_to_select,
        variations_to_propose=variations_to_propose,
    )
    crud.update_prompt_generator_settings(db, settings_data=numerical_settings)

    # Update allowed styles
    crud.update_prompt_generator_allowed_styles(db, style_ids=allowed_style_ids)

    return RedirectResponse(url="/settings/prompt-generator", status_code=303)


# --- General Settings Management ---

@router.get("/settings/general", response_class=HTMLResponse)
async def manage_general_settings(request: Request, db: Session = Depends(get_db)):
    """
    Displays the page for managing general application settings.
    """
    settings = crud.get_all_settings(db)
    ollama_instances = crud.get_ollama_instances(db)
    return templates.TemplateResponse(
        "settings_general.html",
        {
            "request": request, "title": "General Settings",
            "active_page": "general_settings",
            "ollama_instances": ollama_instances,
            "settings": {
                "output_url_base": settings.get("OUTPUT_URL_BASE", ""),
                "default_upscale_denoise": settings.get("DEFAULT_UPSCALE_DENOISE", "0.2"),
                "prompt_enhancement_ollama_instance_id": settings.get("PROMPT_ENHANCEMENT_OLLAMA_INSTANCE_ID"),
                "prompt_enhancement_model_name": settings.get("PROMPT_ENHANCEMENT_MODEL_NAME", ""),
            }
        }
    )

@router.post("/settings/general", response_class=RedirectResponse)
async def handle_update_general_settings(
    db: Session = Depends(get_db),
    output_url_base: str = Form(""),
    default_upscale_denoise: str = Form("0.2"),
    prompt_enhancement_ollama_instance_id: Optional[str] = Form(""),
    prompt_enhancement_model_name: str = Form("")
):
    """
    Handles updating general settings in the database.
    """
    settings_to_update = {
        "OUTPUT_URL_BASE": output_url_base.strip(),
        "DEFAULT_UPSCALE_DENOISE": default_upscale_denoise.strip(),
        "PROMPT_ENHANCEMENT_OLLAMA_INSTANCE_ID": prompt_enhancement_ollama_instance_id,
        "PROMPT_ENHANCEMENT_MODEL_NAME": prompt_enhancement_model_name.strip(),
    }
    crud.update_settings(db, settings_data=settings_to_update)
    return RedirectResponse(url="/settings/general", status_code=303)


# --- API Helper for Web UI ---

class OllamaApiUrlPayload(schemas.BaseModel):
    ollama_api_url: str

@router.post("/api/v1/ollama/list-models")
async def api_list_ollama_models(payload: OllamaApiUrlPayload):
    """
    API endpoint for the web UI to dynamically fetch models from an Ollama server.
    """
    if not payload.ollama_api_url:
        raise HTTPException(status_code=400, detail="Ollama API URL is required.")
    
    client = None
    try:
        # We instantiate the client with a dummy model name as it's not needed for listing models
        client = OllamaClient(api_url=payload.ollama_api_url, model_name="dummy")
        models = await client.list_models()
        return JSONResponse(content={"models": models})
    except OllamaError as e:
        logger.warning(f"Failed to list Ollama models for URL {payload.ollama_api_url}: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        if client:
            await client.close()

class DescribeTestPayload(schemas.BaseModel):
    image_url: str
    description_type: str
    language: str

@router.post("/api/v1/tools/test-describe")
async def api_test_describe_tool(payload: DescribeTestPayload, db: Session = Depends(get_db)):
    settings = crud.get_description_settings(db)
    if not settings or not settings.ollama_instance_id or not settings.model_name:
        raise HTTPException(status_code=400, detail="Describe tool is not configured in settings.")
    
    instance = crud.get_ollama_instance_by_id(db, settings.ollama_instance_id)
    if not instance or not instance.is_active:
        raise HTTPException(status_code=400, detail="The configured Ollama instance is not active or does not exist.")
    
    template_key = f"{payload.description_type}_prompt_template_{payload.language}"
    prompt_template = getattr(settings, template_key, None)
    if not prompt_template:
        raise HTTPException(status_code=400, detail="Invalid description type or language.")
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(payload.image_url) as response:
                response.raise_for_status()
                image_data = await response.read()
                image_base64 = base64.b64encode(image_data).decode('utf-8')
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to download or process image: {e}")
    
    client = None
    try:
        client = OllamaClient(api_url=instance.base_url, model_name=settings.model_name)
        description = await client.describe_image(prompt=prompt_template, image_base64=image_base64)
        return JSONResponse(content={"description": description})
    except OllamaError as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if client: await client.close()