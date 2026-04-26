from dataclasses import dataclass, field
from datetime import datetime


@dataclass(frozen=True)
class UserRecord:
    id: str
    username: str
    password_hash: str
    status: str


@dataclass
class SessionPrincipal:
    session_id: str
    user_id: str
    username: str
    issued_at: datetime = field(default_factory=datetime.now)
    expires_at: datetime = field(default_factory=datetime.now)
