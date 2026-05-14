"""arXiv Daily Report Routes"""

from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from auth.deps import get_current_session
from auth.models import SessionPrincipal
from data import calendar_db
from services.report_generator import generate_daily_report_from_recommendations

router = APIRouter(prefix="/arxiv", tags=["arxiv"])


class PreferenceIn(BaseModel):
    push_time: str = "09:00"
    paper_count: int = 5
    categories: list = ["cs.AI", "cs.LG"]
    is_enabled: bool = True


@router.get("/preference")
async def get_preference(
    session: SessionPrincipal = Depends(get_current_session)
):
    preference = calendar_db.get_arxiv_preference(session.user_id)
    if not preference:
        return {
            "user_id": session.user_id,
            "push_time": "09:00",
            "paper_count": 5,
            "categories": ["cs.AI", "cs.LG"],
            "is_enabled": True,
            "is_default": True
        }
    return preference


@router.post("/preference")
async def update_preference(
    req: PreferenceIn,
    session: SessionPrincipal = Depends(get_current_session)
):
    preference = calendar_db.create_or_update_arxiv_preference(
        session.user_id,
        {
            "push_time": req.push_time,
            "paper_count": req.paper_count,
            "categories": req.categories,
            "is_enabled": req.is_enabled
        }
    )
    return {
        "status": "updated",
        "preference": preference
    }


@router.post("/report/generate")
async def generate_report(
    report_date: str | None = None,
    session: SessionPrincipal = Depends(get_current_session)
):
    result = await generate_daily_report_from_recommendations(
        session.user_id,
        report_date
    )
    
    if result.get("status") == "skipped":
        return {
            "status": "skipped",
            "message": result.get("reason", "没有可用的推荐内容")
        }
    
    return {
        "status": "success",
        "report": result.get("report"),
        "paper_count": result.get("paper_count", 0)
    }


@router.get("/report/today")
async def get_today_report(
    session: SessionPrincipal = Depends(get_current_session)
):
    today = datetime.now().strftime("%Y-%m-%d")
    report = calendar_db.get_daily_report(session.user_id, today)
    
    if not report:
        raise HTTPException(status_code=404, detail="今日日报尚未生成")
    
    return {"report": report}


@router.get("/report/{report_date}")
async def get_report_by_date(
    report_date: str,
    session: SessionPrincipal = Depends(get_current_session)
):
    report = calendar_db.get_daily_report(session.user_id, report_date)
    
    if not report:
        raise HTTPException(status_code=404, detail="日报不存在")
    
    return {"report": report}


@router.get("/reports")
async def get_reports_list(
    limit: int = 30,
    session: SessionPrincipal = Depends(get_current_session)
):
    reports = calendar_db.get_daily_reports_list(session.user_id, limit)
    return {
        "total": len(reports),
        "reports": reports
    }


@router.post("/report/{report_id}/download")
async def increment_download(
    report_id: int,
    session: SessionPrincipal = Depends(get_current_session)
):
    calendar_db.increment_report_download(report_id)
    return {"status": "downloaded"}
