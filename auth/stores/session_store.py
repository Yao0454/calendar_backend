from datetime import datetime, timezone
from pathlib import Path
from auth.models import SessionPrincipal
from auth.stores.base_json_store import BaseJsonStore


class SessionStore(BaseJsonStore):
    def __init__(self, file_path: str | Path) -> None:
        super().__init__(file_path)
        self._index: dict[str, dict] = {}
        self._reload()

    def _reload(self) -> None:
        rows: list[dict] = self.read_json()
        self._index = {r["session_id"]: r for r in rows}

    def get(self, session_id: str) -> SessionPrincipal | None:
        d = self._index.get(session_id)
        if not d:
            return None
        expires = datetime.fromisoformat(d["expires_at"])
        if expires <= datetime.now(timezone.utc):
            return None
        return SessionPrincipal(
            session_id=d["session_id"],
            user_id=d["user_id"],
            username=d["username"],
            issued_at=datetime.fromisoformat(d["issued_at"]),
            expires_at=expires,
        )

    def create(self, session: SessionPrincipal) -> None:
        with self._lock:
            rows: list[dict] = self.read_json()
            entry = {
                "session_id": session.session_id,
                "user_id": session.user_id,
                "username": session.username,
                "issued_at": session.issued_at.isoformat(),
                "expires_at": session.expires_at.isoformat(),
            }
            for i, r in enumerate(rows):
                if r["session_id"] == session.session_id:
                    rows[i] = entry
                    break
            else:
                rows.append(entry)
            self.write_json_atomic(rows)
            self._reload()

    def revoke(self, session_id: str) -> None:
        with self._lock:
            rows = [r for r in self.read_json() if r["session_id"] != session_id]
            self.write_json_atomic(rows)
            self._reload()

    def cleanup_expired(self) -> int:
        with self._lock:
            now = datetime.now(timezone.utc)
            rows = self.read_json()
            valid = [r for r in rows if datetime.fromisoformat(r["expires_at"]) > now]
            removed = len(rows) - len(valid)
            if removed:
                self.write_json_atomic(valid)
                self._reload()
            return removed
