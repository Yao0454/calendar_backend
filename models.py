from typing import Any, Literal

from pydantic import BaseModel


class ExtractRequest(BaseModel):
    text: str | None = None
    image_base64: str | None = None
    image_mime: str | None = "image/jpeg"
    file_base64: str | None = None
    file_type: str | None = None
    current_date: str | None = None  # e.g. "2026-04-26", helps model resolve relative dates


class ExtractResponse(BaseModel):
    """Returned after AI extraction. Events/todos include server-assigned IDs for cloud sync."""
    events: list[dict[str, Any]] = []
    todos: list[dict[str, Any]] = []


class HealthResponse(BaseModel):
    status: str
    model: str
    ollama: bool
