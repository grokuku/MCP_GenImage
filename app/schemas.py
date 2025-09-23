# app/schemas.py
from pydantic import BaseModel, Field
from typing import Any, List, Optional, TypeVar, Generic, Union, Literal
from datetime import datetime

# --- JSON-RPC Generic Models ---

JsonRpcId = Union[str, int, None]
T = TypeVar('T')

class JsonRpcError(BaseModel):
    code: int
    message: str
    data: Optional[Any] = None

class JsonRpcRequest(BaseModel):
    jsonrpc: str = "2.0"
    method: str
    params: Optional[Any] = None
    id: JsonRpcId = None

class JsonRpcResponse(BaseModel, Generic[T]):
    jsonrpc: str = "2.0"
    result: Optional[T] = None
    error: Optional[JsonRpcError] = None
    id: JsonRpcId

# --- MCP Tool-Specific Parameter Schemas ---

class GenerateImageParams(BaseModel):
    """Defines the parameters for the 'generate_image' tool."""
    prompt: str
    negative_prompt: Optional[str] = ""
    style_names: Optional[List[str]] = Field(default_factory=list)
    aspect_ratio: Optional[str] = None
    render_type: Optional[str] = None
    seed: Optional[int] = None
    enhance_prompt: Optional[bool] = True

class UpscaleImageParams(BaseModel):
    """Defines the parameters for the 'upscale_image' tool."""
    input_image_url: str
    prompt: Optional[str] = None
    render_type: Optional[str] = None
    denoise: Optional[float] = Field(None, ge=0.0, le=1.0)
    seed: Optional[int] = None

class ToolCallParams(BaseModel):
    """
    Generic wrapper for any tool call. The arguments are a dict
    and will be validated against the specific tool's schema in the endpoint.
    """
    name: str
    arguments: dict


# --- Base Schemas for Tool Definitions ---

GENERATE_IMAGE_TOOL_SCHEMA = {
    "name": "generate_image",
    "title": "Generate Image from Text",
    "description": "Generates a new image based on a textual description (prompt).",
    "inputSchema": {
        "type": "object",
        "properties": {
            "prompt": {
                "type": "string",
                "description": "A detailed description of the image to generate."
            },
            "negative_prompt": {
                "type": "string",
                "description": "Optional. A description of elements to avoid in the image."
            },
            "style_names": {
                "type": "array",
                "description": "Optional. A list of style names to apply.",
                "items": { "type": "string" }
            },
            "aspect_ratio": {
                "type": "string",
                "description": "Optional. The desired aspect ratio of the final image.",
                "enum": ["1:1", "16:9", "9:16", "4:3", "3:4"]
            },
            "render_type": {
                "type": "string",
                "description": "Optional. The specific rendering workflow to use."
            },
            "seed": {
                "type": "integer",
                "description": "Optional. A specific seed for reproducing an image."
            },
            "enhance_prompt": {
                "type": "boolean",
                "description": "Optional. If true, an LLM will enhance the prompt. Defaults to true.",
                "default": True
            }
        },
        "required": ["prompt"]
    }
}

UPSCALE_IMAGE_TOOL_SCHEMA = {
    "name": "upscale_image",
    "title": "Upscale an Image",
    "description": "Increases the resolution and enhances the detail of an existing image.",
    "inputSchema": {
        "type": "object",
        "properties": {
            "input_image_url": {
                "type": "string",
                "description": "The URL of the source image to upscale."
            },
            "prompt": {
                "type": "string",
                "description": "Optional. A textual description to guide the upscaling process."
            },
            "render_type": {
                "type": "string",
                "description": "Optional. The specific upscaling workflow to use."
            },
            # --- START CORRECTION ---
            "upscale_type": {
                "type": "string",
                "title": "Upscale Type",
                "description": "The specific upscaling model or method to use."
            },
            # --- END CORRECTION ---
            "denoise": {
                "type": "number",
                "description": "Optional. Denoising factor (0.0 to 1.0). Higher values allow for more creative changes."
            },
            "seed": {
                "type": "integer",
                "description": "Optional. A specific seed for reproducing the upscale."
            }
        },
        "required": ["input_image_url"]
    }
}


# --- Database ORM Schemas ---

class RenderTypeBase(BaseModel):
    name: str
    workflow_filename: str
    prompt_examples: Optional[str] = None
    is_visible: bool = True
    generation_mode: Literal["image_generation", "upscale"] = "image_generation"

class RenderTypeCreate(RenderTypeBase):
    pass

class RenderType(RenderTypeBase):
    id: int
    is_default_for_generation: bool
    is_default_for_upscale: bool

    class Config:
        from_attributes = True

# --- Style Schemas ---
class StyleBase(BaseModel):
    name: str
    category: str
    prompt_template: str
    negative_prompt_template: str

class StyleCreate(StyleBase):
    compatible_render_type_ids: List[int] = []
    default_render_type_id: Optional[int] = None

class Style(StyleBase):
    id: int
    is_active: bool
    is_default: bool
    default_render_type_id: Optional[int] = None
    default_render_type: Optional[RenderType] = None
    compatible_render_types: List[RenderType] = []

    class Config:
        from_attributes = True

# --- ComfyUI Schemas ---
class ComfyUIInstanceBase(BaseModel):
    name: str
    base_url: str

class ComfyUIInstanceCreate(ComfyUIInstanceBase):
    compatible_render_type_ids: List[int] = []

class ComfyUIInstance(ComfyUIInstanceBase):
    id: int
    is_active: bool
    compatible_render_types: List[RenderType] = []

    class Config:
        from_attributes = True

# --- GenerationLog Schemas ---
class GenerationLogBase(BaseModel):
    positive_prompt: str
    negative_prompt: str
    render_type_name: Optional[str] = None
    style_names: Optional[str] = None
    aspect_ratio: Optional[str] = None
    seed: Optional[int] = None
    llm_enhanced: bool = False
    status: str
    image_filename: Optional[str] = None
    duration_ms: Optional[int] = None
    error_message: Optional[str] = None
    comfyui_instance_id: Optional[int] = None

class GenerationLogCreate(GenerationLogBase):
    pass

class GenerationLog(GenerationLogBase):
    id: int
    timestamp: datetime

    class Config:
        from_attributes = True