#### Fichier : app/main.py
# app/main.py
from pathlib import Path
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from .api import mcp_routes
from .web import web_routes

# Define the project root directory. Path(__file__) is /app/main.py, so .parent is /app.
# This ensures all paths are constructed reliably.
PROJECT_ROOT = Path(__file__).parent

# NOTE: We have removed `Base.metadata.create_all(bind=engine)`.
# Database schema migrations must be handled exclusively by Alembic
# to ensure consistency and prevent conflicts.
# Run `docker compose run --rm mcp_genimage alembic upgrade head` to apply migrations.

app = FastAPI(
    title="MCP GenImage Tool Server",
    description="A server implementing the Model Context Protocol for image generation via ComfyUI, with a web interface for management.",
    version="2.0.0-alpha"
)

# --- Mount Routers ---
# The MCP JSON-RPC endpoint
app.include_router(mcp_routes.router)
# The web interface endpoints
app.include_router(web_routes.router)

# --- Mount Static Directories ---
# Serves the generated images from the '/app/outputs' directory
app.mount("/outputs", StaticFiles(directory="/app/outputs"), name="outputs")
# Serves static assets for the web interface (CSS, JS) from a reliable absolute path
app.mount(
    "/static",
    StaticFiles(directory=PROJECT_ROOT / "web" / "static"),
    name="static"
)