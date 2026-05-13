# 📦 项目目录结构迁移实施指南

## 概述

本指南逐步说明如何将项目从当前的混乱结构迁移到推荐的清晰结构。

---

## 现有结构回顾

```
calendar_backend/
├── auth/                    # 认证模块
├── data/                    # 数据库
│   ├── calendar_db.py      # 大型单文件，包含所有数据库操作
│   └── calendar.db
├── routes/                  # 所有路由混在一个目录
│   ├── items_router.py
│   └── ...
├── services/               # 所有服务混在一个目录
│   ├── extractor.py
│   ├── ollama.py
│   └── ...
├── main.py
├── config.py
├── models.py
└── ...
```

---

## 目标结构

```
calendar_backend/
├── app/                          # 新的应用目录
│   ├── core/                     # 核心配置
│   ├── auth/                     # 认证模块
│   ├── calendar/                 # 日程模块
│   ├── chat/                     # 对话模块
│   ├── profile/                  # 画像模块
│   ├── recommendations/          # 推荐模块
│   └── db/                       # 数据库层
├── shared/                       # 共享工具
├── services/                     # 第三方服务集成
├── tests/                        # 测试
├── docs/                         # 文档
└── main.py                       # 入口
```

---

## 分步骤迁移指南

### 📌 阶段 1：准备工作（15分钟）

#### 1.1 备份现有代码
```bash
cd calendar_backend
git add .
git commit -m "backup: before refactoring"
```

#### 1.2 创建新目录结构
```bash
# 创建主目录
mkdir -p app/{core,auth,calendar,chat,profile,recommendations/crawler,db}
mkdir -p shared
mkdir -p services
mkdir -p tests/fixtures

# 创建 __init__.py 文件
touch app/__init__.py
touch app/core/__init__.py
touch app/auth/__init__.py
touch app/calendar/__init__.py
touch app/chat/__init__.py
touch app/profile/__init__.py
touch app/recommendations/__init__.py
touch app/recommendations/crawler/__init__.py
touch app/db/__init__.py
touch shared/__init__.py
touch services/__init__.py
touch tests/__init__.py
touch tests/fixtures/__init__.py
```

---

### 📌 阶段 2：核心配置迁移（10分钟）

#### 2.1 创建 app/core/config.py
```python
# 复制 config.py 的内容，并改进
import os
from typing import Optional

class Settings:
    # Ollama 配置
    OLLAMA_BASE_URL: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    MODEL_NAME: str = os.getenv("MODEL_NAME", "qwen3-vl:30b")
    
    # 服务器配置
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "5522"))
    REQUEST_TIMEOUT: int = int(os.getenv("REQUEST_TIMEOUT", "120"))
    
    # API 密钥
    GITHUB_API_TOKEN: Optional[str] = os.getenv("GITHUB_API_TOKEN")
    TWITTER_BEARER_TOKEN: Optional[str] = os.getenv("TWITTER_BEARER_TOKEN")
    
    # 爬虫配置
    ARXIV_FETCH_LIMIT: int = int(os.getenv("ARXIV_FETCH_LIMIT", "50"))
    GITHUB_FETCH_LIMIT: int = int(os.getenv("GITHUB_FETCH_LIMIT", "50"))
    TWITTER_FETCH_LIMIT: int = int(os.getenv("TWITTER_FETCH_LIMIT", "20"))

settings = Settings()
```

#### 2.2 创建 app/core/__init__.py
```python
from .config import settings

__all__ = ["settings"]
```

---

### 📌 阶段 3：认证模块迁移（10分钟）

#### 3.1 复制认证模块
```bash
# 复制现有的认证模块
cp auth/* app/auth/
```

#### 3.2 更新导入语句
在 `app/auth/` 中的所有 Python 文件，将导入改为相对导入：
```python
# 原来可能是：
from config import MODEL_NAME

# 改为：
from app.core import settings
```

---

