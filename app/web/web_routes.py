from pathlib import Path
from typing import List, Optional
from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
import logging
import collections

from app.database import crud
from app.database.session import get_db

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
    render_types = crud.get_render_types(db)
    return templates.TemplateResponse(
        "test_generation.html",
        {
            "request": request,
            "title": "Test Generation",
            "styles": styles,
            "render_types": render_types,
            "active_page": "test_generation" # For nav highlighting
        }
    )


# --- Statistics Page ---

@router.get("/statistics", response_class=HTMLResponse)
async def statistics_page(request: Request, db: Session = Depends(get_db)):
    """
    Displays the generation history and statistics.
    """
    # --- Aggregate Statistics ---
    total_count = crud.get_total_successful_generations_count(db)
    enhanced_count = crud.get_prompt_enhancement_count(db)
    render_type_usage = crud.get_usage_count_by_render_type(db)
    
    # Process style usage
    style_names_list = crud.get_all_style_names_from_logs(db)
    all_styles = [style.strip() for styles_str in style_names_list for style in styles_str.split(',')]
    style_usage = collections.Counter(all_styles)
    
    # --- Detailed History ---
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
            "active_page": "render_types" # For nav highlighting
        }
    )


@router.post("/render-types/add", response_class=RedirectResponse)
async def handle_add_render_type(
    name: str = Form(...),
    workflow_filename: str = Form(...),
    prompt_examples: str = Form(""),
    db: Session = Depends(get_db)
):
    """
    Handles the creation of a new render type.
    """
    existing_type = crud.get_render_type_by_name(db, name=name)
    if existing_type:
        logger.warning(f"Attempted to create a duplicate render type: {name}")
    else:
        crud.create_render_type(
            db,
            name=name,
            workflow_filename=workflow_filename,
            prompt_examples=prompt_examples
        )
    return RedirectResponse(url="/render-types", status_code=303)


@router.post("/render-types/update/{render_type_id}", response_class=RedirectResponse)
async def handle_update_render_type(
    render_type_id: int,
    name: str = Form(...),
    workflow_filename: str = Form(...),
    prompt_examples: str = Form(""),
    db: Session = Depends(get_db)
):
    """
    Handles updating an existing render type.
    """
    crud.update_render_type(
        db,
        render_type_id=render_type_id,
        name=name,
        workflow_filename=workflow_filename,
        prompt_examples=prompt_examples
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


@router.post("/render-types/set-default/{render_type_id}", response_class=RedirectResponse)
async def handle_set_default_render_type(
    render_type_id: int,
    db: Session = Depends(get_db)
):
    """
    Handles setting a render type as the default.
    """
    crud.set_default_render_type(db, render_type_id=render_type_id)
    return RedirectResponse(url="/render-types", status_code=303)


# --- Styles Management ---

@router.get("/styles", response_class=HTMLResponse)
async def manage_styles(request: Request, db: Session = Depends(get_db)):
    """
    Displays the page for managing styles.
    """
    styles = crud.get_styles(db)
    render_types = crud.get_render_types(db) # Fetch render types for the form
    return templates.TemplateResponse(
        "manage_styles.html",
        {
            "request": request,
            "title": "Manage Styles",
            "styles": styles,
            "render_types": render_types, # Pass them to the template
            "active_page": "styles" # For nav highlighting
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
    recommended_render_type: Optional[int] = Form(None)
):
    """
    Handles the creation of a new style.
    """
    existing_style = crud.get_style_by_name(db, name=name)
    if existing_style:
        logger.warning(f"Attempted to create a duplicate style: {name}")
    else:
        crud.create_style(
            db=db,
            name=name,
            category=category,
            prompt_template=prompt_template,
            negative_prompt_template=negative_prompt_template,
            compatible_render_type_ids=compatible_render_types,
            recommended_render_type_id=recommended_render_type
        )
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
    recommended_render_type: Optional[int] = Form(None)
):
    """
    Handles updating an existing style.
    """
    crud.update_style(
        db=db,
        style_id=style_id,
        name=name,
        category=category,
        prompt_template=prompt_template,
        negative_prompt_template=negative_prompt_template,
        compatible_render_type_ids=compatible_render_types,
        recommended_render_type_id=recommended_render_type
    )
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
    context = {
        "request": request,
        "title": "Manage ComfyUI Instances",
        "active_page": "comfyui_settings",
        "instances": instances
    }
    return templates.TemplateResponse("manage_comfyui.html", context)

@router.post("/settings/comfyui/add", response_class=RedirectResponse)
async def handle_add_comfyui_instance(
    name: str = Form(...),
    base_url: str = Form(...),
    db: Session = Depends(get_db)
):
    """
    Handles adding a new ComfyUI instance.
    """
    instance = crud.create_comfyui_instance(db, name=name, base_url=base_url.strip())
    if not instance:
        logger.warning(f"Attempted to create a ComfyUI instance with a duplicate name or URL: {name} / {base_url}")
        # In a real app, we might want to return a message to the user here.
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
    # Provide default values for the template if they don't exist in the DB
    context = {
        "request": request,
        "title": "General & Ollama Settings",
        "active_page": "ollama_settings",
        "settings": {
            "output_url_base": settings.get("OUTPUT_URL_BASE", ""),
            "ollama_api_url": settings.get("OLLAMA_API_URL", ""),
            "ollama_model_name": settings.get("OLLAMA_MODEL_NAME", ""),
            "ollama_keep_alive": settings.get("OLLAMA_KEEP_ALIVE", "5m"),
            "ollama_context_window": settings.get("OLLAMA_CONTEXT_WINDOW", "2048"),
        }
    }
    return templates.TemplateResponse("manage_ollama.html", context)


@router.post("/settings/ollama", response_class=RedirectResponse)
async def handle_update_ollama_settings(
    db: Session = Depends(get_db),
    output_url_base: str = Form(""),
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
        "OLLAMA_API_URL": ollama_api_url.strip(),
        "OLLAMA_MODEL_NAME": ollama_model_name.strip(),
        "OLLAMA_KEEP_ALIVE": ollama_keep_alive.strip(),
        "OLLAMA_CONTEXT_WINDOW": ollama_context_window.strip()
    }
    crud.update_settings(db, settings_data=settings_to_update)
    return RedirectResponse(url="/settings/ollama", status_code=303)