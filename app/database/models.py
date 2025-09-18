# This file will contain our SQLAlchemy models.
# We will add models for Styles, Workflows, Statistics, etc., in future steps.

from sqlalchemy import Boolean, Column, Integer, String, DateTime, ForeignKey, Table
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from .session import Base


# Association table for the many-to-many relationship between Style and RenderType
style_render_type_association = Table(
    "style_render_type_association",
    Base.metadata,
    Column("style_id", Integer, ForeignKey("styles.id"), primary_key=True),
    Column("render_type_id", Integer, ForeignKey("render_types.id"), primary_key=True),
)

# Association table for the many-to-many relationship between ComfyUIInstance and RenderType
comfyui_render_type_association = Table(
    "comfyui_render_type_association",
    Base.metadata,
    Column("comfyui_instance_id", Integer, ForeignKey("comfyui_instances.id"), primary_key=True),
    Column("render_type_id", Integer, ForeignKey("render_types.id"), primary_key=True),
)


class RenderType(Base):
    """
    Represents a render type that maps a user-friendly name to a
    specific ComfyUI workflow JSON file.
    """
    __tablename__ = "render_types"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True, nullable=False)
    workflow_filename = Column(String, nullable=False)
    prompt_examples = Column(String, nullable=True) # New field
    is_default = Column(Boolean, default=False, nullable=False)

    # Back-populates the many-to-many relationship from Style
    compatible_styles = relationship(
        "Style",
        secondary=style_render_type_association,
        back_populates="compatible_render_types"
    )

    # Back-populates the one-to-many relationship for recommended render type
    styles_recommending_this = relationship(
        "Style",
        back_populates="recommended_render_type"
    )

    # Back-populates the many-to-many relationship from ComfyUIInstance
    compatible_comfyui_instances = relationship(
        "ComfyUIInstance",
        secondary=comfyui_render_type_association,
        back_populates="compatible_render_types"
    )

    def __repr__(self):
        return f"<RenderType(id={self.id}, name='{self.name}', workflow='{self.workflow_filename}')>"


class Style(Base):
    """
    Represents a style that can be applied to a prompt.
    A style consists of a name, a category, and templates for both the
    positive and negative prompts that get merged with the user's prompts.
    It is also linked to compatible and recommended render types.
    """
    __tablename__ = "styles"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True, nullable=False)
    category = Column(String, index=True, nullable=False)
    prompt_template = Column(String, nullable=False)
    negative_prompt_template = Column(String, nullable=False, server_default='', default='')
    is_active = Column(Boolean, default=True, nullable=False)
    is_default = Column(Boolean, default=False, nullable=False)

    # Foreign key for the recommended render type (one-to-many)
    recommended_render_type_id = Column(Integer, ForeignKey("render_types.id"), nullable=True)

    # Relationship for the recommended render type
    recommended_render_type = relationship(
        "RenderType",
        back_populates="styles_recommending_this"
    )

    # Relationship for compatible render types (many-to-many)
    compatible_render_types = relationship(
        "RenderType",
        secondary=style_render_type_association,
        back_populates="compatible_styles"
    )

    def __repr__(self):
        return f"<Style(id={self.id}, name='{self.name}', category='{self.category}')>"


class Setting(Base):
    """
    Represents a generic key-value store for application settings
    that can be configured via the web UI.
    """
    __tablename__ = "settings"

    key = Column(String, primary_key=True, index=True)
    value = Column(String, nullable=False, default='')

    def __repr__(self):
        return f"<Setting(key='{self.key}', value='{self.value}')>"


class ComfyUIInstance(Base):
    """
    Represents a configured ComfyUI server instance.
    """
    __tablename__ = "comfyui_instances"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False)
    base_url = Column(String, unique=True, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)

    generation_logs = relationship("GenerationLog", back_populates="comfyui_instance")

    # Relationship for compatible render types (many-to-many)
    compatible_render_types = relationship(
        "RenderType",
        secondary=comfyui_render_type_association,
        back_populates="compatible_comfyui_instances"
    )

    def __repr__(self):
        return f"<ComfyUIInstance(id={self.id}, name='{self.name}', url='{self.base_url}', active={self.is_active})>"


class GenerationLog(Base):
    """
    Stores the history of each image generation request.
    """
    __tablename__ = "generation_logs"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
    
    # Generation Parameters
    positive_prompt = Column(String, nullable=False)
    negative_prompt = Column(String, nullable=False)
    render_type_name = Column(String, nullable=True)
    style_names = Column(String, nullable=True)
    aspect_ratio = Column(String, nullable=True)
    seed = Column(String, nullable=True)
    llm_enhanced = Column(Boolean, default=False, nullable=False)
    
    # Generation Outcome
    image_filename = Column(String, nullable=True)
    duration_ms = Column(Integer, nullable=True)
    status = Column(String, index=True, nullable=False)  # e.g., 'SUCCESS', 'FAILED'
    error_message = Column(String, nullable=True)

    # Foreign Key
    comfyui_instance_id = Column(Integer, ForeignKey("comfyui_instances.id"), nullable=True)
    comfyui_instance = relationship("ComfyUIInstance", back_populates="generation_logs")

    def __repr__(self):
        return f"<GenerationLog(id={self.id}, status='{self.status}', timestamp='{self.timestamp}')>"