### 📌 阶段 4：数据库层迁移（30分钟）

这是最重要的一步，需要拆分 `data/calendar_db.py`。

#### 4.1 创建 app/db/base.py
```python
"""数据库连接和基础函数"""
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

_DB_PATH = Path(__file__).parent.parent.parent / "data" / "calendar.db"

@contextmanager
def get_db_connection():
    """获取数据库连接"""
    conn = sqlite3.connect(str(_DB_PATH))
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()

def get_now() -> str:
    """获取当前 UTC 时间戳"""
    return datetime.now(timezone.utc).isoformat()
```

#### 4.2 创建 app/db/models.py
```python
"""数据库 schema 定义和初始化"""

INIT_TABLES_SQL = """
-- 现有表...
CREATE TABLE IF NOT EXISTS events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT NOT NULL,
    ...
);

-- 新表...
CREATE TABLE IF NOT EXISTS chat_messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT NOT NULL,
    ...
);
"""

def init_db():
    """初始化数据库"""
    from .base import get_db_connection
    
    _DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with get_db_connection() as conn:
        conn.executescript(INIT_TABLES_SQL)
```

#### 4.3 创建 app/db/calendar.py
```python
"""日程事件相关的数据操作"""
from .base import get_db_connection, get_now

def get_events(user_id: str):
    """获取用户的所有事件"""
    with get_db_connection() as conn:
        c = conn.cursor()
        rows = c.execute(
            "SELECT * FROM events WHERE user_id=? ORDER BY date",
            (user_id,)
        ).fetchall()
    return [dict(row) for row in rows]

def create_event(user_id: str, data: dict):
    """创建事件"""
    with get_db_connection() as conn:
        c = conn.cursor()
        c.execute(
            """INSERT INTO events (user_id, title, date, time, location, notes, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (user_id, data['title'], data.get('date'), data.get('time'), 
             data.get('location'), data.get('notes'), get_now(), get_now())
        )
        return get_events(user_id)[-1]

# ... 其他日程操作函数
```

#### 4.4 创建 app/db/chat.py
```python
"""对话相关的数据操作"""
from .base import get_db_connection, get_now

def save_chat_message(user_id: str, session_id: str, role: str, content: str):
    """保存聊天消息"""
    with get_db_connection() as conn:
        c = conn.cursor()
        c.execute(
            """INSERT INTO chat_messages (user_id, session_id, role, content, created_at)
               VALUES (?, ?, ?, ?, ?)""",
            (user_id, session_id, role, content, get_now())
        )

def get_chat_history(user_id: str, session_id: str, limit: int = 50):
    """获取对话历史"""
    with get_db_connection() as conn:
        rows = conn.execute(
            """SELECT * FROM chat_messages WHERE user_id=? AND session_id=?
               ORDER BY created_at ASC LIMIT ?""",
            (user_id, session_id, limit)
        ).fetchall()
    return [dict(row) for row in rows]

# ... 其他对话操作函数
```

#### 4.5 创建 app/db/profile.py
```python
"""用户画像相关的数据操作"""
from .base import get_db_connection, get_now

def create_or_update_interest(user_id: str, category: str, tag: str, keywords: list):
    """创建或更新兴趣"""
    # ... 实现
    pass

# ... 其他画像操作函数
```

#### 4.6 创建 app/db/recommendations.py
```python
"""推荐相关的数据操作"""
from .base import get_db_connection, get_now

def create_or_update_content(source: str, source_id: str, title: str, ...):
    """创建或更新内容"""
    # ... 实现
    pass

# ... 其他推荐操作函数
```

#### 4.7 创建 app/db/__init__.py
```python
"""数据库模块"""
from . import base, models, calendar, chat, profile, recommendations

def init_db():
    """初始化数据库"""
    models.init_db()

__all__ = ["base", "models", "calendar", "chat", "profile", "recommendations", "init_db"]
```

---

