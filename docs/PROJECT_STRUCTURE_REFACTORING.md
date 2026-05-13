# 📐 推荐的项目结构重新规划

## 当前问题分析

```
calendar_backend/
├── auth/                    # 认证模块
├── data/                    # 数据库
├── routes/                  # 所有路由都在这
│   ├── items_router.py     # 日程管理
│   ├── chat_router.py      # 对话（新）
│   ├── profile_router.py   # 用户画像（新）
│   └── recommendations_router.py  # 推荐（新）
├── services/               # 所有服务都在这
│   ├── extractor.py
│   ├── ollama.py
│   ├── planner_agent.py    # 规划（新）
│   ├── content_crawler.py  # 爬虫（新）
│   ├── recommendation_engine.py  # 推荐（新）
│   └── background_tasks.py # 后台任务（新）
└── main.py
```

**问题：**
- routes 和 services 目录太杂乱，混淆了不同功能的边界
- 难以快速找到相关文件
- 测试文件无处放置

---

## 🎯 推荐的新项构结构

```
calendar_backend/
│
├── 📁 app/                          # 应用核心代码
│   │
│   ├── 📁 core/                     # 核心配置和工具
│   │   ├── config.py               # 配置文件
│   │   ├── security.py             # 安全相关
│   │   └── dependencies.py         # 依赖注入
│   │
│   ├── 📁 auth/                     # 用户认证模块
│   │   ├── __init__.py
│   │   ├── service.py              # 认证服务
│   │   ├── models.py               # 认证模型
│   │   ├── router.py               # 认证路由
│   │   ├── password_service.py     # 密码服务
│   │   ├── deps.py                 # 依赖
│   │   └── stores/
│   │       ├── session_store.py
│   │       └── user_store.py
│   │
│   ├── 📁 calendar/                 # 日程管理模块（原 items）
│   │   ├── __init__.py
│   │   ├── models.py               # 日程模型
│   │   ├── router.py               # 日程路由
│   │   └── service.py              # 日程服务
│   │
│   ├── 📁 chat/                     # AI 对话模块（新）
│   │   ├── __init__.py
│   │   ├── models.py               # 对话模型（Request/Response）
│   │   ├── router.py               # 对话路由
│   │   ├── service.py              # 对话服务
│   │   └── planner_agent.py        # AI 规划助手
│   │
│   ├── 📁 profile/                  # 用户画像模块（新）
│   │   ├── __init__.py
│   │   ├── models.py               # 画像模型
│   │   ├── router.py               # 画像路由
│   │   └── service.py              # 画像服务
│   │
│   ├── 📁 recommendations/          # 推荐系统模块（新）
│   │   ├── __init__.py
│   │   ├── models.py               # 推荐模型
│   │   ├── router.py               # 推荐路由
│   │   ├── service.py              # 推荐引擎
│   │   ├── crawler/                # 内容爬虫
│   │   │   ├── __init__.py
│   │   │   ├── base.py             # 爬虫基类
│   │   │   ├── arxiv.py            # arXiv 爬虫
│   │   │   ├── github.py           # GitHub 爬虫
│   │   │   └── twitter.py          # Twitter 爬虫
│   │   └── tasks.py                # 后台任务
│   │
│   └── 📁 db/                       # 数据库层
│       ├── __init__.py
│       ├── base.py                 # 数据库基础函数
│       ├── models.py               # 数据库模型定义
│       ├── calendar.py             # 日程数据操作
│       ├── chat.py                 # 对话数据操作
│       ├── profile.py              # 画像数据操作
│       ├── recommendations.py      # 推荐数据操作
│       └── migrations/             # 数据库迁移（可选）
│
├── 📁 shared/                       # 共享工具和库
│   ├── __init__.py
│   ├── utils.py                    # 通用工具函数
│   ├── exceptions.py               # 自定义异常
│   ├── schemas.py                  # 通用 Pydantic 模型
│   └── constants.py                # 常量定义
│
├── 📁 services/                     # 第三方服务集成
│   ├── __init__.py
│   ├── ollama.py                   # Ollama 集成
│   ├── file_handler.py             # 文件处理
│   └── report_generator.py         # 报告生成
│
├── 📁 tests/                        # 单元测试
│   ├── __init__.py
│   ├── conftest.py                 # pytest 配置
│   ├── test_auth.py
│   ├── test_calendar.py
│   ├── test_chat.py
│   ├── test_profile.py
│   ├── test_recommendations.py
│   └── fixtures/
│       └── __init__.py
│
├── 📁 docs/                         # 文档
│   ├── README.md
│   ├── QUICK_START.md
│   ├── API.md
│   ├── ARCHITECTURE.md
│   └── DEPLOYMENT.md
│
├── main.py                          # 应用入口
├── requirements.txt                 # 依赖
├── .env.example                     # 环境变量示例
├── Dockerfile                       # Docker 配置
├── docker-compose.yml               # Docker Compose
└── pytest.ini                       # Pytest 配置

```

