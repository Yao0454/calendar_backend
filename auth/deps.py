from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from starlette import status

from auth.models import SessionPrincipal
from auth.stores.session_store import SessionStore

bearer = HTTPBearer(auto_error=False)

# Set by main.py
_session_store: SessionStore | None = None


def set_session_store(store: SessionStore) -> None:
    global _session_store
    _session_store = store


def get_current_session(
    creds: HTTPAuthorizationCredentials = Depends(bearer),
) -> SessionPrincipal:
    if creds is None or creds.scheme.lower() != "bearer":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail="需要登录：Bearer <session_id>")
    session = _session_store.get(creds.credentials.strip())  # type: ignore[union-attr]
    if session is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail="会话已过期，请重新登录")
    return session
