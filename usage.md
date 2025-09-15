#### Fichier : usage.md
# MCP_GenImage Tool Server

## 1. Overview

MCP_GenImage is a Dockerized tool server that conforms to the Model Context Protocol (MCP). It acts as a bridge between an MCP-compliant client (like GroBot) and a ComfyUI server, providing a standardized `tools/call` interface for generating images.

The server abstracts the complexity of interacting with ComfyUI's API, allowing an LLM agent to request an image with a simple set of parameters.

---

## 2. Prerequisites

### ComfyUI Server
A running ComfyUI instance is required. The MCP_GenImage service must be able to reach its API. This is configured via the web interface.

### ComfyUI Workflow Configuration (Crucial)
The service injects parameters into a predefined ComfyUI workflow template. For this to work, specific nodes in your workflow **must** be titled correctly.

In the ComfyUI interface, right-click on a node and select "Properties" to set its title. The following titles are required:

*   **`Positive Prompt`**: This title must be assigned to the node that takes the main positive prompt as input. This is typically a `CLIPTextEncode` node or a primitive Text Box node connected to it. **This node is mandatory.**
*   **`Negative Prompt`**: This title should be assigned to the node that takes the negative prompt.
*   **`Latent Image`**: This title should be assigned to the `EmptyLatentImage` node to control the output dimensions.

---

## 3. Configuration

The service is configured primarily via its web interface at `http://localhost:8001` (or your configured port). Initial startup configuration is managed via an `.env` file.

*   `OUTPUT_URL_BASE`: **(Required)** The public-facing base URL that will be used to construct the final link to the generated image. Example: `http://192.168.1.50:8001/outputs`
*   `COMFYUI_API_URL`: (Optional) Can be used to pre-populate a ComfyUI instance on first startup, but management via the UI is recommended.
*   `OLLAMA_API_URL`: (Optional) Can be used to pre-populate the Ollama settings, but management via the UI is recommended.

---

## 4. Running the Service

Use Docker Compose to build and run the service in detached mode:

```bash
docker compose up --build -d
```

Remember to run database migrations: `docker compose run --rm mcp_genimage alembic upgrade head`

---

## 5. MCP API Endpoint

The server exposes a single endpoint for all MCP communication.

*   **Endpoint**: `POST /mcp`
*   **Protocol**: JSON-RPC 2.0

### Method: `tools/list`

Discovers the available tools.

**Request:**
```json
{
    "jsonrpc": "2.0",
    "method": "tools/list",
    "id": "1"
}
```

**Successful Response:**
```json
{
    "jsonrpc": "2.0",
    "result": {
        "tools": [
            {
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
                            "items": { "type": "string" }
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
                            "default": true
                        }
                    },
                    "required": ["prompt"]
                }
            }
        ]
    },
    "id": "1"
}
```

### Method: `tools/call`

Executes the `generate_image` tool.

**Request Example:**
```json
{
    "jsonrpc": "2.0",
    "method": "tools/call",
    "params": {
        "name": "generate_image",
        "arguments": {
            "prompt": "A majestic dragon flying over a medieval castle",
            "negative_prompt": "modern buildings, cars, blurry",
            "style_names": ["Fantasy Art", "Cinematic"],
            "aspect_ratio": "16:9",
            "render_type": "SDXL_High_Quality",
            "enhance_prompt": true
        }
    },
    "id": "req-123"
}
```

**Successful Response:**
```json
{
    "jsonrpc": "2.0",
    "result": {
        "content": {
            "type": "image",
            "source": "http://192.168.1.50:8001/outputs/ComfyUI_00025_.png"
        }
    },
    "id": "req-123"
}
```

**Error Response (Example):**
If no active ComfyUI server is configured.
```json
{
    "jsonrpc": "2.0",
    "error": {
        "code": -32001,
        "message": "No active ComfyUI server is configured."
    },
    "id": "req-124"
}
```