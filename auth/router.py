from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from auth.auth_service import AuthService
from auth.deps import get_current_session
from auth.models import SessionPrincipal

router = APIRouter(prefix="/auth", tags=["auth"])

# Injected by main.py after building the service instance
_auth_service: AuthService | None = None


def set_auth_service(svc: AuthService) -> None:
    global _auth_service
    _auth_service = svc


def _svc() -> AuthService:
    assert _auth_service is not None
    return _auth_service


# ── Schemas ──────────────────────────────────────────────────────────────────

class RegisterRequest(BaseModel):
    username: str = Field(..., min_length=2, max_length=32)
    password: str = Field(..., min_length=6)


class LoginRequest(BaseModel):
    username: str
    password: str


class SessionResponse(BaseModel):
    session_id: str
    username: str
    expires_at: str


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post("/register", status_code=201)
def register(body: RegisterRequest):
    ok = _svc().register(body.username, body.password)
    if not ok:
        raise HTTPException(status_code=409, detail="用户名已存在")
    return {"ok": True, "message": "注册成功"}


@router.post("/login", response_model=SessionResponse)
def login(body: LoginRequest):
    session = _svc().login(body.username, body.password)
    if session is None:
        raise HTTPException(status_code=401, detail="用户名或密码错误")
    return SessionResponse(
        session_id=session.session_id,
        username=session.username,
        expires_at=session.expires_at.isoformat(),
    )


@router.get("/me", response_model=SessionResponse)
def me(session: SessionPrincipal = Depends(get_current_session)):
    return SessionResponse(
        session_id=session.session_id,
        username=session.username,
        expires_at=session.expires_at.isoformat(),
    )


@router.post("/logout")
def logout(session: SessionPrincipal = Depends(get_current_session)):
    _svc().logout(session.session_id)
    return {"ok": True}
