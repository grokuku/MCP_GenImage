# app/database/crud.py
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func
from typing import Optional, List, Literal

from . import models
from .. import schemas


# --- RenderType CRUD Operations ---

def get_render_types(db: Session, visible_only: bool = False):
    """
    Retrieves all render types from the database.
    If visible_only is True, retrieves only those marked as visible.
    """
    query = db.query(models.RenderType)
    if visible_only:
        query = query.filter(models.RenderType.is_visible == True)
    return query.order_by(models.RenderType.name).all()


def get_render_type_by_id(db: Session, render_type_id: int):
    """Retrieves a single render type by its ID."""
    return db.query(models.RenderType).filter(models.RenderType.id == render_type_id).first()


def get_render_type_by_name(db: Session, name: str):
    """Retrieves a single render type by its unique name."""
    return db.query(models.RenderType).filter(models.RenderType.name == name).first()


def get_default_render_type_for_generation(db: Session) -> Optional[models.RenderType]:
    """Retrieves the default render type for the 'image_generation' mode."""
    return db.query(models.RenderType).filter(models.RenderType.is_default_for_generation == True).first()


def get_default_render_type_for_upscale(db: Session) -> Optional[models.RenderType]:
    """Retrieves the default render type for the 'upscale' mode."""
    return db.query(models.RenderType).filter(models.RenderType.is_default_for_upscale == True).first()


def create_render_type(db: Session, render_type: schemas.RenderTypeCreate):
    """Creates a new render type in the database."""
    db_render_type = models.RenderType(
        name=render_type.name,
        workflow_filename=render_type.workflow_filename,
        prompt_examples=render_type.prompt_examples,
        is_visible=render_type.is_visible,
        generation_mode=render_type.generation_mode
    )
    db.add(db_render_type)
    db.commit()
    db.refresh(db_render_type)
    return db_render_type


def update_render_type(
    db: Session,
    render_type_id: int,
    render_type: schemas.RenderTypeCreate
):
    """Updates an existing render type."""
    db_render_type = get_render_type_by_id(db, render_type_id)
    if not db_render_type:
        return None
    
    db_render_type.name = render_type.name
    db_render_type.workflow_filename = render_type.workflow_filename
    db_render_type.prompt_examples = render_type.prompt_examples
    db_render_type.is_visible = render_type.is_visible
    db_render_type.generation_mode = render_type.generation_mode
    
    db.commit()
    db.refresh(db_render_type)
    return db_render_type


def set_default_render_type_for_mode(
    db: Session,
    render_type_id: int,
    mode: Literal["generation", "upscale"]
) -> Optional[models.RenderType]:
    """
    Sets a specific render type as the default for a given mode,
    ensuring all others are unset for that mode.
    """
    target_render_type = get_render_type_by_id(db, render_type_id)
    if not target_render_type:
        return None

    if mode == "generation":
        if target_render_type.generation_mode != "image_generation":
            return None
        current_default = get_default_render_type_for_generation(db)
        if current_default:
            current_default.is_default_for_generation = False
        target_render_type.is_default_for_generation = True

    elif mode == "upscale":
        if target_render_type.generation_mode != "upscale":
            return None
        current_default = get_default_render_type_for_upscale(db)
        if current_default:
            current_default.is_default_for_upscale = False
        target_render_type.is_default_for_upscale = True

    db.commit()
    db.refresh(target_render_type)
    return target_render_type


def delete_render_type(db: Session, render_type_id: int):
    """Deletes a render type from the database by its ID."""
    db_render_type = db.query(models.RenderType).filter(models.RenderType.id == render_type_id).first()
    if db_render_type:
        db.delete(db_render_type)
        db.commit()
        return True
    return False


# --- Style CRUD Operations ---

def get_styles(db: Session):
    """
    Retrieves all styles from the database, ordered by category then name.
    Eagerly loads compatible and default render types.
    """
    return db.query(models.Style).options(
        joinedload(models.Style.compatible_render_types),
        joinedload(models.Style.default_render_type)
    ).order_by(models.Style.category, models.Style.name).all()


