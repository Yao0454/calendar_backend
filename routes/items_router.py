from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from auth.deps import get_current_session
from auth.models import SessionPrincipal
from data import calendar_db as db

router = APIRouter(prefix="/items", tags=["items"])


# ── Schemas ───────────────────────────────────────────────────────────────────

class EventIn(BaseModel):
    title: str
    date: str | None = None
    time: str | None = None
    location: str | None = None
    notes: str | None = None
    is_pinned: bool = False


class TodoIn(BaseModel):
    title: str
    deadline: str | None = None
    priority: str = "medium"
    notes: str | None = None
    is_done: bool = False
    is_pinned: bool = False


class PinBody(BaseModel):
    is_pinned: bool


class DoneBody(BaseModel):
    is_done: bool


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get("")
def get_all(session: SessionPrincipal = Depends(get_current_session)):
    return {
        "events": db.get_events(session.user_id),
        "todos":  db.get_todos(session.user_id),
    }


# Events
@router.post("/events", status_code=201)
def create_event(body: EventIn, session: SessionPrincipal = Depends(get_current_session)):
    return db.create_event(session.user_id, body.model_dump())


@router.put("/events/{event_id}")
def update_event(event_id: int, body: EventIn,
                 session: SessionPrincipal = Depends(get_current_session)):
    result = db.update_event(event_id, session.user_id, body.model_dump())
    if not result:
        raise HTTPException(404, "Not found")
    return result


@router.delete("/events/{event_id}", status_code=204)
def delete_event(event_id: int, session: SessionPrincipal = Depends(get_current_session)):
    if not db.delete_event(event_id, session.user_id):
        raise HTTPException(404, "Not found")


@router.patch("/events/{event_id}/pin")
def pin_event(event_id: int, body: PinBody,
              session: SessionPrincipal = Depends(get_current_session)):
    db.set_event_pinned(event_id, session.user_id, body.is_pinned)
    return {"ok": True}


# Todos
@router.post("/todos", status_code=201)
def create_todo(body: TodoIn, session: SessionPrincipal = Depends(get_current_session)):
    return db.create_todo(session.user_id, body.model_dump())


@router.put("/todos/{todo_id}")
def update_todo(todo_id: int, body: TodoIn,
                session: SessionPrincipal = Depends(get_current_session)):
    result = db.update_todo(todo_id, session.user_id, body.model_dump())
    if not result:
        raise HTTPException(404, "Not found")
    return result


@router.delete("/todos/{todo_id}", status_code=204)
def delete_todo(todo_id: int, session: SessionPrincipal = Depends(get_current_session)):
    if not db.delete_todo(todo_id, session.user_id):
        raise HTTPException(404, "Not found")


@router.patch("/todos/{todo_id}/done")
def done_todo(todo_id: int, body: DoneBody,
              session: SessionPrincipal = Depends(get_current_session)):
    db.set_todo_done(todo_id, session.user_id, body.is_done)
    return {"ok": True}


@router.patch("/todos/{todo_id}/pin")
def pin_todo(todo_id: int, body: PinBody,
             session: SessionPrincipal = Depends(get_current_session)):
    db.set_todo_pinned(todo_id, session.user_id, body.is_pinned)
    return {"ok": True}
