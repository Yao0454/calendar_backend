import logging
import sys
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from auth import deps as auth_deps
from auth import router as auth_router
from auth.auth_service import AuthService
from auth.models import SessionPrincipal
from auth.stores.session_store import SessionStore
from auth.stores.user_store import UserStore
from config import MODEL_NAME
from models import Event, ExtractRequest, ExtractResponse, HealthResponse, Todo
from services import extractor
from services.file_handler import compress_image_base64, extract_pdf_text
from services.ollama import (
    OllamaModelNotFoundError,
    OllamaTimeoutError,
    OllamaUnavailableError,
    is_available,
)

# ── Auth setup ────────────────────────────────────────────────────────────────
_DB = Path(__file__).parent / "data" / "db"
_user_store = UserStore(_DB / "users.json")
_session_store = SessionStore(_DB / "sessions.json")
_auth_svc = AuthService(_user_store, _session_store)

auth_deps.set_session_store(_session_store)
auth_router.set_auth_service(_auth_svc)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    if await is_available():
        logger.info("Ollama is reachable at startup")
    else:
        logger.warning(
            "Ollama is NOT reachable — start 'ollama serve' before sending requests"
        )
    yield


app = FastAPI(title="Calendar Extractor", lifespan=lifespan)
app.include_router(auth_router.router)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", response_model=HealthResponse)
async def health():
    ollama_ok = await is_available()
    return HealthResponse(status="ok", model=MODEL_NAME, ollama=ollama_ok)


@app.post("/extract", response_model=ExtractResponse)
async def extract(
    req: ExtractRequest,
    _session: SessionPrincipal = Depends(auth_deps.get_current_session),
):
    if not req.text and not req.image_base64 and not req.file_base64:
        raise HTTPException(
            status_code=400, detail="请提供 text、image_base64 或 file_base64 之一"
        )

    try:
        if req.text:
            result = await extractor.extract_from_text(req.text, req.current_date)

        elif req.image_base64:
            mime = req.image_mime or "image/jpeg"
            compressed_b64, compressed_mime = compress_image_base64(
                req.image_base64, mime
            )
            result = await extractor.extract_from_image(
                compressed_b64, compressed_mime, req.current_date
            )

        else:
            file_type = (req.file_type or "").lower()
            if file_type == "pdf":
                text = extract_pdf_text(str(req.file_base64))
                result = await extractor.extract_from_text(text, req.current_date)
            else:
                raise HTTPException(
                    status_code=400, detail=f"不支持的文件类型：{file_type}"
                )

    except OllamaUnavailableError:
        raise HTTPException(
            status_code=503, detail="Ollama 服务不可达，请确认已运行 ollama serve"
        )
    except OllamaModelNotFoundError as e:
        raise HTTPException(
            status_code=503,
            detail=f"模型 {e.model} 未找到，请运行 ollama pull {e.model}",
        )
    except OllamaTimeoutError:
        raise HTTPException(status_code=504, detail="Ollama 推理超时")
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))

    events = [Event(**e) for e in result.get("events", [])]
    todos = [Todo(**t) for t in result.get("todos", [])]
    return ExtractResponse(events=events, todos=todos)
