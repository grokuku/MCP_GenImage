from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload
from typing import Optional, List

from . import models
from .. import schemas


# --- RenderType CRUD Operations ---

def get_render_types(db: Session):
    """
    Retrieves all render types from the database.
    """
    return db.query(models.RenderType).order_by(models.RenderType.name).all()


def get_render_type_by_id(db: Session, render_type_id: int):
    """
    Retrieves a single render type by its ID.
    """
    return db.query(models.RenderType).filter(models.RenderType.id == render_type_id).first()


def get_render_type_by_name(db: Session, name: str):
    """
    Retrieves a single render type by its unique name.
    """
    return db.query(models.RenderType).filter(models.RenderType.name == name).first()


def get_default_render_type(db: Session) -> Optional[models.RenderType]:
    """
    Retrieves the render type marked as default.
    """
    return db.query(models.RenderType).filter(models.RenderType.is_default == True).first()


def create_render_type(db: Session, name: str, workflow_filename: str, prompt_examples: str):
    """
    Creates a new render type in the database.
    """
    db_render_type = models.RenderType(
        name=name,
        workflow_filename=workflow_filename,
        prompt_examples=prompt_examples
    )
    db.add(db_render_type)
    db.commit()
    db.refresh(db_render_type)
    return db_render_type


def update_render_type(
    db: Session,
    render_type_id: int,
    name: str,
    workflow_filename: str,
    prompt_examples: str
):
    """
    Updates an existing render type.
    """
    db_render_type = get_render_type_by_id(db, render_type_id)
    if not db_render_type:
        return None
    
    db_render_type.name = name
    db_render_type.workflow_filename = workflow_filename
    db_render_type.prompt_examples = prompt_examples
    
    db.commit()
    db.refresh(db_render_type)
    return db_render_type


def set_default_render_type(db: Session, render_type_id: int) -> Optional[models.RenderType]:
    """
    Sets a specific render type as the default one.
    Ensures any other render type is unset as default.
    """
    # First, find the render type to be set as default
    target_render_type = get_render_type_by_id(db, render_type_id)
    if not target_render_type:
        return None

    # Second, find the current default render type, if any
    current_default = get_default_render_type(db)
    
    # If there's a current default and it's not the target, unset it
    if current_default and current_default.id != target_render_type.id:
        current_default.is_default = False
    
    # Set the target as the new default
    target_render_type.is_default = True
    
    db.commit()
    db.refresh(target_render_type)
    return target_render_type


