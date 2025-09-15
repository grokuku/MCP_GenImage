#### Fichier : app/config.py
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

    model_config = SettingsConfigDict(
        # No longer loading from .env file
        extra='ignore'
    )

settings = Settings()