def get_style_by_name(db: Session, name: str):
    """
    Retrieves a single style by its unique name.
    Eagerly loads compatible and default render types.
    """
    return db.query(models.Style).options(
        joinedload(models.Style.compatible_render_types),
        joinedload(models.Style.default_render_type)
    ).filter(models.Style.name == name).first()


def get_style_by_id(db: Session, style_id: int):
    """
    Retrieves a single style by its ID.
    Eagerly loads compatible and default render types.
    """
    return db.query(models.Style).options(
        joinedload(models.Style.compatible_render_types),
        joinedload(models.Style.default_render_type)
    ).filter(models.Style.id == style_id).first()


def get_default_styles(db: Session) -> List[models.Style]:
    """Retrieves all styles marked as default."""
    return db.query(models.Style).filter(models.Style.is_default == True).all()


def toggle_style_default_status(db: Session, style_id: int) -> Optional[models.Style]:
    """Toggles the is_default status of a specific style."""
    db_style = get_style_by_id(db, style_id)
    if not db_style:
        return None
    db_style.is_default = not db_style.is_default
    db.commit()
    db.refresh(db_style)
    return db_style


def create_style(db: Session, style: schemas.StyleCreate):
    """Creates a new style in the database."""
    compatible_types = []
    if style.compatible_render_type_ids:
        compatible_types = db.query(models.RenderType).filter(
            models.RenderType.id.in_(style.compatible_render_type_ids)
        ).all()

    db_style = models.Style(
        name=style.name, category=style.category,
        prompt_template=style.prompt_template,
        negative_prompt_template=style.negative_prompt_template,
        default_render_type_id=style.default_render_type_id,
        compatible_render_types=compatible_types
    )
    db.add(db_style)
    db.commit()
    db.refresh(db_style)
    return db_style


def update_style(
    db: Session,
    style_id: int,
    style: schemas.StyleCreate
):
    """Updates an existing style."""
    db_style = get_style_by_id(db, style_id)
    if not db_style:
        return None

    db_style.name = style.name
    db_style.category = style.category
    db_style.prompt_template = style.prompt_template
    db_style.negative_prompt_template = style.negative_prompt_template
    db_style.default_render_type_id = style.default_render_type_id

    compatible_types = []
    if style.compatible_render_type_ids:
        compatible_types = db.query(models.RenderType).filter(
            models.RenderType.id.in_(style.compatible_render_type_ids)
        ).all()
    db_style.compatible_render_types = compatible_types

    db.commit()
    db.refresh(db_style)
    return db_style


def delete_style(db: Session, style_id: int):
    """Deletes a style from the database by its ID."""
    db_style = db.query(models.Style).filter(models.Style.id == style_id).first()
    if db_style:
        db.delete(db_style)
        db.commit()
        return True
    return False


# --- Settings CRUD Operations ---

def get_all_settings(db: Session) -> dict[str, str]:
    """Retrieves all settings and returns them as a dictionary."""
    settings = db.query(models.Setting).all()
    return {setting.key: setting.value for setting in settings}


def update_settings(db: Session, settings_data: dict[str, str]):
    """Updates multiple settings in the database (upsert)."""
    for key, value in settings_data.items():
        db_setting = db.query(models.Setting).filter(models.Setting.key == key).first()
        if db_setting:
            db_setting.value = value
        else:
            db_setting = models.Setting(key=key, value=value)
            db.add(db_setting)
    db.commit()


# --- ComfyUI Instance CRUD Operations ---

def get_comfyui_instances(db: Session):
    """Retrieves all ComfyUI instances from the database."""
    return db.query(models.ComfyUIInstance).options(
        joinedload(models.ComfyUIInstance.compatible_render_types)
    ).order_by(models.ComfyUIInstance.name).all()