---

## 🔄 迁移计划

### 第一步：创建新的目录结构
```bash
mkdir -p app/core
mkdir -p app/auth
mkdir -p app/calendar
mkdir -p app/chat
mkdir -p app/profile
mkdir -p app/recommendations/crawler
mkdir -p app/db
mkdir -p shared
mkdir -p services
mkdir -p tests/fixtures
```

### 第二步：文件迁移映射

**认证模块**
```
auth/ → app/auth/
  ├── auth_service.py → service.py
  ├── models.py → models.py
  ├── router.py → router.py
  ├── password_service.py → password_service.py
  ├── deps.py → deps.py
  └── stores/ → stores/
```

**日程模块**
```
routes/items_router.py → app/calendar/router.py
创建 app/calendar/models.py (Pydantic 模型)
创建 app/calendar/service.py (业务逻辑)
```

**对话模块（新）**
```
routes/chat_router.py → app/chat/router.py
services/planner_agent.py → app/chat/planner_agent.py
创建 app/chat/models.py
创建 app/chat/service.py
```

**画像模块（新）**
```
routes/profile_router.py → app/profile/router.py
创建 app/profile/models.py
创建 app/profile/service.py
```

**推荐模块（新）**
```
routes/recommendations_router.py → app/recommendations/router.py
services/content_crawler.py → app/recommendations/crawler/
services/recommendation_engine.py → app/recommendations/service.py
services/background_tasks.py → app/recommendations/tasks.py
创建 app/recommendations/models.py
```

**数据库**
```
data/calendar_db.py → app/db/
  ├── base.py (数据库连接基础)
  ├── calendar.py (日程相关操作)
  ├── chat.py (对话相关操作)
  ├── profile.py (画像相关操作)
  └── recommendations.py (推荐相关操作)
```

**服务层**
```
services/ollama.py → services/ollama.py
services/file_handler.py → services/file_handler.py
services/report_generator.py → services/report_generator.py
```

---

## 📝 关键文件说明

### app/core/config.py
```python
# 从 config.py 移动过来，统一配置管理
import os
from typing import Optional

class Settings:
    OLLAMA_BASE_URL: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    MODEL_NAME: str = os.getenv("MODEL_NAME", "qwen3-vl:30b")
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

### app/db/base.py
```python
# 数据库连接基础
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

_DB_PATH = Path(__file__).parent.parent.parent / "data" / "calendar.db"

@contextmanager
def get_db_connection():
    conn = sqlite3.connect(str(_DB_PATH))
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()

def get_now() -> str:
    return datetime.now(timezone.utc).isoformat()
```

### app/db/calendar.py
```python
# 日程相关数据操作
from .base import get_db_connection, get_now

def get_events(user_id: str):
    """获取用户的所有事件"""
    with get_db_connection() as conn:
        # SQL 操作
        pass

def create_event(user_id: str, data: dict):
    """创建事件"""
    with get_db_connection() as conn:
        # SQL 操作
        pass
```

### app/chat/service.py
```python
# 对话业务逻辑，不包含路由代码
from .planner_agent import PlannerAgent
from app.db import chat

class ChatService:
    def __init__(self):
        self.planner = PlannerAgent()
    
    async def start_conversation(self, user_id: str, request: str):
        # 调用 planner，保存到数据库
        result = await self.planner.start_conversation(user_id, request)
        chat.save_message(user_id, ...)
        return result
```

### app/calendar/router.py
```python
# 路由只处理 HTTP 请求/响应
from fastapi import APIRouter
from .service import CalendarService
from .models import EventCreate

router = APIRouter(prefix="/items", tags=["calendar"])
service = CalendarService()

@router.post("/events")
async def create_event(body: EventCreate, session=...):
    return await service.create_event(session.user_id, body)
```

---

## 🏗️ 分层架构

```
┌─────────────────────────────────────────┐
│         API Layer (Routes)              │
│  router.py (HTTP 请求/响应处理)         │
└────────────────┬────────────────────────┘
                 │
