import logging

import httpx

from config import MODEL_NAME, OLLAMA_BASE_URL, REQUEST_TIMEOUT

logger = logging.getLogger(__name__)


async def chat(messages: list[dict]) -> str:
    payload = {
        "model": MODEL_NAME,
        "stream": False,
        "messages": messages,
    }
    async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
        try:
            resp = await client.post(f"{OLLAMA_BASE_URL}/api/chat", json=payload)
        except httpx.ConnectError:
            raise OllamaUnavailableError()
        except httpx.TimeoutException:
            raise OllamaTimeoutError()

    if resp.status_code == 404:
        raise OllamaModelNotFoundError(MODEL_NAME)
    if resp.status_code != 200:
        raise OllamaUnavailableError()

    data = resp.json()
    return data["message"]["content"]


async def is_available() -> bool:
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            resp = await client.get(f"{OLLAMA_BASE_URL}/api/tags")
            return resp.status_code == 200
    except Exception:
        return False


class OllamaUnavailableError(Exception):
    pass


class OllamaModelNotFoundError(Exception):
    def __init__(self, model: str):
        self.model = model
        super().__init__(model)


class OllamaTimeoutError(Exception):
    pass
