# app/services/ollama_client.py
import httpx
import logging
from typing import List, Dict, Any, Optional

# NOTE: The direct import of 'settings' and the global client instance
# have been removed. The client will now be instantiated dynamically.

# Setup logger
logger = logging.getLogger(__name__)

# --- System Prompts for Prompt Enhancement ---
# These define the "personality" and instructions for the LLM.

ENHANCE_POSITIVE_PROMPT_SYSTEM_MESSAGE = """
You are an expert prompt engineer for advanced text-to-image generation models.
Your task is to refine and enrich a user's base prompt.
**Your final output must be in English.** If the user's prompt is in another language, you must translate it to English while performing the enhancement.
**If style examples are provided, use them as a strong guide for the tone, structure, and level of detail.**
**It is crucial to preserve all original keywords, concepts, and any technical syntax like weights (e.g., `(word:1.2)`) or embeddings.**
Your goal is to translate and correct the base prompt, add descriptive details and vivid imagery *around* the core concepts provided by the user, combining them into a coherent, powerful paragraph.
Do not replace the user's core ideas. Enhance them.
Do not add any preamble, just return the enhanced prompt in english.
"""

ENHANCE_NEGATIVE_PROMPT_SYSTEM_MESSAGE = """
You are an expert prompt engineer for advanced text-to-image generation models.
Your task is to create a coherent negative prompt.
You will be given the final positive prompt for context, and a list of
base negative concepts.
**It is crucial to preserve all original negative keywords, concepts, and technical embeddings (e.g., `(bad_hands:1.2)`).**
Clean up, organize, and add common negative terms (e.g., ugly, deformed, blurry, watermark, text) to the user's list, ensuring they do not contradict the positive prompt.
Do not add any preamble, just return the final negative prompt as a single line of comma-separated terms.
"""


class OllamaError(Exception):
    """Custom exception for Ollama client errors."""
    pass


class OllamaClient:
    """
    An asynchronous client to interact with an Ollama server for prompt manipulation.
    This client is designed to be instantiated dynamically and used as an async context manager.
    """
    def __init__(self, api_url: str, model_name: str, keep_alive: str = "5m", context_window: int = 0):
        if not api_url or not model_name:
            raise ValueError("Ollama API URL and model name are required.")
        self.api_url = api_url
        self.model_name = model_name
        self.keep_alive = keep_alive
        self.context_window = context_window
        # Set a much longer timeout for potentially slow LLM models
        self.client = httpx.AsyncClient(base_url=self.api_url, timeout=180.0)
        logger.info(f"Ollama client instantiated for model '{self.model_name}' at {self.api_url}")

    async def __aenter__(self):
        """Enter the async context manager."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Exit the async context manager, ensuring the client is closed."""
        await self.close()

    async def _generate(self, messages: List[Dict[str, Any]]) -> str:
        """
        Private helper to send a structured request to the Ollama chat API.
        Can handle both text-only and multimodal (text + image) messages.
        """
        options = { "num_ctx": self.context_window } if self.context_window > 0 else {}

        request_body = {
            "model": self.model_name,
            "messages": messages,
            "stream": False,  # We want the full response at once
            "keep_alive": self.keep_alive,
            "options": options
        }
        try:
            # To avoid logging base64 images, we'll create a log-safe version of the messages
            log_safe_messages = [
                {k: (v if k != 'images' else f'[{len(v)} image(s)]') for k, v in msg.items()}
                for msg in messages
            ]
            logger.debug(f"Sending request to Ollama: {log_safe_messages}")
            response = await self.client.post("/api/chat", json=request_body)
            response.raise_for_status()  # Raises HTTPStatusError for 4xx/5xx responses

            response_data = response.json()
            content = response_data.get("message", {}).get("content", "").strip()

            # Clean up potential markdown code blocks or quotes
            if content.startswith("```") and content.endswith("```"):
                content = content[3:-3].strip()
            if content.startswith('"') and content.endswith('"'):
                content = content[1:-1].strip()

            logger.debug(f"Received and cleaned response from Ollama: {content}")
            return content

        except httpx.TimeoutException as e:
            logger.error(f"Ollama request timed out after {self.client.timeout.read} seconds: {e}")
            raise OllamaError(f"Ollama server at {self.api_url} took too long to respond.") from e
        except httpx.RequestError as e:
            logger.error(f"An HTTP request error occurred when contacting Ollama: {e}")
            raise OllamaError(f"Could not connect to Ollama server at {self.api_url}. Is it running?") from e
        except httpx.HTTPStatusError as e:
            logger.error(f"Ollama server returned an error: {e.response.status_code} {e.response.text}")
            raise OllamaError(f"Ollama server returned an error: {e.response.status_code}") from e
        except Exception as e:
            logger.error(f"An unexpected error occurred in the Ollama client: {e}")
            raise OllamaError("An unexpected error occurred while processing the Ollama response.") from e

    async def enhance_positive_prompt(self, base_prompt: str, examples: Optional[str] = None) -> str:
        """
        Takes a user's prompt and uses the LLM to enhance it.
        Optionally uses examples to guide the enhancement.
        """
        if not base_prompt:
            return ""

        user_content = base_prompt
        if examples:
            user_content = (
                "Here are some examples of high-quality prompts for the desired style:\n"
                f"---\n{examples}\n---\n"
                "Now, using those examples as a strong style guide, please enhance the following user prompt:\n"
                f"\"{base_prompt}\""
            )

        messages = [
            {"role": "system", "content": ENHANCE_POSITIVE_PROMPT_SYSTEM_MESSAGE},
            {"role": "user", "content": user_content}
        ]
        return await self._generate(messages)

    async def enhance_negative_prompt(self, base_negative: str, positive_context: str) -> str:
        """
        Takes a user's negative prompt and enhances it using the final
        positive prompt as context.
        """
        if not base_negative:
            # If there's no base negative prompt, we can still generate a standard one.
            base_negative = "standard negative terms"

        user_message = (
            f"Positive Prompt Context: \"{positive_context}\"\n\n"
            f"Base Negative Concepts: \"{base_negative}\""
        )

        messages = [
            {"role": "system", "content": ENHANCE_NEGATIVE_PROMPT_SYSTEM_MESSAGE},
            {"role": "user", "content": user_message}
        ]
        return await self._generate(messages)

    async def describe_image(self, prompt: str, image_base64: str) -> str:
        """
        Sends a prompt and a base64 encoded image to a multimodal LLM.
        """
        if not prompt or not image_base64:
            raise ValueError("A prompt and a base64 encoded image are required.")

        messages = [{
            "role": "user",
            "content": prompt,
            "images": [image_base64]
        }]
        return await self._generate(messages)

    async def list_models(self) -> List[Dict[str, Any]]:
        """
        Fetches the list of local models from the Ollama server.
        """
        try:
            response = await self.client.get("/api/tags")
            response.raise_for_status()
            return response.json().get("models", [])
        except httpx.RequestError as e:
            raise OllamaError(f"Could not connect to Ollama server at {self.api_url} to list models.") from e
        except httpx.HTTPStatusError as e:
            raise OllamaError(f"Ollama server returned an error when listing models: {e.response.status_code}") from e
        except Exception as e:
            raise OllamaError("An unexpected error occurred while listing Ollama models.") from e


    async def close(self):
        """Closes the underlying HTTPX client."""
        await self.client.aclose()
        logger.info("Ollama client has been closed.")