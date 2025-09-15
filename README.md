#### Fichier : README.md
    # MCP_GenImage Server

    ## Overview

    MCP_GenImage is a comprehensive, Dockerized hub for image generation. It acts as a sophisticated bridge between an MCP client (like an LLM agent) and a ComfyUI backend, while also providing a full-featured web interface for configuration and testing.

    The server exposes a standard Model Context Protocol (MCP) endpoint for programmatic access, and a user-friendly web UI to manage styles, render workflows, and service configurations.

    ## Features

    *   **Web Interface:** A complete UI to manage all aspects of the service:
        *   **Test Generation:** An interactive page to test the entire image generation pipeline.
        *   **Style Management:** Create and manage prompt fragments (styles) that can be easily applied to generations.
        *   **Render Type Management:** Map user-friendly names (e.g., `SDXL_TURBO`) to specific ComfyUI workflow files.
        *   **Dynamic Service Configuration:** Configure connections to ComfyUI and Ollama servers directly from the UI without restarting the service.
    *   **Intelligent Prompt Processing:**
        *   Applies multiple predefined styles to prompts.
        *   Optionally enhances prompts using an LLM (via Ollama) for more creative and detailed results.
    *   **MCP Compliant:** Implements `tools/list` and `tools/call` for seamless integration with MCP-based systems.
    *   **Asynchronous & Robust:** Uses asynchronous communication with ComfyUI and is designed to run without a configured Ollama instance.
    *   **Self-Contained Image Serving:** Serves generated images from its own endpoint, removing the need to expose the ComfyUI server directly to clients.

    ## Prerequisites

    1.  **Docker and Docker Compose:** The application is designed to run as a containerized service.
    2.  **A Running ComfyUI Instance:** The server needs at least one running ComfyUI instance accessible on the network.

    ### ComfyUI Workflow Contract

    For the service to correctly inject parameters, your ComfyUI workflow JSON files **must** contain nodes that have the following exact `title` properties in the workflow graph:

    *   `Positive Prompt`: This node (typically a `CLIPTextEncode`) will receive the main prompt.
    *   `Negative Prompt`: This node (typically a `CLIPTextEncode`) will receive the negative prompt.
    *   `Latent Image`: This node (typically an `EmptyLatentImage`) will have its dimensions adjusted based on the requested aspect ratio.

    The service identifies these specific nodes by their titles to inject the data. If these titles are not found, the generation will fail.

    ## Installation and Usage

    1.  **Clone the repository.**

    2.  **Create your environment file:** Copy `.env.example` to a new file named `.env` and fill in the required `OUTPUT_URL_BASE`. This is the public-facing URL where your `outputs` directory will be accessible.

    3.  **Place your workflow(s):** Add your ComfyUI workflow file(s) inside the `workflows/` directory.

    4.  **Build and run the server:**
        ```bash
        docker compose up --build -d
        ```

    5.  **Apply Database Migrations:** The first time you run the server, and after any update that modifies the database structure, you must run the migrations.
        ```bash
        docker compose run --rm mcp_genimage alembic upgrade head
        ```

    6.  **Configure Services:** Open your browser to `http://localhost:8001` (or the port you configured).
        *   Navigate to **ComfyUI Settings** and add at least one ComfyUI server instance.
        *   (Optional) Navigate to **Ollama Settings** to configure your Ollama server for prompt enhancement.

    The application is now ready to use via the web interface or the API.

    ## Project Structure

    ```
        📁 MCP_GenImage/
      ├─ 📄 .env.example
      ├─ 📄 Dockerfile
      ├─ 📄 README.md
      ├─ 📄 alembic.ini
      ├─ 📄 docker-compose.yml
      ├─ 📄 features.md
      ├─ 📄 project_context.md
      ├─ 📄 requirements.txt
      ├─ 📄 usage.md
      │
      ├─ 📁 alembic/
      ├─ 📁 app/
      │  ├─ 📄 main.py
      │  ├─ 📁 api/
      │  ├─ 📁 database/
      │  ├─ 📁 services/
      │  └─ 📁 web/
      │     ├─ 📁 static/
      │     └─ 📁 templates/
      ├─ 📁 data/
      ├─ 📁 outputs/
      └─ 📁 workflows/
    ```