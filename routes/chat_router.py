"""Chat & Planning routes"""

import uuid
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from auth.deps import get_current_session
from auth.models import SessionPrincipal
from data import calendar_db
from services.planner_agent import planner
from services.ollama import OllamaUnavailableError, OllamaTimeoutError, OllamaModelNotFoundError

router = APIRouter(prefix="/chat", tags=["chat"])


class StartChatRequest(BaseModel):
    user_request: str


class SendMessageRequest(BaseModel):
    session_id: str
    message: str


class ConfirmPlanRequest(BaseModel):
    draft_id: int
    confirm: bool = True


class ChatMessage(BaseModel):
    id: int
    role: str
    content: str
    created_at: str


@router.post("/start", status_code=201)
async def start_chat(
    req: StartChatRequest,
    session: SessionPrincipal = Depends(get_current_session)
):
    try:
        session_id = str(uuid.uuid4())
        
        result = await planner.start_conversation(session.user_id, req.user_request)
        
        calendar_db.save_chat_message(
            session.user_id,
            session_id,
            "user",
            req.user_request
        )
        
        calendar_db.save_chat_message(
            session.user_id,
            session_id,
            "assistant",
            result["ai_response"]
        )
        
        return {
            "session_id": session_id,
            "ai_response": result["ai_response"],
            "schedule_context": result["schedule_context"]
        }
    
    except OllamaUnavailableError:
        raise HTTPException(status_code=503, detail="Ollama 服务不可达")
    except OllamaModelNotFoundError as e:
        raise HTTPException(status_code=503, detail=f"模型 {e.model} 未找到")
    except OllamaTimeoutError:
        raise HTTPException(status_code=504, detail="Ollama 推理超时")


@router.post("/message")
async def send_message(
    req: SendMessageRequest,
    session: SessionPrincipal = Depends(get_current_session)
):
    try:
        calendar_db.save_chat_message(
            session.user_id,
            req.session_id,
            "user",
            req.message
        )
        
        history = calendar_db.get_chat_history(session.user_id, req.session_id)
        
        messages = [
            {
                "role": "system",
                "content": planner._build_system_prompt()
            }
        ]
        
        for msg in history:
            messages.append({
                "role": msg["role"],
                "content": msg["content"]
            })
        
        from services import ollama
        ai_response = await ollama.chat(messages)
        
        calendar_db.save_chat_message(
            session.user_id,
            req.session_id,
            "assistant",
            ai_response
        )
        
        return {
            "message": req.message,
            "ai_response": ai_response
        }
    
    except OllamaUnavailableError:
        raise HTTPException(status_code=503, detail="Ollama 服务不可达")
    except OllamaTimeoutError:
        raise HTTPException(status_code=504, detail="Ollama 推理超时")


@router.get("/history/{session_id}")
async def get_chat_history(
    session_id: str,
    session: SessionPrincipal = Depends(get_current_session)
):
    history = calendar_db.get_chat_history(session.user_id, session_id)
    return {"messages": history}


@router.post("/draft")
async def create_draft(
    req: SendMessageRequest,
    session: SessionPrincipal = Depends(get_current_session)
):
    try:
        history = calendar_db.get_chat_history(session.user_id, req.session_id)
        
        plan_result = await planner.generate_plan_from_response(
            session.user_id,
            history[0]["content"] if history else "",
            history[-1]["content"] if history else "",
            history
        )
        
        if not plan_result["success"]:
            raise HTTPException(status_code=400, detail=plan_result["error"])
        
        plan = plan_result["plan"]
        
        draft = calendar_db.create_planning_draft(
            session.user_id,
            title="AI规划方案",
            description=f"基于对话的规划方案",
            proposed_events=plan.get("events", []),
            proposed_todos=plan.get("todos", [])
        )
        
        return {
            "draft_id": draft["id"],
            "draft": draft
        }
    
    except OllamaUnavailableError:
        raise HTTPException(status_code=503, detail="Ollama 服务不可达")
    except OllamaTimeoutError:
        raise HTTPException(status_code=504, detail="Ollama 推理超时")


@router.get("/drafts")
async def get_drafts(
    status: str | None = None,
    session: SessionPrincipal = Depends(get_current_session)
):
    drafts = calendar_db.get_planning_drafts(session.user_id, status)
    return {"drafts": drafts}


@router.get("/drafts/{draft_id}")
async def get_draft_detail(
    draft_id: int,
    session: SessionPrincipal = Depends(get_current_session)
):
    draft = calendar_db.get_planning_draft(draft_id, session.user_id)
    if not draft:
        raise HTTPException(status_code=404, detail="Draft not found")
    return {"draft": draft}


@router.post("/confirm/{draft_id}")
async def confirm_draft(
    draft_id: int,
    req: ConfirmPlanRequest,
    session: SessionPrincipal = Depends(get_current_session)
):
    if req.confirm:
        result = calendar_db.confirm_planning_draft(draft_id, session.user_id)
        if not result:
            raise HTTPException(status_code=404, detail="Draft not found or already processed")
        return {
            "status": "confirmed",
            "events_imported": len(result["events"]),
            "todos_imported": len(result["todos"]),
            "data": result
        }
    else:
        success = calendar_db.reject_planning_draft(draft_id, session.user_id)
        return {
            "status": "rejected",
            "success": success
        }


@router.delete("/session/{session_id}")
async def clear_session(
    session_id: str,
    session: SessionPrincipal = Depends(get_current_session)
):
    calendar_db.clear_chat_session(session.user_id, session_id)
    return {"status": "cleared"}