def delete_render_type(db: Session, render_type_id: int):
    """
    Deletes a render type from the database by its ID.
    """
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
    Eagerly loads compatible and recommended render types.
    """
    return db.query(models.Style).options(
        joinedload(models.Style.compatible_render_types),
        joinedload(models.Style.recommended_render_type)
    ).order_by(models.Style.category, models.Style.name).all()


def get_style_by_name(db: Session, name: str):
    """
    Retrieves a single style by its unique name.
    Eagerly loads compatible and recommended render types.
    """
    return db.query(models.Style).options(
        joinedload(models.Style.compatible_render_types),
        joinedload(models.Style.recommended_render_type)
    ).filter(models.Style.name == name).first()


def get_style_by_id(db: Session, style_id: int):
    """
    Retrieves a single style by its ID.
    Eagerly loads compatible and recommended render types.
    """
    return db.query(models.Style).options(
        joinedload(models.Style.compatible_render_types),
        joinedload(models.Style.recommended_render_type)
    ).filter(models.Style.id == style_id).first()


def get_default_styles(db: Session) -> List[models.Style]:
    """
    Retrieves all styles marked as default.
    """
    return db.query(models.Style).filter(models.Style.is_default == True).all()


def toggle_style_default_status(db: Session, style_id: int) -> Optional[models.Style]:
    """
    Toggles the is_default status of a specific style.
    """
    db_style = get_style_by_id(db, style_id)
    if not db_style:
        return None
    
    db_style.is_default = not db_style.is_default
    db.commit()
    db.refresh(db_style)
    return db_style


def create_style(
    db: Session,
    name: str,
    category: str,
    prompt_template: str,
    negative_prompt_template: str,
    compatible_render_type_ids: List[int],
    recommended_render_type_id: Optional[int]
):
    """
    Creates a new style in the database and links it to its
    compatible and recommended render types.
    """
    compatible_types = []
    if compatible_render_type_ids:
        compatible_types = db.query(models.RenderType).filter(
            models.RenderType.id.in_(compatible_render_type_ids)
        ).all()

    db_style = models.Style(
        name=name,
        category=category,
        prompt_template=prompt_template,
        negative_prompt_template=negative_prompt_template,
        recommended_render_type_id=recommended_render_type_id,
        compatible_render_types=compatible_types
    )
    db.add(db_style)
    db.commit()
    db.refresh(db_style)
    return db_style


def update_style(
    db: Session,
    style_id: int,
    name: str,
    category: str,
    prompt_template: str,
    negative_prompt_template: str,
    compatible_render_type_ids: List[int],
    recommended_render_type_id: Optional[int]
):
    """
    Updates an existing style, including its relationships
    to render types.
    """
    db_style = get_style_by_id(db, style_id)
    if not db_style:
        return None

    # Update scalar fields
    db_style.name = name
    db_style.category = category
    db_style.prompt_template = prompt_template
    db_style.negative_prompt_template = negative_prompt_template
    db_style.recommended_render_type_id = recommended_render_type_id

    # Update many-to-many relationship
    compatible_types = []
    if compatible_render_type_ids:
        compatible_types = db.query(models.RenderType).filter(
            models.RenderType.id.in_(compatible_render_type_ids)
        ).all()
    db_style.compatible_render_types = compatible_types

    db.commit()
    db.refresh(db_style)
    return db_style


def delete_style(db: Session, style_id: int):
    """
    Deletes a style from the database by its ID.
    """
    db_style = db.query(models.Style).filter(models.Style.id == style_id).first()
    if db_style:
        db.delete(db_style)
        db.commit()
        return True
    return False


# --- Settings CRUD Operations ---

def get_all_settings(db: Session) -> dict[str, str]:
    """
    Retrieves all settings and returns them as a dictionary.
    """
    settings = db.query(models.Setting).all()
    return {setting.key: setting.value for setting in settings}


def update_settings(db: Session, settings_data: dict[str, str]):
    """
    Updates multiple settings in the database (upsert).
    """
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
    """
    Retrieves all ComfyUI instances from the database, eager loading
    their compatible render types.
    """
    return db.query(models.ComfyUIInstance).options(
        joinedload(models.ComfyUIInstance.compatible_render_types)
    ).order_by(models.ComfyUIInstance.name).all()


def get_comfyui_instance_by_id(db: Session, instance_id: int):
    """
    Retrieves a single ComfyUI instance by its ID, eager loading
    its compatible render types.
    """
    return db.query(models.ComfyUIInstance).options(
        joinedload(models.ComfyUIInstance.compatible_render_types)
    ).filter(models.ComfyUIInstance.id == instance_id).first()


def get_one_active_comfyui_instance(db: Session) -> Optional[models.ComfyUIInstance]:
    """
    Retrieves the first active ComfyUI instance found.
    Maintained for compatibility, but get_all_active_comfyui_instances is preferred.
    """
    return db.query(models.ComfyUIInstance).filter(models.ComfyUIInstance.is_active == True).first()


def get_all_active_comfyui_instances(db: Session) -> List[models.ComfyUIInstance]:
    """
    Retrieves all active ComfyUI instances for load balancing.
    Eager loads compatible render types.
    """
    return db.query(models.ComfyUIInstance).options(
        joinedload(models.ComfyUIInstance.compatible_render_types)
    ).filter(models.ComfyUIInstance.is_active == True).all()


def create_comfyui_instance(
    db: Session,
    name: str,
    base_url: str,
    compatible_render_type_ids: List[int]
):
    """
    Creates a new ComfyUI instance and links it to compatible render types.
    """
    exists = db.query(models.ComfyUIInstance).filter(
        (models.ComfyUIInstance.name == name) | (models.ComfyUIInstance.base_url == base_url)
    ).first()
    if exists:
        return None

    compatible_types = []
    if compatible_render_type_ids:
        compatible_types = db.query(models.RenderType).filter(
            models.RenderType.id.in_(compatible_render_type_ids)
        ).all()

    db_instance = models.ComfyUIInstance(
        name=name,
        base_url=base_url,
        compatible_render_types=compatible_types
    )
    db.add(db_instance)
    db.commit()
    db.refresh(db_instance)
    return db_instance


def update_comfyui_instance(
    db: Session,
    instance_id: int,
    name: str,
    base_url: str,
    compatible_render_type_ids: List[int]
):
    """
    Updates an existing ComfyUI instance, including its compatible render types.
    """
    db_instance = get_comfyui_instance_by_id(db, instance_id)
    if not db_instance:
        return None

    db_instance.name = name
    db_instance.base_url = base_url

    compatible_types = []
    if compatible_render_type_ids:
        compatible_types = db.query(models.RenderType).filter(
            models.RenderType.id.in_(compatible_render_type_ids)
        ).all()
    db_instance.compatible_render_types = compatible_types

    db.commit()
    db.refresh(db_instance)
    return db_instance


def toggle_comfyui_instance_active_status(db: Session, instance_id: int) -> Optional[models.ComfyUIInstance]:
    """
    Toggles the is_active status of a specific ComfyUI instance.
    """
    db_instance = get_comfyui_instance_by_id(db, instance_id)
    if not db_instance:
        return None
    
    db_instance.is_active = not db_instance.is_active
    db.commit()
    db.refresh(db_instance)
    return db_instance


def delete_comfyui_instance(db: Session, instance_id: int):
    """
    Deletes a ComfyUI instance from the database by its ID.
    """
    db_instance = db.query(models.ComfyUIInstance).filter(models.ComfyUIInstance.id == instance_id).first()
    if db_instance:
        db.delete(db_instance)
        db.commit()
        return True
    return False


# --- GenerationLog CRUD Operations ---

def create_generation_log(db: Session, log: schemas.GenerationLogCreate) -> models.GenerationLog:
    """
    Creates a new generation log entry in the database.
    """
    db_log = models.GenerationLog(**log.model_dump())
    db.add(db_log)
    db.commit()
    db.refresh(db_log)
    return db_log


def get_generation_logs(db: Session, skip: int = 0, limit: int = 100) -> List[models.GenerationLog]:
    """
    Retrieves a list of generation logs, most recent first.
    """
    return db.query(models.GenerationLog).order_by(
        models.GenerationLog.timestamp.desc()
    ).offset(skip).limit(limit).all()


# --- Statistics Functions ---

def get_total_successful_generations_count(db: Session) -> int:
    """
    Counts the total number of successful generations.
    """
    return db.query(models.GenerationLog).filter(models.GenerationLog.status == 'SUCCESS').count()


def get_prompt_enhancement_count(db: Session) -> int:
    """
    Counts how many times the LLM prompt enhancement was used successfully.
    """
    return db.query(models.GenerationLog).filter(
        models.GenerationLog.status == 'SUCCESS',
        models.GenerationLog.llm_enhanced == True
    ).count()


def get_usage_count_by_render_type(db: Session) -> List[tuple[str, int]]:
    """
    Gets the count of successful generations grouped by render_type_name.
    """
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
    """
    Retrieves all 'style_names' strings from successful generation logs.
    The counting and splitting will be handled in the calling function.
    """
    results = db.query(models.GenerationLog.style_names).filter(
        models.GenerationLog.status == 'SUCCESS',
        models.GenerationLog.style_names.isnot(None),
        models.GenerationLog.style_names != ''
    ).all()
    return [row[0] for row in results]