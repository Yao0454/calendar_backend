from pathlib import Path
from auth.models import UserRecord
from auth.stores.base_json_store import BaseJsonStore


class UserStore(BaseJsonStore):
    def __init__(self, file_path: str | Path) -> None:
        super().__init__(file_path)
        self._id: dict[str, dict] = {}
        self._name: dict[str, dict] = {}
        self._reload()

    def _reload(self) -> None:
        rows: list[dict] = self.read_json()
        self._id = {r["id"]: r for r in rows}
        self._name = {r["username"]: r for r in rows}

    def get_by_id(self, uid: str) -> UserRecord | None:
        d = self._id.get(uid)
        return UserRecord(**d) if d else None

    def get_by_username(self, username: str) -> UserRecord | None:
        d = self._name.get(username)
        return UserRecord(**d) if d else None

    def save(self, user: UserRecord) -> None:
        with self._lock:
            rows: list[dict] = self.read_json()
            entry = {
                "id": user.id,
                "username": user.username,
                "password_hash": user.password_hash,
                "status": user.status,
            }
            for i, r in enumerate(rows):
                if r["id"] == user.id:
                    rows[i] = entry
                    break
            else:
                rows.append(entry)
            self.write_json_atomic(rows)
            self._reload()