### 📌 阶段 5：日程模块迁移（15分钟）

#### 5.1 创建 app/calendar/models.py
```python
"""日程的 Pydantic 模型"""
from pydantic import BaseModel
from typing import Optional

class EventCreate(BaseModel):
    title: str
    date: Optional[str] = None
    time: Optional[str] = None
    location: Optional[str] = None
    notes: Optional[str] = None
    is_pinned: bool = False

class TodoCreate(BaseModel):
    title: str
    deadline: Optional[str] = None
    priority: str = "medium"
    notes: Optional[str] = None
    is_done: bool = False
    is_pinned: bool = False
```

#### 5.2 创建 app/calendar/service.py
```python
"""日程业务逻辑"""
from app.db import calendar as db_calendar

class CalendarService:
    @staticmethod
    async def get_all(user_id: str):
        """获取所有事件和待办"""
        events = db_calendar.get_events(user_id)
        todos = db_calendar.get_todos(user_id)
        return {"events": events, "todos": todos}
    
    @staticmethod
    async def create_event(user_id: str, event_data: dict):
        """创建事件"""
        return db_calendar.create_event(user_id, event_data)
    
    # ... 其他方法
```

#### 5.3 创建 app/calendar/router.py
```python
"""日程路由"""
from fastapi import APIRouter, Depends, HTTPException
from app.auth.deps import get_current_session
from app.auth.models import SessionPrincipal
from .models import EventCreate, TodoCreate
from .service import CalendarService

router = APIRouter(prefix="/items", tags=["calendar"])
service = CalendarService()

@router.get("")
async def get_all(session: SessionPrincipal = Depends(get_current_session)):
    return await service.get_all(session.user_id)

@router.post("/events", status_code=201)
async def create_event(
    body: EventCreate,
    session: SessionPrincipal = Depends(get_current_session)
):
    return await service.create_event(session.user_id, body.dict())

# ... 其他路由
```

---

### 📌 阶段 6：对话模块迁移（20分钟）

#### 6.1 创建 app/chat/models.py
```python
"""对话的数据模型"""
from pydantic import BaseModel

class StartChatRequest(BaseModel):
    user_request: str

class SendMessageRequest(BaseModel):
    session_id: str
    message: str
```

#### 6.2 创建 app/chat/planner_agent.py
```python
"""AI 规划助手 - 直接复制 services/planner_agent.py"""
# ... 复制整个 PlannerAgent 类
```

#### 6.3 创建 app/chat/service.py
```python
"""对话业务逻辑"""
from app.db import chat as db_chat
from .planner_agent import PlannerAgent

class ChatService:
    def __init__(self):
        self.planner = PlannerAgent()
    
    async def start_conversation(self, user_id: str, request: str):
        """开始对话"""
        session_id = str(uuid.uuid4())
        result = await self.planner.start_conversation(user_id, request)
        
        # 保存到数据库
        db_chat.save_chat_message(user_id, session_id, "user", request)
        db_chat.save_chat_message(user_id, session_id, "assistant", result["ai_response"])
        
        return {"session_id": session_id, "ai_response": result["ai_response"]}
    
    # ... 其他方法
```

#### 6.4 创建 app/chat/router.py
```python
"""对话路由"""
from fastapi import APIRouter, Depends, HTTPException
from app.auth.deps import get_current_session
from .models import StartChatRequest, SendMessageRequest
from .service import ChatService

router = APIRouter(prefix="/chat", tags=["chat"])
service = ChatService()

@router.post("/start", status_code=201)
async def start_chat(req: StartChatRequest, session = ...):
    return await service.start_conversation(session.user_id, req.user_request)

# ... 其他路由
```

---

### 📌 阶段 7：其他模块迁移（20分钟）

#### 7.1 用户画像模块
类似地创建：
- `app/profile/models.py`
- `app/profile/service.py`
- `app/profile/router.py`

