# app/services/comfyui_client.py
import json
import httpx
import websockets
import uuid
import asyncio
from pathlib import Path
import logging

# NOTE: The direct import of 'settings' and the global client instance
# have been removed. The client will now be instantiated dynamically.
from ..schemas import GenerateImageParams

# Setup logger
logger = logging.getLogger(__name__)

# --- WORKFLOW NODE TITLES ---
# These titles must match the titles set in the ComfyUI workflow's node properties.
POSITIVE_PROMPT_TITLE = "Positive Prompt"
NEGATIVE_PROMPT_TITLE = "Negative Prompt"
LATENT_IMAGE_TITLE = "Latent Image"

# --- ASPECT RATIO PRESETS ---
# A dictionary to map aspect ratio strings to (width, height) tuples.
# Common resolutions for SDXL models.
ASPECT_RATIOS = {
    "1:1": (1024, 1024),
    "16:9": (1344, 768),
    "9:16": (768, 1344),
    "4:3": (1152, 896),
    "3:4": (896, 1152),
    "3:2": (1216, 832),
    "2:3": (832, 1216)
}
DEFAULT_ASPECT_RATIO = (1024, 1024)


# --- CUSTOM EXCEPTIONS ---
class ComfyUIError(Exception):
    """Base exception for ComfyUI client errors."""
    pass

class ComfyUIConnectionError(ComfyUIError):
    """Raised for network-related errors when connecting to ComfyUI."""
    pass

class WorkflowFileNotFoundError(ComfyUIError):
    """Raised when the workflow JSON file cannot be found."""
    pass

class WorkflowFileInvalidError(ComfyUIError):
    """Raised when the workflow JSON file is not valid JSON."""
    pass

class WorkflowExecutionError(ComfyUIError):
    """Raised for errors during the execution of the workflow in ComfyUI."""
    pass


