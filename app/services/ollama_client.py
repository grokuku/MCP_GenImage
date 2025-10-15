# app/services/ollama_client.py
import httpx
import logging
from typing import List, Dict, Any, Optional, Union
import json
import re
import asyncio

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

JSON_GENERATION_SYSTEM_MESSAGE = """
You are a helpful assistant that ALWAYS responds with a valid JSON object or a valid JSON list.
You must follow the user's instructions to generate the content of the JSON.
Your final output must be ONLY the JSON structure, with no extra text, explanations, or markdown formatting.
"""

class OllamaError(Exception):
    """Custom exception for Ollama client errors."""
    pass

class OllamaJsonParseError(OllamaError):
    """Custom exception for when JSON parsing fails, containing the raw response."""
    def __init__(self, message, content: str):
        super().__init__(message)
        self.content = content


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
        self.client = httpx.AsyncClient(base_url=self.api_url, timeout=180.0) # Timeout reverted to 3 minutes
        logger.info(f"Ollama client instantiated for model '{self.model_name}' at {self.api_url}")

    async def __aenter__(self):
        """Enter the async context manager."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Exit the async context manager, ensuring the client is closed."""
        await self.close()

    async def _generate(
        self, messages: List[Dict[str, Any]], expect_json: bool = False, max_retries: int = 3
    ) -> Union[str, Dict, List]:
        """
        Private helper to send a structured request to the Ollama chat API.
        Includes retry logic for JSON parsing.
        """
        options = { "num_ctx": self.context_window } if self.context_window > 0 else {}
        request_body = {
            "model": self.model_name, "messages": messages, "stream": False,
            "keep_alive": self.keep_alive, "options": options
        }
        if expect_json:
            request_body["format"] = "json"

        last_error = None
        last_content = ""
        for attempt in range(max_retries):
            try:
                log_safe_messages = [
                    {k: (v if k != 'images' else f'[{len(v)} image(s)]') for k, v in msg.items()}
                    for msg in messages
                ]
                logger.debug(f"Sending request to Ollama (Attempt {attempt + 1}/{max_retries}): {log_safe_messages}")
                
                response = await self.client.post("/api/chat", json=request_body)
                response.raise_for_status()

                response_data = response.json()
                content = response_data.get("message", {}).get("content", "").strip()
                last_content = content # Store last response for potential error logging

                if not expect_json:
                    if content.startswith("```json"): content = content[7:-3].strip()
                    elif content.startswith("```"): content = content[3:-3].strip()
                    if content.startswith('"') and content.endswith('"'): content = content[1:-1].strip()
                    logger.debug(f"Received and cleaned text response from Ollama: {content}")
                    return content
                
                try:
                    parsed_json = json.loads(content)
                    logger.debug(f"Successfully parsed JSON response from Ollama: {parsed_json}")
                    return parsed_json
                except json.JSONDecodeError:
                    logger.warning(f"Attempt {attempt + 1}: Failed to parse JSON from LLM response. Content: {content}")
                    # Raise a specific error to be caught by the generic exception handler below,
                    # which will store it in last_error and trigger a retry.
                    raise OllamaJsonParseError(
                        "LLM returned malformed data that could not be parsed as JSON.",
                        content=last_content
                    )
            
            except (httpx.TimeoutException, httpx.RequestError, httpx.HTTPStatusError) as e:
                logger.error(f"HTTP error on attempt {attempt + 1}: {e}")
                last_error = e
            except Exception as e:
                logger.error(f"An unexpected error occurred on attempt {attempt + 1}: {e}", exc_info=True)
                last_error = e

            if attempt < max_retries - 1:
                await asyncio.sleep(1)

        logger.error(f"All {max_retries} attempts to get a valid response from Ollama failed.")
        if isinstance(last_error, OllamaJsonParseError):
            raise last_error
        if isinstance(last_error, httpx.TimeoutException):
            raise OllamaError(f"Ollama server at {self.api_url} took too long to respond.") from last_error
        if isinstance(last_error, httpx.RequestError):
            raise OllamaError(f"Could not connect to Ollama server at {self.api_url}.") from last_error
        if isinstance(last_error, httpx.HTTPStatusError):
            raise OllamaError(f"Ollama server returned an error: {last_error.response.status_code}") from last_error
        raise OllamaError("An unexpected error occurred while processing the Ollama response.") from last_error

    async def generate_text(self, prompt: str) -> str:
        """
        Sends a simple text prompt to the LLM and gets a text response.
        """
        if not prompt: return ""
        messages = [{"role": "user", "content": prompt}]
        return await self._generate(messages, expect_json=False)

    async def generate_json(self, prompt: str) -> Union[Dict, List]:
        """
        Sends a prompt and expects a JSON object/list in response.
        Handles retries and parsing internally with a dedicated system prompt.
        """
        if not prompt: return {}
        messages = [
            {"role": "system", "content": JSON_GENERATION_SYSTEM_MESSAGE},
            {"role": "user", "content": prompt}
        ]
        return await self._generate(messages, expect_json=True)

    async def enhance_positive_prompt(self, base_prompt: str, examples: Optional[str] = None) -> str:
        """
        Takes a user's prompt and uses the LLM to enhance it.
        Optionally uses examples to guide the enhancement.
        """
        if not base_prompt: return ""

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