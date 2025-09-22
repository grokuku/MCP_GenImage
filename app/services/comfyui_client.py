# app/services/comfyui_client.py
import json
import httpx
import websockets
import uuid
import asyncio
from pathlib import Path
import logging
from urllib.parse import urlparse
import aiohttp

from ..schemas import GenerateImageParams

# Setup logger
logger = logging.getLogger(__name__)

# --- CONSTANTS FOR RETRY MECHANISM ---
HISTORY_MAX_RETRIES = 10
HISTORY_RETRY_DELAY = 0.5  # seconds


# --- CUSTOM EXCEPTIONS ---
class ComfyUIError(Exception):
    """Base exception for ComfyUI client errors."""
    pass

class ComfyUIConnectionError(ComfyUIError):
    """Raised for network-related errors when connecting to ComfyUI."""
    pass

class WorkflowFileInvalidError(ComfyUIError):
    """Raised when the workflow JSON file is not valid JSON."""
    pass

class WorkflowExecutionError(ComfyUIError):
    """Raised for errors during the execution of the workflow in ComfyUI."""
    pass


class ComfyUIClient:
    def __init__(self, api_url: str, generation_timeout: int):
        self.server_address = api_url.replace('http://', '').replace('https://', '')
        self.base_api_url = api_url
        self.http_timeout = httpx.Timeout(10.0, connect=5.0)
        self.generation_timeout = generation_timeout

    async def _queue_prompt(self, workflow: dict, client_id: str) -> dict:
        try:
            payload = json.dumps({"prompt": workflow, "client_id": client_id}).encode('utf-8')
            async with httpx.AsyncClient(timeout=self.http_timeout) as client:
                response = await client.post(
                    f"{self.base_api_url}/prompt",
                    content=payload,
                    headers={'Content-Type': 'application/json'}
                )
                response.raise_for_status()
                return response.json()
        except httpx.RequestError as e:
            raise ComfyUIConnectionError(f"Could not connect to ComfyUI to queue prompt: {e}") from e
        except httpx.HTTPStatusError as e:
            raise ComfyUIConnectionError(f"ComfyUI returned an error when queueing prompt: {e.response.status_code} - {e.response.text}") from e

    async def _get_image_data(self, filename: str, subfolder: str, image_type: str) -> bytes:
        try:
            async with httpx.AsyncClient(timeout=self.http_timeout) as client:
                response = await client.get(f"{self.base_api_url}/view", params={'filename': filename, 'subfolder': subfolder, 'type': image_type})
                response.raise_for_status()
                return response.content
        except httpx.RequestError as e:
            raise ComfyUIConnectionError(f"Could not connect to ComfyUI to download image: {e}") from e
        except httpx.HTTPStatusError as e:
            raise ComfyUIConnectionError(f"ComfyUI returned an error when downloading image: {e.response.status_code} - {e.response.text}") from e

    async def _get_history(self, prompt_id: str) -> dict:
        for attempt in range(HISTORY_MAX_RETRIES):
            try:
                async with httpx.AsyncClient(timeout=self.http_timeout) as client:
                    response = await client.get(f"{self.base_api_url}/history/{prompt_id}")
                    response.raise_for_status()

                history = response.json()
                if prompt_id in history:
                    logger.info(f"Successfully retrieved history for prompt {prompt_id} on attempt {attempt + 1}.")
                    return history[prompt_id]
                else:
                    logger.warning(f"History for prompt {prompt_id} not yet available (attempt {attempt + 1}/{HISTORY_MAX_RETRIES}). Retrying...")

            except json.JSONDecodeError:
                logger.warning(f"Received non-JSON response for history {prompt_id} (attempt {attempt + 1}/{HISTORY_MAX_RETRIES}). Retrying...")
            except httpx.RequestError as e:
                raise ComfyUIConnectionError(f"Could not connect to ComfyUI to get history: {e}") from e
            except httpx.HTTPStatusError as e:
                raise ComfyUIConnectionError(f"ComfyUI returned an error when getting history: {e.response.status_code} - {e.response.text}") from e
            
            await asyncio.sleep(HISTORY_RETRY_DELAY)
        
        raise WorkflowExecutionError(f"Failed to retrieve history for prompt_id {prompt_id} after {HISTORY_MAX_RETRIES} attempts.")

    async def get_queue_size(self) -> int:
        """Fetches the current queue size (running + pending) from the ComfyUI server."""
        try:
            async with httpx.AsyncClient(timeout=self.http_timeout) as client:
                response = await client.get(f"{self.base_api_url}/queue")
                response.raise_for_status()
                data = response.json()
                size = len(data.get('queue_running', [])) + len(data.get('queue_pending', []))
                logger.debug(f"Queue size for {self.base_api_url} is {size}")
                return size
        except (httpx.RequestError, httpx.HTTPStatusError) as e:
            logger.warning(f"Could not get queue size for {self.base_api_url}: {e}")
            raise ComfyUIConnectionError(f"Could not get queue size from {self.base_api_url}") from e

    async def upload_image_from_url(self, image_url: str) -> str:
        """Downloads an image from a URL and uploads it to the ComfyUI server."""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(image_url) as response:
                    response.raise_for_status()
                    image_data = await response.read()
                    content_type = response.headers.get('Content-Type', 'application/octet-stream')

                filename = Path(urlparse(image_url).path).name or "uploaded_image.bin"
                form_data = aiohttp.FormData()
                form_data.add_field('image', image_data, filename=filename, content_type=content_type)
                
                async with session.post(f"{self.base_api_url}/upload/image", data=form_data) as upload_response:
                    upload_response.raise_for_status()
                    response_json = await upload_response.json()
                    if 'name' not in response_json:
                        raise ComfyUIError(f"ComfyUI image upload response did not contain a 'name' field. Response: {response_json}")
                    return response_json['name']

        except aiohttp.ClientError as e:
            raise ComfyUIConnectionError(f"Failed to download or upload image from URL {image_url}: {e}") from e
        except Exception as e:
            raise ComfyUIError(f"An unexpected error occurred during image upload: {e}") from e

    async def run_workflow_and_get_image(
        self,
        workflow: dict,
        output_node_title: str,
        output_dir_path: str,
        output_url_base: str
    ) -> str:
        """
        Queues a workflow, waits for completion, finds the output image from the
        specified node, saves it, and returns its public URL.
        """
        client_id = str(uuid.uuid4())
        prompt_id = None
        try:
            queue_response = await self._queue_prompt(workflow, client_id)
            prompt_id = queue_response.get('prompt_id')
            if not prompt_id:
                raise WorkflowExecutionError(f"ComfyUI API did not return a prompt_id. Response: {queue_response}")
            logger.info(f"Prompt queued with ID: {prompt_id} on server {self.base_api_url}")

            ws_url = f"ws://{self.server_address}/ws?clientId={client_id}"
            logger.info(f"Connecting to WebSocket: {ws_url}")
            try:
                async with asyncio.timeout(self.generation_timeout):
                    async with websockets.connect(ws_url) as websocket:
                        while True:
                            message_data = await websocket.recv()
                            if isinstance(message_data, bytes):
                                message_str = message_data.decode('utf-8', errors='ignore')
                            else:
                                message_str = message_data
                            
                            try:
                                message = json.loads(message_str)
                            except json.JSONDecodeError:
                                logger.warning(f"Received non-JSON WebSocket message: {message_str[:200]}")
                                continue
                            
                            if message['type'] == 'executing' and message['data']['node'] is None and message['data']['prompt_id'] == prompt_id:
                                logger.info(f"Execution finished for prompt_id: {prompt_id}")
                                break
            except TimeoutError as e:
                raise WorkflowExecutionError(f"Generation timed out after {self.generation_timeout}s for prompt_id: {prompt_id}") from e
            except (websockets.exceptions.WebSocketException, ConnectionRefusedError) as e:
                raise ComfyUIConnectionError(f"Could not connect to ComfyUI WebSocket: {e}") from e

            history = await self._get_history(prompt_id)
            
            # Find the target output node by its title in the original workflow prompt
            output_node_id = None
            for node_id, node_data in workflow.items():
                if node_data.get("_meta", {}).get("title") == output_node_title:
                    output_node_id = node_id
                    break

            if not output_node_id:
                raise WorkflowExecutionError(f"Node with title '{output_node_title}' not found in the executed workflow.")

            outputs = history.get('outputs', {})
            node_output = outputs.get(output_node_id)
            if not node_output or 'images' not in node_output:
                raise WorkflowExecutionError(f"No image output found for node ID {output_node_id} (title: {output_node_title}).")

            image_info = node_output['images'][0]
            filename, subfolder, image_type = image_info['filename'], image_info.get('subfolder', ''), image_info['type']
            
            logger.info(f"Downloading final image: {filename}")
            image_data = await self._get_image_data(filename, subfolder, image_type)

            unique_filename = f"{uuid.uuid4()}{Path(filename).suffix}"
            output_path = Path(output_dir_path) / unique_filename
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, 'wb') as f: f.write(image_data)
            logger.info(f"Image saved to: {output_path}")

            final_url = f"{output_url_base.rstrip('/')}/{unique_filename}"
            logger.info(f"Returning public URL: {final_url}")
            return final_url
        
        except Exception as e:
            logger.error(f"Unhandled exception in run_workflow_and_get_image (prompt_id: {prompt_id})", exc_info=True)
            raise e