def get_comfyui_instance_by_id(db: Session, instance_id: int):
    """Retrieves a single ComfyUI instance by its ID."""
    return db.query(models.ComfyUIInstance).options(
        joinedload(models.ComfyUIInstance.compatible_render_types)
    ).filter(models.ComfyUIInstance.id == instance_id).first()


def get_all_active_comfyui_instances(db: Session) -> List[models.ComfyUIInstance]:
    """Retrieves all active ComfyUI instances for load balancing."""
    return db.query(models.ComfyUIInstance).options(
        joinedload(models.ComfyUIInstance.compatible_render_types)
    ).filter(models.ComfyUIInstance.is_active == True).all()


def create_comfyui_instance(
    db: Session,
    comfyui_instance: schemas.ComfyUIInstanceCreate
):
    """Creates a new ComfyUI instance."""
    exists = db.query(models.ComfyUIInstance).filter(
        (models.ComfyUIInstance.name == comfyui_instance.name) | (models.ComfyUIInstance.base_url == comfyui_instance.base_url)
    ).first()
    if exists:
        return None

    compatible_types = []
    if comfyui_instance.compatible_render_type_ids:
        compatible_types = db.query(models.RenderType).filter(
            models.RenderType.id.in_(comfyui_instance.compatible_render_type_ids)
        ).all()

    db_instance = models.ComfyUIInstance(
        name=comfyui_instance.name,
        base_url=comfyui_instance.base_url,
        compatible_render_types=compatible_types
    )
    db.add(db_instance)
    db.commit()
    db.refresh(db_instance)
    return db_instance


def update_comfyui_instance(
    db: Session,
    instance_id: int,
    comfyui_instance: schemas.ComfyUIInstanceCreate
):
    """Updates an existing ComfyUI instance."""
    db_instance = get_comfyui_instance_by_id(db, instance_id)
    if not db_instance:
        return None

    db_instance.name = comfyui_instance.name
    db_instance.base_url = comfyui_instance.base_url

    compatible_types = []
    if comfyui_instance.compatible_render_type_ids:
        compatible_types = db.query(models.RenderType).filter(
            models.RenderType.id.in_(comfyui_instance.compatible_render_type_ids)
        ).all()
    db_instance.compatible_render_types = compatible_types

    db.commit()
    db.refresh(db_instance)
    return db_instance


def toggle_comfyui_instance_active_status(db: Session, instance_id: int) -> Optional[models.ComfyUIInstance]:
    """Toggles the is_active status of a specific ComfyUI instance."""
    db_instance = get_comfyui_instance_by_id(db, instance_id)
    if not db_instance:
        return None
    
    db_instance.is_active = not db_instance.is_active
    db.commit()
    db.refresh(db_instance)
    return db_instance


def delete_comfyui_instance(db: Session, instance_id: int):
    """Deletes a ComfyUI instance from the database by its ID."""
    db_instance = db.query(models.ComfyUIInstance).filter(models.ComfyUIInstance.id == instance_id).first()
    if db_instance:
        db.delete(db_instance)
        db.commit()
        return True
    return False


# --- Ollama Instance CRUD Operations ---

def get_ollama_instances(db: Session):
    """Retrieves all Ollama instances from the database."""
    return db.query(models.OllamaInstance).order_by(models.OllamaInstance.name).all()


def get_ollama_instance_by_id(db: Session, instance_id: int):
    """Retrieves a single Ollama instance by its ID."""
    return db.query(models.OllamaInstance).filter(models.OllamaInstance.id == instance_id).first()


def create_ollama_instance(db: Session, instance: schemas.OllamaInstanceCreate):
    """Creates a new Ollama instance."""
    exists = db.query(models.OllamaInstance).filter(
        (models.OllamaInstance.name == instance.name) | (models.OllamaInstance.base_url == instance.base_url)
    ).first()
    if exists:
        return None

    db_instance = models.OllamaInstance(name=instance.name, base_url=instance.base_url)
    db.add(db_instance)
    db.commit()
    db.refresh(db_instance)
    return db_instance


