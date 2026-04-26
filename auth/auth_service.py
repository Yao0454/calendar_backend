import uuid
from datetime import UTC, datetime, timedelta

from auth.models import SessionPrincipal, UserRecord
from auth.password_service import PasswordService
from auth.stores.session_store import SessionStore
from auth.stores.user_store import UserStore

SESSION_TTL_DAYS = 30


class AuthService:
    def __init__(self, user_store: UserStore, session_store: SessionStore) -> None:
        self.users = user_store
        self.sessions = session_store

    def register(self, username: str, password: str) -> bool:
        if self.users.get_by_username(username) is not None:
            return False
        user = UserRecord(
            id=str(uuid.uuid4()),
            username=username,
            password_hash=PasswordService.hash_password(password),
            status="active",
        )
        self.users.save(user)
        return True

    def login(self, username: str, password: str) -> SessionPrincipal | None:
        user = self.users.get_by_username(username)
        if not user or not PasswordService.verify(password, user.password_hash):
            return None
        now = datetime.now(UTC)
        session = SessionPrincipal(
            session_id=str(uuid.uuid4()),
            user_id=user.id,
            username=user.username,
            issued_at=now,
            expires_at=now + timedelta(days=SESSION_TTL_DAYS),
        )
        self.sessions.create(session)
        return session

    def logout(self, session_id: str) -> None:
        self.sessions.revoke(session_id)
