#### Fichier : app/schemas.py
from pydantic import BaseModel, Field, field_validator
from typing import Any, List, Optional, TypeVar, Generic, Union
from datetime import datetime

# --- JSON-RPC Generic Models ---

# The request/response ID can be a string, integer, or null.
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

    @field_validator('jsonrpc')
    @classmethod
    def must_be_2_0(cls, v: str) -> str:
        if v != '2.0':
            raise ValueError('jsonrpc version must be "2.0"')
        return v

class JsonRpcResponse(BaseModel, Generic[T]):
    jsonrpc: str = "2.0"
    result: Optional[T] = None
    error: Optional[JsonRpcError] = None
    id: JsonRpcId

# --- MCP Tool-Specific Models ---

class GenerateImageParams(BaseModel):
    """
    Defines the parameters for the 'generate_image' tool call, aligned with
    the logic we have defined.
    """
    prompt: str
    negative_prompt: str = ""
    style_names: List[str] = Field(default_factory=list, examples=[["Cinematic", "Photorealistic"]])
    aspect_ratio: Optional[str] = Field(None, examples=["16:9", "1:1"])
    render_type: Optional[str] = Field(None, examples=["SDXL_TURBO", "UPSCALE_4X"])
    enhance_prompt: bool = True

# Note: This is a generic wrapper for any tool. We will use GenerateImageParams
# as the specific model for our 'generate_image' method.
class ToolCallParams(BaseModel):
    name: str
    arguments: GenerateImageParams

# --- Tool Definition (as a dictionary for simplicity) ---

GENERATE_IMAGE_TOOL_DEF = {
    "name": "generate_image",
    "title": "Generate Image from Text",
    "description": "Generates an image based on a textual description (prompt). Can be used to create illustrations, photos, or artistic representations.",
    "inputSchema": {
        "type": "object",
        "properties": {
            "prompt": {
                "type": "string",
                "description": "A detailed description of the image to be generated. Be as specific as possible about the subject, style, colors, and composition."
            },
            "negative_prompt": {
                "type": "string",
                "description": "Optional. A description of elements to avoid in the image (e.g., 'ugly, deformed, extra fingers')."
            },
            "style_names": {
                "type": "array",
                "description": "Optional. A list of style names to apply to the prompt (e.g., ['Cinematic', 'Photorealistic']). Styles are configured in the web UI.",
                "items": {
                    "type": "string"
                }
            },
            "aspect_ratio": {
                "type": "string",
                "description": "Optional. The desired aspect ratio of the final image. Defaults to '1:1' (square).",
                "enum": ["1:1", "16:9", "9:16", "4:3", "3:4"]
            },
            "render_type": {
                "type": "string",
                "description": "Optional. The specific rendering workflow to use (e.g., for upscaling, video, or a specific model). Overrides the default workflow."
            },
            "enhance_prompt": {
                "type": "boolean",
                "description": "Optional. If true, an LLM will be used to enhance and refine the final prompts before generation. Defaults to true.",
                "default": True
            }
        },
        "required": ["prompt"]
    }
}

# --- Database ORM Models ---

class GenerationLogBase(BaseModel):
    positive_prompt: str
    negative_prompt: str
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