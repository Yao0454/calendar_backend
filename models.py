from typing import Literal

from pydantic import BaseModel


class ExtractRequest(BaseModel):
    text: str | None = None
    image_base64: str | None = None
    image_mime: str | None = "image/jpeg"
    file_base64: str | None = None
    file_type: str | None = None


class Event(BaseModel):
    title: str | None = None
    date: str | None = None
    time: str | None = None
    location: str | None = None
    notes: str | None = None


class Todo(BaseModel):
    title: str | None = None
    deadline: str | None = None
    priority: Literal["high", "medium", "low"] | None = None
    notes: str | None = None


class ExtractResponse(BaseModel):
    events: list[Event] = []
    todos: list[Todo] = []


class HealthResponse(BaseModel):
    status: str
    model: str
    ollama: bool