def update_ollama_instance(db: Session, instance_id: int, instance: schemas.OllamaInstanceUpdate):
    """Updates an existing Ollama instance."""
    db_instance = get_ollama_instance_by_id(db, instance_id)
    if not db_instance:
        return None

    db_instance.name = instance.name
    db_instance.base_url = instance.base_url
    db.commit()
    db.refresh(db_instance)
    return db_instance


def toggle_ollama_instance_active_status(db: Session, instance_id: int) -> Optional[models.OllamaInstance]:
    """Toggles the is_active status of a specific Ollama instance."""
    db_instance = get_ollama_instance_by_id(db, instance_id)
    if not db_instance:
        return None
    
    db_instance.is_active = not db_instance.is_active
    db.commit()
    db.refresh(db_instance)
    return db_instance


def delete_ollama_instance(db: Session, instance_id: int):
    """Deletes an Ollama instance from the database by its ID."""
    db_instance = get_ollama_instance_by_id(db, instance_id)
    if db_instance:
        db.delete(db_instance)
        db.commit()
        return True
    return False


# --- DescriptionSettings CRUD Operations ---

def get_description_settings(db: Session) -> Optional[models.DescriptionSettings]:
    """Retrieves the description settings, creating them if they don't exist."""
    settings = db.query(models.DescriptionSettings).first()
    if not settings:
        settings = models.DescriptionSettings(id=1)
        db.add(settings)
        db.commit()
        db.refresh(settings)
    return settings


def update_description_settings(db: Session, settings_data: schemas.DescriptionSettingsUpdate):
    """Updates the description settings."""
    db_settings = get_description_settings(db)
    
    # Update fields from the Pydantic model
    update_data = settings_data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_settings, key, value)
    
    db.commit()
    db.refresh(db_settings)
    return db_settings


# --- GenerationLog CRUD Operations ---

def create_generation_log(db: Session, log: schemas.GenerationLogCreate) -> models.GenerationLog:
    """Creates a new generation log entry in the database."""
    db_log = models.GenerationLog(**log.model_dump())
    db.add(db_log)
    db.commit()
    db.refresh(db_log)
    return db_log


def get_generation_logs(db: Session, skip: int = 0, limit: int = 100) -> List[models.GenerationLog]:
    """Retrieves a list of generation logs, most recent first."""
    return db.query(models.GenerationLog).order_by(
        models.GenerationLog.timestamp.desc()
    ).offset(skip).limit(limit).all()


# --- Statistics Functions ---

def get_total_successful_generations_count(db: Session) -> int:
    """Counts the total number of successful generations."""
    return db.query(models.GenerationLog).filter(models.GenerationLog.status == 'SUCCESS').count()


def get_prompt_enhancement_count(db: Session) -> int:
    """Counts how many times the LLM prompt enhancement was used successfully."""
    return db.query(models.GenerationLog).filter(
        models.GenerationLog.status == 'SUCCESS',
        models.GenerationLog.llm_enhanced == True
    ).count()


def get_usage_count_by_render_type(db: Session) -> List[tuple[str, int]]:
    """Gets the count of successful generations grouped by render_type_name."""
    return db.query(
        models.GenerationLog.render_type_name,
        func.count(models.GenerationLog.id)
    ).filter(
        models.GenerationLog.status == 'SUCCESS'
    ).group_by(
        models.GenerationLog.render_type_name
    ).order_by(
        func.count(models.GenerationLog.id).desc()
    ).all()


def get_all_style_names_from_logs(db: Session) -> List[str]:
    """Retrieves all 'style_names' strings from successful generation logs."""
    results = db.query(models.GenerationLog.style_names).filter(
        models.GenerationLog.status == 'SUCCESS',
        models.GenerationLog.style_names.isnot(None),
        models.GenerationLog.style_names != ''
    ).all()
    return [row[0] for row in results]