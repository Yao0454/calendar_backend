import json
import os
import tempfile
from pathlib import Path
from threading import RLock
from typing import Any


class BaseJsonStore:
    def __init__(self, file_path: str | Path) -> None:
        self.file_path = Path(file_path)
        self.file_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = RLock()

    def read_json(self) -> Any:
        with self._lock:
            if not self.file_path.exists():
                return []
            with self.file_path.open("r", encoding="utf-8") as f:
                return json.load(f)

    def write_json_atomic(self, data: Any) -> None:
        with self._lock:
            tmp_dir = self.file_path.parent / "temp"
            tmp_dir.mkdir(parents=True, exist_ok=True)
            fd, tmp_str = tempfile.mkstemp(dir=str(tmp_dir), suffix=".tmp")
            tmp_path = Path(tmp_str)
            try:
                with os.fdopen(fd, "w", encoding="utf-8") as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
                    f.flush()
                    os.fsync(f.fileno())
                tmp_path.replace(self.file_path)
            except Exception:
                tmp_path.unlink(missing_ok=True)
                raise
            finally:
                tmp_path.unlink(missing_ok=True)