┌────────────────▼────────────────────────┐
│      Service Layer (Business Logic)     │
│  service.py (业务逻辑，与数据库交互)    │
└────────────────┬────────────────────────┘
                 │
┌────────────────▼────────────────────────┐
│       Data Layer (Database)             │
│  app/db/ (SQL 操作)                     │
└─────────────────────────────────────────┘
```

### 路由层职责：
- 解析 HTTP 请求
- 验证请求参数
- 调用 Service 层
- 返回 HTTP 响应
- 错误处理

### Service 层职责：
- 业务逻辑处理
- 调用 Data 层
- 数据转换
- 不处理 HTTP 相关内容

### Data 层职责：
- 数据库 SQL 操作
- 数据持久化
- 查询和更新

---

## 🔑 关键改进

### 1. 模块化清晰
每个业务模块（认证、日程、对话等）都有自己的目录，包含：
- `models.py` - Pydantic 数据模型
- `router.py` - 路由定义
- `service.py` - 业务逻辑
- 可选的特定类（如 `planner_agent.py`）

### 2. 分层架构
- Route 层：只处理 HTTP
- Service 层：业务逻辑
- Data 层：数据库操作
- 易于测试和维护

### 3. 数据库组织
`app/db/` 按功能模块分文件：
- `calendar.py` - 日程操作
- `chat.py` - 对话操作
- `profile.py` - 画像操作
- `recommendations.py` - 推荐操作

### 4. 测试友好
- `tests/` 目录对应应用结构
- 每个模块都有独立的测试文件
- `conftest.py` 统一配置

### 5. 可扩展性
- 添加新功能只需创建新模块目录
- 不需要修改现有代码
- 新爬虫可以直接添加到 `app/recommendations/crawler/`

---

## 📋 迁移检查清单

- [ ] 创建新目录结构
- [ ] 移动认证模块文件
- [ ] 移动日程管理文件
- [ ] 创建日程 service 层
- [ ] 创建对话模块文件
- [ ] 创建画像模块文件
- [ ] 创建推荐模块文件
- [ ] 分离数据库操作
- [ ] 更新所有导入语句
- [ ] 更新 main.py 路由注册
- [ ] 添加单元测试
- [ ] 验证所有功能正常
- [ ] 更新 requirements.txt
- [ ] 创建 pytest.ini
- [ ] 创建 .env.example

---

## 🚀 迁移步骤

### 第 1 步：创建目录和基础文件
```bash
# 创建目录
mkdir -p app/{core,auth,calendar,chat,profile,recommendations/crawler,db}
mkdir -p shared services tests/fixtures

# 创建 __init__.py
touch app/__init__.py
touch app/core/__init__.py
# ... 等等
```

### 第 2 步：移动和重构认证模块
```bash
# 复制认证模块
cp -r auth/* app/auth/
# 编辑导入语句
```

### 第 3 步：创建数据库层
```bash
# 拆分 calendar_db.py
# 创建 app/db/base.py
# 创建 app/db/calendar.py
# 创建 app/db/chat.py
# 等等
```

### 第 4 步：创建业务层（Service）
为每个模块创建 service.py，包含业务逻辑

### 第 5 步：更新路由层
重构路由，使其只处理 HTTP，调用 service

### 第 6 步：更新 main.py
```python
from app.auth.router import router as auth_router
from app.calendar.router import router as calendar_router
from app.chat.router import router as chat_router
from app.profile.router import router as profile_router
from app.recommendations.router import router as recommendations_router

app.include_router(auth_router)
app.include_router(calendar_router)
app.include_router(chat_router)
app.include_router(profile_router)
app.include_router(recommendations_router)
```

### 第 7 步：添加测试
为每个模块创建对应的测试文件

---

## 📊 对比总结

| 方面 | 原结构 | 新结构 |
|------|--------|--------|
| 目录清晰度 | ⭐⭐ | ⭐⭐⭐⭐⭐ |
| 功能模块化 | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| 代码复用性 | ⭐⭐ | ⭐⭐⭐⭐ |
| 测试难度 | ⭐⭐⭐ | ⭐ |
| 扩展性 | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| 文件查找速度 | ⭐ | ⭐⭐⭐⭐⭐ |

---

这个新的项目结构遵循了：
- ✅ **MVC 分层模式**
- ✅ **Domain-Driven Design** 的思想
- ✅ **FastAPI 最佳实践**
- ✅ **Python 项目规范**
- ✅ **可测试性原则**
- ✅ **可维护性原则**

