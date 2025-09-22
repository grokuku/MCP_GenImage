# app/web/web_routes.py
# app/web/web_routes.py
from pathlib import Path
from typing import List, Optional
from fastapi import APIRouter, Request, Depends, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
import logging
import collections

from ..database import crud
from ..database.session import get_db
from .. import schemas

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

    return templates.TemplateResponse(
        "test_generation.html",
        {
            "request": request,
            "title": "Test Tools",
            "styles": styles,
            "render_types_gen": render_types_gen,
            "render_types_upscale": render_types_upscale,
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


# --- General & Ollama Settings Management ---

@router.get("/settings/ollama", response_class=HTMLResponse)
async def manage_ollama_settings(request: Request, db: Session = Depends(get_db)):
    """
    Displays the page for managing Ollama and other general settings.
    """
    settings = crud.get_all_settings(db)
    return templates.TemplateResponse(
        "manage_ollama.html",
        {
            "request": request, "title": "General & Ollama Settings",
            "active_page": "ollama_settings",
            "settings": {
                "output_url_base": settings.get("OUTPUT_URL_BASE", ""),
                "default_upscale_denoise": settings.get("DEFAULT_UPSCALE_DENOISE", "0.2"),
                "ollama_api_url": settings.get("OLLAMA_API_URL", ""),
                "ollama_model_name": settings.get("OLLAMA_MODEL_NAME", ""),
                "ollama_keep_alive": settings.get("OLLAMA_KEEP_ALIVE", "5m"),
                "ollama_context_window": settings.get("OLLAMA_CONTEXT_WINDOW", "2048"),
            }
        }
    )


@router.post("/settings/ollama", response_class=RedirectResponse)
async def handle_update_ollama_settings(
    db: Session = Depends(get_db),
    output_url_base: str = Form(""),
    default_upscale_denoise: str = Form("0.2"),
    ollama_api_url: str = Form(""),
    ollama_model_name: str = Form(""),
    ollama_keep_alive: str = Form("5m"),
    ollama_context_window: str = Form("2048")
):
    """
    Handles updating Ollama and other general settings in the database.
    """
    settings_to_update = {
        "OUTPUT_URL_BASE": output_url_base.strip(),
        "DEFAULT_UPSCALE_DENOISE": default_upscale_denoise.strip(),
        "OLLAMA_API_URL": ollama_api_url.strip(),
        "OLLAMA_MODEL_NAME": ollama_model_name.strip(),
        "OLLAMA_KEEP_ALIVE": ollama_keep_alive.strip(),
        "OLLAMA_CONTEXT_WINDOW": ollama_context_window.strip()
    }
    crud.update_settings(db, settings_data=settings_to_update)
    return RedirectResponse(url="/settings/ollama", status_code=303)