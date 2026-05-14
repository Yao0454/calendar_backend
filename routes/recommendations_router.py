"""Content Recommendations Routes"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from auth.deps import get_current_session
from auth.models import SessionPrincipal
from data import calendar_db

router = APIRouter(prefix="/recommendations", tags=["recommendations"])


class ContentAction(BaseModel):
    action: str


@router.get("/feed")
async def get_recommendation_feed(
    unread_only: bool = False,
    limit: int = 20,
    offset: int = 0,
    session: SessionPrincipal = Depends(get_current_session)
):
    recommendations = calendar_db.get_user_recommendations(session.user_id, unread_only)
    
    total = len(recommendations)
    paginated = recommendations[offset:offset + limit]
    
    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "items": paginated
    }


@router.get("/{content_id}")
async def get_content_detail(
    content_id: int,
    session: SessionPrincipal = Depends(get_current_session)
):
    content = calendar_db.get_content_by_id(content_id)
    if not content:
        raise HTTPException(status_code=404, detail="Content not found")
    
    return {"content": content}


@router.post("/{content_id}/read")
async def mark_as_read(
    content_id: int,
    session: SessionPrincipal = Depends(get_current_session)
):
    calendar_db.mark_recommendation_read(session.user_id, content_id)
    return {"status": "marked_read"}


@router.post("/{content_id}/save")
async def save_content(
    content_id: int,
    session: SessionPrincipal = Depends(get_current_session)
):
    calendar_db.mark_recommendation_saved(session.user_id, content_id)
    return {"status": "saved"}


@router.get("/stats/summary")
async def get_stats_summary(
    session: SessionPrincipal = Depends(get_current_session)
):
    recommendations = calendar_db.get_user_recommendations(session.user_id)
    
    stats = {
        "total_recommendations": len(recommendations),
        "unread": sum(1 for r in recommendations if not r.get("read")),
        "saved": sum(1 for r in recommendations if r.get("saved")),
        "by_source": {}
    }
    
    for r in recommendations:
        source = r.get("source", "unknown")
        if source not in stats["by_source"]:
            stats["by_source"][source] = {"total": 0, "unread": 0}
        
        stats["by_source"][source]["total"] += 1
        if not r.get("read"):
            stats["by_source"][source]["unread"] += 1
    
    return stats
