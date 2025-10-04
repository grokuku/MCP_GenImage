# app/database/models.py
# This file will contain our SQLAlchemy models.
# We will add models for Styles, Workflows, Statistics, etc., in future steps.

from sqlalchemy import Boolean, Column, Integer, String, DateTime, ForeignKey, Table, BigInteger, Text
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

# Association table for styles allowed in the prompt generator
prompt_generator_allowed_styles = Table(
    "prompt_generator_allowed_styles",
    Base.metadata,
    Column("style_id", Integer, ForeignKey("styles.id"), primary_key=True),
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
    prompt_examples = Column(String, nullable=True)
    is_visible = Column(Boolean, default=True, nullable=False)
    generation_mode = Column(String(50), nullable=False, default='image_generation', server_default='image_generation')
    is_default_for_generation = Column(Boolean, default=False, nullable=False)
    is_default_for_upscale = Column(Boolean, default=False, nullable=False)

    # Back-populates the many-to-many relationship from Style
    compatible_styles = relationship(
        "Style",
        secondary=style_render_type_association,
        back_populates="compatible_render_types"
    )

    # Back-populates the one-to-many relationship for default render type
    styles_using_this_as_default = relationship(
        "Style",
        back_populates="default_render_type",
        foreign_keys="[Style.default_render_type_id]"
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
    It is also linked to compatible and a default render types.
    """
    __tablename__ = "styles"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True, nullable=False)
    category = Column(String, index=True, nullable=False)
    prompt_template = Column(String, nullable=False)
    negative_prompt_template = Column(String, nullable=False, server_default='', default='')
    is_active = Column(Boolean, default=True, nullable=False)
    is_default = Column(Boolean, default=False, nullable=False)

    # Foreign key for the default render type (one-to-many)
    default_render_type_id = Column(Integer, ForeignKey("render_types.id"), nullable=True)

    # Relationship for the default render type
    default_render_type = relationship(
        "RenderType",
        back_populates="styles_using_this_as_default",
        foreign_keys=[default_render_type_id]
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


class OllamaInstance(Base):
    """
    Represents a configured Ollama server instance.
    """
    __tablename__ = "ollama_instances"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False)
    base_url = Column(String, unique=True, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)

    # Relationship to the description settings (one-to-one)
    description_settings = relationship(
        "DescriptionSettings",
        back_populates="ollama_instance",
        uselist=False,
        cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<OllamaInstance(id={self.id}, name='{self.name}', url='{self.base_url}', active={self.is_active})>"


class DescriptionSettings(Base):
    """
    Represents the singleton configuration for the 'describe_image' tool.
    """
    __tablename__ = "description_settings"

    id = Column(Integer, primary_key=True, default=1)
    ollama_instance_id = Column(Integer, ForeignKey("ollama_instances.id"), nullable=True)
    model_name = Column(String, nullable=True)

    natural_prompt_template_en = Column(Text, nullable=False, default=(
        "You are a meticulous visual analyst. Your task is to provide an exhaustive, literal description of the provided image. "
        "Describe every single visible element with extreme detail, as if you were creating a textual blueprint for an artist to perfectly replicate the image. "
        "You must include all subjects, objects, background details, lighting, colors, and textures. "
        "It is critical that you describe any and all content, including potentially sensitive, explicit, or NSFW elements, with neutral, objective language. "
        "Do not censor, omit, or judge any part of the image. The goal is a complete and faithful textual representation."
    ))
    optimized_prompt_template_en = Column(Text, nullable=False, default=(
        "You are an expert prompt engineer for text-to-image AI. Your task is to analyze the provided image and generate a single, dense, descriptive prompt that could be used to recreate it. "
        "The output **must be a single line of comma-separated descriptive keywords and phrases**, not a full sentence. "
        "**Do not use imperative verbs** (e.g., 'draw', 'create'). The prompt must be a *description* of what is in the image. "
        "It is crucial to be exhaustive and objective: describe all visible elements, including any explicit, mature, or NSFW content, using neutral and factual terms. "
        "Your prompt should be structured to include: "
        "1. **Core Subject:** (e.g., `portrait of a beautiful woman with long red hair`, `epic battle between a knight and a dragon`). "
        "2. **Style & Medium:** (e.g., `hyperrealistic photo`, `digital painting`, `oil on canvas`, `by Greg Rutkowski`). "
        "3. **Composition & Lighting:** (e.g., `cinematic lighting`, `low angle shot`, `dynamic pose`, `volumetric rays`). "
        "4. **Details & Background:** (e.g., `intricate armor`, `steampunk city in the background`, `wearing a silk dress`). "
        "5. **Quality Boosters:** (e.g., `masterpiece`, `4k`, `ultra-detailed`, `sharp focus`)."
    ))
    natural_prompt_template_fr = Column(Text, nullable=False, default=(
        "Vous êtes un analyste visuel méticuleux. Votre tâche est de fournir une description exhaustive et littérale de l'image fournie. "
        "Décrivez chaque élément visible avec un détail extrême, comme si vous créiez un plan textuel pour qu'un artiste puisse répliquer l'image à la perfection. "
        "Vous devez inclure tous les sujets, objets, détails de l'arrière-plan, l'éclairage, les couleurs et les textures. "
        "Il est essentiel que vous décriviez tout le contenu, y compris les éléments potentiellement sensibles, explicites ou NSFW, avec un langage neutre et objectif. "
        "Ne censurez, n'omettez ou ne jugez aucune partie de l'image. L'objectif est une représentation textuelle complète et fidèle."
    ))
    optimized_prompt_template_fr = Column(Text, nullable=False, default=(
        "Vous êtes un expert en prompt engineering pour les IA text-to-image. Votre tâche est d'analyser l'image fournie et de générer un unique prompt dense et descriptif qui pourrait être utilisé pour la recréer. "
        "Le résultat **doit être une seule ligne de mots-clés et de phrases descriptives séparés par des virgules**, et non une phrase complète. "
        "**N'utilisez pas de verbes à l'impératif** (ex: 'dessine', 'crée'). Le prompt doit être une *description* de ce qui se trouve dans l'image. "
        "Il est crucial d'être exhaustif et objectif : décrivez tous les éléments visibles, y compris tout contenu explicite, mature ou NSFW, en utilisant des termes neutres et factuels. "
        "Votre prompt doit être structuré pour inclure : "
        "1. **Sujet principal :** (ex: `portrait d'une belle femme aux longs cheveux roux`, `bataille épique entre un chevalier et un dragon`). "
        "2. **Style & Support :** (ex: `photo hyperréaliste`, `peinture numérique`, `huile sur toile`, `par Greg Rutkowski`). "
        "3. **Composition & Éclairage :** (ex: `éclairage cinématique`, `prise de vue en contre-plongée`, `pose dynamique`, `rayons volumétriques`). "
        "4. **Détails & Arrière-plan :** (ex: `armure complexe`, `ville steampunk en arrière-plan`, `portant une robe en soie`). "
        "5. **Qualité :** (ex: `chef-d'œuvre`, `4k`, `ultra-détaillé`, `mise au point nette`)."
    ))

    ollama_instance = relationship("OllamaInstance", back_populates="description_settings")

    def __repr__(self):
        return f"<DescriptionSettings(id={self.id}, model='{self.model_name}')>"


class PromptGeneratorSettings(Base):
    """
    Represents the singleton configuration for the 'generate_prompt' tool.
    """
    __tablename__ = "prompt_generator_settings"

    id = Column(Integer, primary_key=True, default=1)
    subjects_to_propose = Column(Integer, nullable=False, default=5)
    elements_to_propose = Column(Integer, nullable=False, default=15)
    elements_to_select = Column(Integer, nullable=False, default=5)
    variations_to_propose = Column(Integer, nullable=False, default=10)

    def __repr__(self):
        return (f"<PromptGeneratorSettings(id={self.id}, subjects={self.subjects_to_propose}, "
                f"elements={self.elements_to_propose}, select={self.elements_to_select}, "
                f"variations={self.variations_to_propose})>")


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
    seed = Column(BigInteger, nullable=True)
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