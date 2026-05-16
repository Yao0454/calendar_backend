"""User Profile Management Routes"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from auth.deps import get_current_session
from auth.models import SessionPrincipal
from data import calendar_db

router = APIRouter(prefix="/profile", tags=["profile"])


class InterestIn(BaseModel):
    category: str
    tag: str
    keywords: list
    weight: float = 1.0


class InterestUpdate(BaseModel):
    keywords: list | None = None
    weight: float | None = None


@router.get("/interests")
async def get_interests(
    category: str | None = None,
    session: SessionPrincipal = Depends(get_current_session)
):
    interests = calendar_db.get_user_interests(session.user_id, category)
    return {
        "user_id": session.user_id,
        "interests": interests,
        "total": len(interests)
    }


@router.post("/interests", status_code=201)
async def create_interest(
    req: InterestIn,
    session: SessionPrincipal = Depends(get_current_session)
):
    interest = calendar_db.create_or_update_interest(
        session.user_id,
        req.category,
        req.tag,
        req.keywords,
        req.weight
    )
    if not interest:
        raise HTTPException(status_code=400, detail="Failed to create interest")
    
    return {
        "status": "created",
        "interest": interest
    }


@router.put("/interests/{interest_id}")
async def update_interest(
    interest_id: int,
    req: InterestUpdate,
    session: SessionPrincipal = Depends(get_current_session)
):
    interests = calendar_db.get_user_interests(session.user_id)
    target = None
    for interest in interests:
        if interest["id"] == interest_id:
            target = interest
            break

    if not target:
        raise HTTPException(status_code=404, detail="Interest not found")

    if req.keywords is not None:
        from services.keyword_expander import expand_keywords
        keywords = await expand_keywords(req.keywords)
    else:
        keywords = target["keywords"]
    weight = req.weight if req.weight is not None else target["weight"]

    updated = calendar_db.create_or_update_interest(
        session.user_id,
        target["category"],
        target["tag"],
        keywords,
        weight
    )

    return {
        "status": "updated",
        "interest": updated
    }


@router.delete("/interests/{interest_id}", status_code=204)
async def delete_interest(
    interest_id: int,
    session: SessionPrincipal = Depends(get_current_session)
):
    calendar_db.delete_interest(session.user_id, interest_id)
    return {"status": "deleted"}


@router.get("/summary")
async def get_profile_summary(
    session: SessionPrincipal = Depends(get_current_session)
):
    interests = calendar_db.get_user_interests(session.user_id)
    
    summary = {
        "research": [],
        "project": [],
        "skill": []
    }
    
    for interest in interests:
        category = interest["category"]
        if category in summary:
            summary[category].append(interest["tag"])

    return {
        "user_id": session.user_id,
        "total_interests": len(interests),
        "summary": summary
    }