class ComfyUIClient:
    def __init__(self, api_url: str, default_workflow_path: str):
        self.server_address = api_url.replace('http://', '').replace('https://', '')
        self.base_api_url = api_url
        self.default_workflow_path = Path(default_workflow_path)
        self.workflows_dir = self.default_workflow_path.parent
        self.timeout = httpx.Timeout(10.0, connect=5.0)

    def _load_workflow(self, workflow_filename: str | None = None) -> dict:
        if workflow_filename:
            if ".." in workflow_filename or "/" in workflow_filename:
                raise WorkflowFileNotFoundError(f"Invalid characters in workflow filename: {workflow_filename}")
            target_path = self.workflows_dir / workflow_filename
        else:
            target_path = self.default_workflow_path

        logger.info(f"Loading workflow from: {target_path}")
        try:
            with open(target_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError as e:
            raise WorkflowFileNotFoundError(f"Workflow file not found at {target_path}") from e
        except json.JSONDecodeError as e:
            raise WorkflowFileInvalidError(f"Could not decode JSON from {target_path}") from e

    def _find_node_by_title(self, workflow: dict, title: str) -> dict | None:
        for node in workflow.values():
            if isinstance(node, dict) and node.get("_meta", {}).get("title") == title:
                return node
        return None

    def _update_node_text_input(self, node: dict, title: str, text: str):
        if 'text' in node['inputs']:
            node['inputs']['text'] = text
        elif 'Text' in node['inputs']:
            node['inputs']['Text'] = text
        else:
            raise WorkflowExecutionError(
                f"Node with title '{title}' was found, but it has no known text input key."
            )
        logger.debug(f"Updated text in node titled '{title}'")

    async def _queue_prompt(self, workflow: dict, client_id: str) -> dict:
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_api_url}/prompt",
                    json={"prompt": workflow, "client_id": client_id}
                )
                response.raise_for_status()
                return response.json()
        except httpx.RequestError as e:
            raise ComfyUIConnectionError(f"Could not connect to ComfyUI to queue prompt: {e}") from e
        except httpx.HTTPStatusError as e:
            raise ComfyUIConnectionError(f"ComfyUI returned an error when queueing prompt: {e.response.status_code} - {e.response.text}") from e

    async def _get_image_data(self, filename: str, subfolder: str, image_type: str) -> bytes:
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(f"{self.base_api_url}/view", params={'filename': filename, 'subfolder': subfolder, 'type': image_type})
                response.raise_for_status()
                return response.content
        except httpx.RequestError as e:
            raise ComfyUIConnectionError(f"Could not connect to ComfyUI to download image: {e}") from e
        except httpx.HTTPStatusError as e:
            raise ComfyUIConnectionError(f"ComfyUI returned an error when downloading image: {e.response.status_code} - {e.response.text}") from e

    async def _get_history(self, prompt_id: str) -> dict:
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(f"{self.base_api_url}/history/{prompt_id}")
                response.raise_for_status()
                history = response.json()
                return history.get(prompt_id, {})
        except httpx.RequestError as e:
            raise ComfyUIConnectionError(f"Could not connect to ComfyUI to get history: {e}") from e
        except httpx.HTTPStatusError as e:
            raise ComfyUIConnectionError(f"ComfyUI returned an error when getting history: {e.response.status_code} - {e.response.text}") from e

    async def generate_image(
        self,
        args: GenerateImageParams,
        output_dir_path: str,
        output_url_base: str,
        workflow_filename: str | None = None
    ) -> str:
        logger.info(f"Generation request received. Prompt starts with: '{args.prompt[:80]}...'")
        client_id = str(uuid.uuid4())
        workflow = self._load_workflow(workflow_filename)

        # --- Inject Final Parameters into Workflow ---
        # Prompts are assumed to be finalized by the time they reach this client.
        positive_node = self._find_node_by_title(workflow, POSITIVE_PROMPT_TITLE)
        if not positive_node:
            raise WorkflowExecutionError(f"Node with title '{POSITIVE_PROMPT_TITLE}' not found in workflow.")
        self._update_node_text_input(positive_node, POSITIVE_PROMPT_TITLE, args.prompt)

        negative_node = self._find_node_by_title(workflow, NEGATIVE_PROMPT_TITLE)
        if negative_node:
            self._update_node_text_input(negative_node, NEGATIVE_PROMPT_TITLE, args.negative_prompt)

        if args.aspect_ratio:
            latent_node = self._find_node_by_title(workflow, LATENT_IMAGE_TITLE)
            if latent_node:
                width, height = ASPECT_RATIOS.get(args.aspect_ratio, DEFAULT_ASPECT_RATIO)
                latent_node['inputs']['width'] = width
                latent_node['inputs']['height'] = height
                logger.info(f"Set aspect ratio to {args.aspect_ratio} ({width}x{height})")
            else:
                logger.warning(f"Aspect ratio '{args.aspect_ratio}' provided, but node '{LATENT_IMAGE_TITLE}' not found.")

        logger.info("Queueing prompt on ComfyUI server...")
        queue_response = await self._queue_prompt(workflow, client_id)
        prompt_id = queue_response.get('prompt_id')
        if not prompt_id:
            raise WorkflowExecutionError(f"ComfyUI API did not return a prompt_id. Response: {queue_response}")
        logger.info(f"Prompt queued with ID: {prompt_id}")

        ws_url = f"ws://{self.server_address}/ws?clientId={client_id}"
        logger.info(f"Connecting to WebSocket: {ws_url}")
        try:
            async with asyncio.timeout(300):
                async with websockets.connect(ws_url) as websocket:
                    while True:
                        message_data = await websocket.recv()
                        message = json.loads(message_data)
                        if message['type'] == 'executing' and message['data']['node'] is None and message['data']['prompt_id'] == prompt_id:
                            logger.info(f"Execution finished for prompt_id: {prompt_id}")
                            break
        except TimeoutError as e:
            raise WorkflowExecutionError(f"Image generation timed out for prompt_id: {prompt_id}") from e
        except (websockets.exceptions.WebSocketException, ConnectionRefusedError) as e:
            raise ComfyUIConnectionError(f"Could not connect to ComfyUI WebSocket: {e}") from e

        history = await self._get_history(prompt_id)
        outputs = history.get('outputs', {})
        images_output = []
        for node_output in outputs.values():
            if 'images' in node_output:
                images_output.extend(node_output['images'])
        
        if not images_output:
            logger.error(f"No images found in history output for prompt_id: {prompt_id}. Full history: {history}")
            raise WorkflowExecutionError(f"No images found in the output for prompt_id: {prompt_id}")

        # Get the first image from the list
        image_info = images_output[0]
        filename = image_info.get('filename')
        subfolder = image_info.get('subfolder', '')
        image_type = image_info.get('type', 'output')
        
        if not filename:
            raise WorkflowExecutionError(f"History output for prompt_id {prompt_id} is missing a filename.")
        
        logger.info(f"Downloading generated image: {filename} (type: {image_type}, subfolder: '{subfolder}')")
        image_data = await self._get_image_data(filename, subfolder, image_type)

        try:
            # Ensure the final filename doesn't contain subdirectories
            safe_filename = Path(filename).name
            output_path = Path(output_dir_path) / safe_filename
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, 'wb') as f:
                f.write(image_data)
            logger.info(f"Image saved to: {output_path}")
        except OSError as e:
            raise ComfyUIError(f"Failed to save image to disk: {e}") from e

        final_url = f"{output_url_base.rstrip('/')}/{safe_filename}"
        logger.info(f"Returning public URL: {final_url}")
        return final_url

# NOTE: Global comfyui_client instance has been removed.