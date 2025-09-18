# app/config.py
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field

class Settings(BaseSettings):
    """
    Loads and validates application settings from environment variables.
    """
    # --- Database Configuration ---
    # This is the only setting remaining, typically provided by the execution
    # environment (like Docker Compose) rather than a .env file.
    database_url: str = Field(
        default='sqlite:///./data/mcp_genimage.db',
        alias='DATABASE_URL'
    )

    # --- ComfyUI Client Configuration ---
    comfyui_generation_timeout: int = Field(
        default=900,  # Default to 15 minutes
        alias='COMFYUI_GENERATION_TIMEOUT',
        description="Timeout in seconds for waiting for an image generation to complete."
    )

    model_config = SettingsConfigDict(
        # No longer loading from .env file
        extra='ignore'
    )

settings = Settings()