#### 7.2 推荐系统模块
创建：
- `app/recommendations/models.py`
- `app/recommendations/crawler/base.py`
- `app/recommendations/crawler/arxiv.py`
- `app/recommendations/crawler/github.py`
- `app/recommendations/crawler/twitter.py`
- `app/recommendations/service.py`
- `app/recommendations/tasks.py`
- `app/recommendations/router.py`

---

### 📌 阶段 8：更新主应用（10分钟）

#### 8.1 创建新的 main.py
```python
"""应用入口"""
import logging
import sys
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# 导入新的模块
from app.core import settings
from app.auth.router import router as auth_router
from app.calendar.router import router as calendar_router
from app.chat.router import router as chat_router
from app.profile.router import router as profile_router
from app.recommendations.router import router as recommendations_router
from app.db import init_db
from services.ollama import is_available

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动时
    init_db()
    logger.info("Database initialized")
    
    if await is_available():
        logger.info("Ollama is available")
    else:
        logger.warning("Ollama is not available")
    
    yield
    
    # 关闭时
    logger.info("Shutting down")

app = FastAPI(
    title="Calendar Backend",
    lifespan=lifespan
)

# 添加中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(auth_router)
app.include_router(calendar_router)
app.include_router(chat_router)
app.include_router(profile_router)
app.include_router(recommendations_router)

@app.get("/health")
async def health():
    return {"status": "ok"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=True
    )
```

---

### 📌 阶段 9：清理和测试（20分钟）

#### 9.1 删除旧目录
```bash
# 检查是否所有代码都已迁移
# 然后删除旧的目录
rm -rf auth routes services/planner_agent.py services/content_crawler.py ...
# 保留 services/{ollama.py, file_handler.py, report_generator.py}
```

#### 9.2 更新 requirements.txt
```bash
pip install apscheduler feedparser
pip freeze > requirements.txt
```

#### 9.3 测试应用
```bash
# 启动 Ollama
ollama serve

# 在另一个终端启动应用
uvicorn main:app --reload

# 访问 http://localhost:5522/docs 测试 API
```

---

## 📋 迁移检查清单

- [ ] 备份现有代码
- [ ] 创建新目录结构
- [ ] 迁移核心配置 (core/config.py)
- [ ] 迁移认证模块 (auth/)
- [ ] 拆分数据库层 (db/)
  - [ ] base.py
  - [ ] models.py
  - [ ] calendar.py
  - [ ] chat.py
  - [ ] profile.py
  - [ ] recommendations.py
- [ ] 创建日程模块 (calendar/)
  - [ ] models.py
  - [ ] service.py
  - [ ] router.py
- [ ] 创建对话模块 (chat/)
  - [ ] models.py
  - [ ] planner_agent.py
  - [ ] service.py
  - [ ] router.py
- [ ] 创建画像模块 (profile/)
- [ ] 创建推荐模块 (recommendations/)
- [ ] 更新 main.py
- [ ] 删除旧目录
- [ ] 更新所有导入语句
- [ ] 测试所有功能
- [ ] 提交到 git

---

## 🚀 总耗时估计

| 阶段 | 任务 | 时间 |
|------|------|------|
| 1 | 准备工作 | 15 分钟 |
| 2 | 核心配置 | 10 分钟 |
| 3 | 认证模块 | 10 分钟 |
| 4 | 数据库层 | 30 分钟 |
| 5 | 日程模块 | 15 分钟 |
| 6 | 对话模块 | 20 分钟 |
| 7 | 其他模块 | 20 分钟 |
| 8 | 主应用 | 10 分钟 |
| 9 | 清理测试 | 20 分钟 |
| **总计** | | **~2.5 小时** |

---

## ✨ 迁移完成后的优势

✅ 项目结构清晰，易于导航
✅ 每个模块独立，易于维护
✅ 代码复用性提高
✅ 测试更容易编写
✅ 新功能更容易添加
✅ 团队协作更高效

