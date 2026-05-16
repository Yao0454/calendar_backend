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
    # Interleave sources so github/arxiv appear together in the feed
    by_source: dict = {}
    for rec in recommendations:
        s = rec.get("source", "arxiv")
        by_source.setdefault(s, []).append(rec)

    mixed = []
    source_keys = sorted(by_source.keys())
    iters = {s: iter(by_source[s]) for s in source_keys}
    active = list(source_keys)
    while active and len(mixed) < total:
        for s in list(active):
            item = next(iters[s], None)
            if item is None:
                active.remove(s)
            else:
                mixed.append(item)

    paginated = mixed[offset:offset + limit]

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


@router.post("/refresh")
async def refresh_recommendations(
    session: SessionPrincipal = Depends(get_current_session)
):
    """手动触发爬虫 + 推荐生成（无需等待定时任务）"""
    from services.recommendation_engine import recommendation_engine
    from services.background_tasks import background_manager
    try:
        # If no content exists yet, run crawler first
        content_count = len(calendar_db.get_content_items(source="arxiv", limit=1))
        if content_count == 0:
            await background_manager.run_crawlers()
        stats = await recommendation_engine.generate_recommendations(session.user_id)
        return {"status": "done", "stats": stats}
    except Exception as e:
        return {"status": "error", "message": str(e)}


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
