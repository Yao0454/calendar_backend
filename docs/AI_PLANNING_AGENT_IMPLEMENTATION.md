# AI 日程规划助手实现文档

## 概述

本文档详细说明如何实现一个集成到日历应用中的 AI 规划助手。用户可以通过自然语言对话与 AI 进行互动，获得基于现有日程的个性化规划方案。

---

## 架构概览

```
┌─────────────────────────────────────────────────────┐
│           FastAPI 后端主应用 (main.py)              │
├─────────────────────────────────────────────────────┤
│  Chat Router (routes/chat_router.py)                │
│  ├─ POST /chat/start      → 开始新对话              │
│  ├─ POST /chat/message    → 发送消息                │
│  ├─ GET  /chat/history    → 获取对话历史            │
│  ├─ GET  /chat/drafts     → 查看规划草稿            │
│  └─ POST /chat/confirm    → 确认并导入规划          │
├─────────────────────────────────────────────────────┤
│  Planner Agent Service (services/planner_agent.py)  │
│  ├─ read_user_schedule()  → 读取用户当前日程        │
│  ├─ parse_user_request()  → 解析用户需求            │
│  ├─ generate_plan()       → 生成规划方案            │
│  └─ create_draft()        → 创建草稿                │
├─────────────────────────────────────────────────────┤
│  Database (data/calendar_db.py)                     │
│  ├─ chat_messages 表      → 保存对话记录            │
│  ├─ planning_drafts 表    → 保存规划草稿            │
│  ├─ events 表             → 日程事件                │
│  └─ todos 表              → 待办事项                │
└─────────────────────────────────────────────────────┘
```

---

## 1. 数据库扩展

### 1.1 新增表结构

在 `data/calendar_db.py` 的 `init_db()` 函数中的 SQL 脚本末尾添加：

```sql
-- 对话消息表
CREATE TABLE IF NOT EXISTS chat_messages (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id         TEXT    NOT NULL,
    session_id      TEXT    NOT NULL,        -- 对话会话唯一 ID
    role            TEXT    NOT NULL,        -- "user" 或 "assistant"
    content         TEXT    NOT NULL,        -- 消息内容
    created_at      TEXT    NOT NULL         -- ISO 8601 时间戳
);

-- 规划草稿表
CREATE TABLE IF NOT EXISTS planning_drafts (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id         TEXT    NOT NULL,
    title           TEXT,                    -- 规划标题（可选）
    description     TEXT,                    -- 规划描述
    proposed_events TEXT    NOT NULL,        -- JSON 数组：提议的日程事件
    proposed_todos  TEXT    NOT NULL,        -- JSON 数组：提议的待办事项
    status          TEXT    NOT NULL DEFAULT 'draft',  -- draft/confirmed/rejected
    created_at      TEXT    NOT NULL,
    updated_at      TEXT    NOT NULL
);

-- 索引优化
CREATE INDEX IF NOT EXISTS idx_chat_user_session ON chat_messages(user_id, session_id);
CREATE INDEX IF NOT EXISTS idx_planning_user ON planning_drafts(user_id);
```

### 1.2 数据库操作函数

在 `data/calendar_db.py` 末尾添加以下函数：

```python
# ─────────────────────────────────────────────────────────────────────────────
# Chat Messages
# ─────────────────────────────────────────────────────────────────────────────

def save_chat_message(user_id: str, session_id: str, role: str, content: str) -> dict:
    """保存单条聊天消息。"""
    with _conn() as c:
        c.execute(
            """INSERT INTO chat_messages (user_id, session_id, role, content, created_at)
               VALUES (?, ?, ?, ?, ?)""",
            (user_id, session_id, role, content, _now())
        )
        msg_id = c.lastrowid
    return {
        "id": msg_id,
        "user_id": user_id,
        "session_id": session_id,
        "role": role,
        "content": content,
        "created_at": _now()
    }


def get_chat_history(user_id: str, session_id: str, limit: int = 50) -> list:
    """获取对话历史。"""
    with _conn() as c:
        c.row_factory = sqlite3.Row
        rows = c.execute(
            """SELECT id, user_id, session_id, role, content, created_at
               FROM chat_messages
               WHERE user_id=? AND session_id=?
               ORDER BY created_at ASC
               LIMIT ?""",
            (user_id, session_id, limit)
        ).fetchall()
    return [dict(row) for row in rows]


def clear_chat_session(user_id: str, session_id: str) -> None:
    """清空对话会话中的所有消息。"""
    with _conn() as c:
        c.execute(
            "DELETE FROM chat_messages WHERE user_id=? AND session_id=?",
            (user_id, session_id)
        )


# ─────────────────────────────────────────────────────────────────────────────
# Planning Drafts
# ─────────────────────────────────────────────────────────────────────────────

def create_planning_draft(
    user_id: str,
    title: str | None,
    description: str | None,
    proposed_events: list,
    proposed_todos: list
) -> dict:
    """创建新的规划草稿。"""
    now = _now()
    with _conn() as c:
        c.execute(
            """INSERT INTO planning_drafts
               (user_id, title, description, proposed_events, proposed_todos, status, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, 'draft', ?, ?)""",
            (
                user_id,
                title,
                description,
                json.dumps(proposed_events),
                json.dumps(proposed_todos),
                now,
                now
            )
        )
        draft_id = c.lastrowid
    return get_planning_draft(draft_id, user_id)


def get_planning_draft(draft_id: int, user_id: str) -> dict | None:
    """获取单个规划草稿。"""
    with _conn() as c:
        c.row_factory = sqlite3.Row
        row = c.execute(
            "SELECT * FROM planning_drafts WHERE id=? AND user_id=?",
            (draft_id, user_id)
        ).fetchone()
    if not row:
        return None
    result = dict(row)
    result["proposed_events"] = json.loads(result["proposed_events"])
    result["proposed_todos"] = json.loads(result["proposed_todos"])
    return result


def get_planning_drafts(user_id: str, status: str | None = None) -> list:
    """获取用户的所有规划草稿，可按状态筛选。"""
    with _conn() as c:
        c.row_factory = sqlite3.Row
        if status:
            rows = c.execute(
                """SELECT * FROM planning_drafts WHERE user_id=? AND status=?
                   ORDER BY updated_at DESC""",
                (user_id, status)
            ).fetchall()
        else:
            rows = c.execute(
                """SELECT * FROM planning_drafts WHERE user_id=?
                   ORDER BY updated_at DESC""",
                (user_id,)
            ).fetchall()
    result = []
    for row in rows:
        d = dict(row)
        d["proposed_events"] = json.loads(d["proposed_events"])
        d["proposed_todos"] = json.loads(d["proposed_todos"])
        result.append(d)
    return result


def confirm_planning_draft(draft_id: int, user_id: str) -> dict | None:
    """确认草稿并将事件和待办导入主表。"""
    draft = get_planning_draft(draft_id, user_id)
    if not draft or draft["status"] != "draft":
        return None

    # 保存事件和待办
    saved_events = bulk_insert_events(user_id, draft["proposed_events"])
    saved_todos = bulk_insert_todos(user_id, draft["proposed_todos"])

    # 更新草稿状态
    with _conn() as c:
        c.execute(
            "UPDATE planning_drafts SET status='confirmed', updated_at=? WHERE id=?",
            (_now(), draft_id)
        )

    return {
        "draft_id": draft_id,
        "events": saved_events,
        "todos": saved_todos
    }


def reject_planning_draft(draft_id: int, user_id: str) -> bool:
    """拒绝规划草稿（标记为已拒绝）。"""
    with _conn() as c:
        c.execute(
            """UPDATE planning_drafts SET status='rejected', updated_at=? 
               WHERE id=? AND user_id=?""",
            (_now(), draft_id, user_id)
        )
    return True
```

---

## 2. 规划助手服务

创建文件 `services/planner_agent.py`：

```python
"""AI Planning Agent Service - 与 Ollama 交互生成规划方案"""

import json
import logging
from datetime import datetime, timedelta
from typing import Optional

from data import calendar_db
from services import ollama

logger = logging.getLogger(__name__)


class PlannerAgent:
    """日程规划 AI Agent"""

    def __init__(self):
        self.model_name = "qwen3-vl:30b"  # 或从 config.py 读取

    def _get_user_schedule_context(self, user_id: str, days: int = 14) -> str:
        """读取用户现有日程，生成上下文信息"""
        events = calendar_db.get_events(user_id)
        todos = calendar_db.get_todos(user_id)

        # 按日期组织事件
        today = datetime.now().date()
        schedule_text = f"当前日期：{today}\n\n【现有日程】\n"

        if events:
            schedule_text += "【日程事件】\n"
            for e in sorted(events, key=lambda x: x.get('date', '') or '9999-12-31'):
                date = e.get('date', '无日期')
                time = e.get('time', '')
                title = e.get('title', '')
                location = e.get('location', '')
                time_str = f" {time}" if time else ""
                loc_str = f"（{location}）" if location else ""
                schedule_text += f"  • {date}{time_str}: {title}{loc_str}\n"

        if todos:
            schedule_text += "\n【待办事项】\n"
            for t in todos:
                if not t.get('is_done', False):
                    deadline = t.get('deadline', '无截止')
                    title = t.get('title', '')
                    priority = t.get('priority', 'medium')
                    schedule_text += f"  • [{priority}] {title} (截止: {deadline})\n"

        return schedule_text

    def _build_system_prompt(self) -> str:
        """构建系统 prompt"""
        return """你是一位高效的日程规划助手。你的职责是：

1. 理解用户的需求（学习新技能、完成项目、参加活动等）
2. 查看用户现有的日程安排
3. 提出合理的规划建议，包括：
   - 需要安排哪些事件（Events）
   - 需要创建哪些待办任务（Todos）
   - 具体的时间和优先级
   - 理由解释

规划原则：
- 避免与现有日程冲突
- 充分利用用户的空闲时间
- 为重要任务预留足够的时间
- 合理分配任务的优先级
- 为长期项目设置多个里程碑

当用户接受你的规划后，你需要生成可以直接导入的 JSON 格式的事件和待办。"""

    async def start_conversation(self, user_id: str, user_request: str) -> dict:
        """开始对话并生成初始规划方案"""
        # 获取用户当前日程
        schedule_context = self._get_user_schedule_context(user_id)

        messages = [
            {
                "role": "system",
                "content": self._build_system_prompt()
            },
            {
                "role": "user",
                "content": f"""{schedule_context}

用户请求：{user_request}

请根据用户的需求和现有日程，提出详细的规划方案。
首先分析用户的需求，然后给出具体的建议。"""
            }
        ]

        # 调用 Ollama
        ai_response = await ollama.chat(messages)
        logger.info(f"AI规划回复：{ai_response[:500]}")

        return {
            "ai_response": ai_response,
            "schedule_context": schedule_context
        }

    async def generate_plan_from_response(
        self, 
        user_id: str, 
        user_request: str,
        ai_response: str,
        conversation_history: list
    ) -> dict:
        """从 AI 回复中生成可执行的规划方案"""
        
        # 构建包含历史的完整对话
        messages = [
            {
                "role": "system",
                "content": self._build_system_prompt()
            }
        ]
        
        # 添加历史对话
        for msg in conversation_history:
            messages.append({
                "role": msg["role"],
                "content": msg["content"]
            })
        
        # 新的用户确认请求
        confirmation_prompt = f"""用户已确认需要这个规划方案。

请生成可以直接导入到日历的 JSON 格式的事件和待办列表。

严格按以下 JSON 格式返回，不要有任何多余的文字、解释或 markdown 代码块：
{{
  "events": [
    {{"title": "事件标题", "date": "YYYY-MM-DD", "time": "HH:MM", "location": "地点", "notes": "备注"}},
    ...
  ],
  "todos": [
    {{"title": "待办标题", "deadline": "YYYY-MM-DD", "priority": "high/medium/low", "notes": "备注"}},
    ...
  ]
}}

规则：
- 所有日期格式为 YYYY-MM-DD，时间格式为 HH:MM（24小时制）
- location 和 notes 可以为 null
- priority 为 high/medium/low
- 不要添加实际不存在的日程冲突"""
        
        messages.append({
            "role": "user",
            "content": confirmation_prompt
        })

        # 调用 Ollama 生成结构化数据
        raw_response = await ollama.chat(messages)
        logger.info(f"规划生成原始回复：{raw_response[:300]}")

        try:
            # 尝试解析 JSON
            text = raw_response.strip()
            if text.startswith("```"):
                lines = text.splitlines()
                text = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])
            plan_data = json.loads(text)
            
            return {
                "success": True,
                "plan": plan_data,
                "raw_response": raw_response
            }
        except (json.JSONDecodeError, ValueError) as e:
            logger.error(f"规划生成失败：{e}")
            return {
                "success": False,
                "error": "无法解析规划方案",
                "raw_response": raw_response
            }

    async def refine_plan(
        self,
        user_id: str,
        conversation_history: list,
        refinement_request: str
    ) -> str:
        """基于用户反馈改进规划方案"""
        schedule_context = self._get_user_schedule_context(user_id)

        messages = [
            {
                "role": "system",
                "content": self._build_system_prompt()
            },
            {
                "role": "user",
                "content": schedule_context
            }
        ]

        # 添加对话历史
        for msg in conversation_history:
            messages.append({
                "role": msg["role"],
                "content": msg["content"]
            })

        # 用户的改进建议
        messages.append({
            "role": "user",
            "content": refinement_request
        })

        ai_response = await ollama.chat(messages)
        return ai_response


# 全局实例
planner = PlannerAgent()
```

---

## 3. 路由实现

创建文件 `routes/chat_router.py`：

```python
"""Chat & Planning routes"""

import uuid
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from auth.deps import get_current_session
from auth.models import SessionPrincipal
from data import calendar_db
from services.planner_agent import planner
from services.ollama import OllamaUnavailableError, OllamaTimeoutError, OllamaModelNotFoundError

router = APIRouter(prefix="/chat", tags=["chat"])


# ── Schemas ───────────────────────────────────────────────────────────────────

class StartChatRequest(BaseModel):
    """开始对话请求"""
    user_request: str  # 用户的规划需求描述


class SendMessageRequest(BaseModel):
    """发送聊天消息"""
    session_id: str
    message: str


class ConfirmPlanRequest(BaseModel):
    """确认规划方案"""
    draft_id: int
    confirm: bool = True  # True 导入，False 拒绝


class ChatMessage(BaseModel):
    """聊天消息"""
    id: int
    role: str
    content: str
    created_at: str


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post("/start", status_code=201)
async def start_chat(
    req: StartChatRequest,
    session: SessionPrincipal = Depends(get_current_session)
):
    """开始新的规划对话"""
    try:
        session_id = str(uuid.uuid4())
        
        # 获取 AI 的初始规划响应
        result = await planner.start_conversation(session.user_id, req.user_request)
        
        # 保存用户消息
        calendar_db.save_chat_message(
            session.user_id,
            session_id,
            "user",
            req.user_request
        )
        
        # 保存 AI 响应
        calendar_db.save_chat_message(
            session.user_id,
            session_id,
            "assistant",
            result["ai_response"]
        )
        
        return {
            "session_id": session_id,
            "ai_response": result["ai_response"],
            "schedule_context": result["schedule_context"]
        }
    
    except OllamaUnavailableError:
        raise HTTPException(status_code=503, detail="Ollama 服务不可达")
    except OllamaModelNotFoundError as e:
        raise HTTPException(status_code=503, detail=f"模型 {e.model} 未找到")
    except OllamaTimeoutError:
        raise HTTPException(status_code=504, detail="Ollama 推理超时")


@router.post("/message")
async def send_message(
    req: SendMessageRequest,
    session: SessionPrincipal = Depends(get_current_session)
):
    """在对话中发送消息并获得回复"""
    try:
        # 保存用户消息
        calendar_db.save_chat_message(
            session.user_id,
            req.session_id,
            "user",
            req.message
        )
        
        # 获取对话历史
        history = calendar_db.get_chat_history(session.user_id, req.session_id)
        
        # 构建消息列表
        messages = [
            {
                "role": "system",
                "content": planner._build_system_prompt()
            }
        ]
        
        # 添加历史记录
        for msg in history:
            messages.append({
                "role": msg["role"],
                "content": msg["content"]
            })
        
        # 调用 Ollama
        ai_response = await planner.planner.chat(messages) if hasattr(planner, 'chat') else ""
        from services import ollama
        ai_response = await ollama.chat(messages)
        
        # 保存 AI 回复
        calendar_db.save_chat_message(
            session.user_id,
            req.session_id,
            "assistant",
            ai_response
        )
        
        return {
            "message": req.message,
            "ai_response": ai_response
        }
    
    except OllamaUnavailableError:
        raise HTTPException(status_code=503, detail="Ollama 服务不可达")
    except OllamaTimeoutError:
        raise HTTPException(status_code=504, detail="Ollama 推理超时")


@router.get("/history/{session_id}")
async def get_chat_history(
    session_id: str,
    session: SessionPrincipal = Depends(get_current_session)
):
    """获取对话历史"""
    history = calendar_db.get_chat_history(session.user_id, session_id)
    return {"messages": history}


@router.post("/draft")
async def create_draft(
    req: SendMessageRequest,
    session: SessionPrincipal = Depends(get_current_session)
):
    """从当前对话生成规划草稿"""
    try:
        # 获取对话历史
        history = calendar_db.get_chat_history(session.user_id, req.session_id)
        
        # 生成规划方案
        plan_result = await planner.generate_plan_from_response(
            session.user_id,
            history[0]["content"] if history else "",
            history[-1]["content"] if history else "",
            history
        )
        
        if not plan_result["success"]:
            raise HTTPException(status_code=400, detail=plan_result["error"])
        
        plan = plan_result["plan"]
        
        # 创建草稿
        draft = calendar_db.create_planning_draft(
            session.user_id,
            title="AI规划方案",
            description=f"基于对话的规划方案",
            proposed_events=plan.get("events", []),
            proposed_todos=plan.get("todos", [])
        )
        
        return {
            "draft_id": draft["id"],
            "draft": draft
        }
    
    except OllamaUnavailableError:
        raise HTTPException(status_code=503, detail="Ollama 服务不可达")
    except OllamaTimeoutError:
        raise HTTPException(status_code=504, detail="Ollama 推理超时")


@router.get("/drafts")
async def get_drafts(
    status: str | None = None,
    session: SessionPrincipal = Depends(get_current_session)
):
    """获取用户的规划草稿"""
    drafts = calendar_db.get_planning_drafts(session.user_id, status)
    return {"drafts": drafts}


@router.get("/drafts/{draft_id}")
async def get_draft_detail(
    draft_id: int,
    session: SessionPrincipal = Depends(get_current_session)
):
    """获取单个规划草稿详情"""
    draft = calendar_db.get_planning_draft(draft_id, session.user_id)
    if not draft:
        raise HTTPException(status_code=404, detail="Draft not found")
    return {"draft": draft}


@router.post("/confirm/{draft_id}")
async def confirm_draft(
    draft_id: int,
    req: ConfirmPlanRequest,
    session: SessionPrincipal = Depends(get_current_session)
):
    """确认或拒绝规划草稿"""
    if req.confirm:
        # 确认草稿并导入日程
        result = calendar_db.confirm_planning_draft(draft_id, session.user_id)
        if not result:
            raise HTTPException(status_code=404, detail="Draft not found or already processed")
        return {
            "status": "confirmed",
            "events_imported": len(result["events"]),
            "todos_imported": len(result["todos"]),
            "data": result
        }
    else:
        # 拒绝草稿
        success = calendar_db.reject_planning_draft(draft_id, session.user_id)
        return {
            "status": "rejected",
            "success": success
        }


@router.delete("/session/{session_id}")
async def clear_session(
    session_id: str,
    session: SessionPrincipal = Depends(get_current_session)
):
    """清空对话会话"""
    calendar_db.clear_chat_session(session.user_id, session_id)
    return {"status": "cleared"}
```

---

## 4. 集成到主应用

在 `main.py` 中添加：

```python
from routes import chat_router  # 在其他 import 后添加

# 在 app.include_router 部分添加：
app.include_router(auth_router.router)
app.include_router(items_router.router)
app.include_router(chat_router.router)  # ← 新增
```

---

## 5. 工作流程示例

### 用户交互流程

```
┌─────────────────────────────────────────────────────┐
│ 1. 用户发起规划请求                                  │
│    POST /chat/start                                 │
│    {"user_request": "我想学习 PyTorch，需要花4周"}  │
└────────────────┬────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────┐
│ 2. AI 分析用户日程和需求                            │
│    - 读取现有日程                                   │
│    - 找出空闲时间槽                                 │
│    - 生成详细规划方案                               │
└────────────────┬────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────┐
│ 3. 返回规划建议给用户                                │
│    Response: {ai_response, schedule_context}        │
└────────────────┬────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────┐
│ 4. 用户可以继续对话或要求调整                        │
│    POST /chat/message                               │
│    {"message": "能不能改成每天2小时而不是3小时？"}  │
└────────────────┬────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────┐
│ 5. AI 生成改进的规划方案                             │
│    - 根据新的约束条件调整时间分配                    │
│    - 重新计算工作量和截止日期                       │
└────────────────┬────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────┐
│ 6. 创建规划草稿                                      │
│    POST /chat/draft                                 │
│    - 生成结构化的 Events 和 Todos                   │
│    - 保存为草稿供用户审核                            │
└────────────────┬────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────┐
│ 7. 用户确认规划                                      │
│    POST /chat/confirm/{draft_id}                    │
│    - 导入所有事件到日程表                            │
│    - 导入所有待办到待办列表                          │
│    - 更新草稿状态为 "confirmed"                     │
└──────────────────────────────────────────────────────┘
```

---

## 6. API 端点参考

### 开始对话
```
POST /chat/start
请求：
{
  "user_request": "我想在下周内完成数据分析项目的代码审查"
}

响应：
{
  "session_id": "uuid-string",
  "ai_response": "根据你的日程，我建议...",
  "schedule_context": "当前日期：2026-04-26\n【现有日程】..."
}
```

### 发送消息
```
POST /chat/message
请求：
{
  "session_id": "uuid-string",
  "message": "能否将这个任务分成3部分来做？"
}

响应：
{
  "message": "...",
  "ai_response": "当然可以，我建议..."
}
```

### 获取对话历史
```
GET /chat/history/{session_id}

响应：
{
  "messages": [
    {
      "id": 1,
      "role": "user",
      "content": "我想学习 PyTorch",
      "created_at": "2026-04-26T10:30:00+00:00"
    },
    {
      "id": 2,
      "role": "assistant",
      "content": "基于你的日程...",
      "created_at": "2026-04-26T10:30:05+00:00"
    }
  ]
}
```

### 创建规划草稿
```
POST /chat/draft
请求：
{
  "session_id": "uuid-string",
  "message": "我觉得这个方案可以，请生成日程"
}

响应：
{
  "draft_id": 42,
  "draft": {
    "id": 42,
    "user_id": "user123",
    "title": "AI规划方案",
    "description": "基于对话的规划方案",
    "proposed_events": [
      {
        "title": "PyTorch 学习 - 基础",
        "date": "2026-04-28",
        "time": "19:00",
        "location": null,
        "notes": "安装和基本概念"
      }
    ],
    "proposed_todos": [
      {
        "title": "完成 PyTorch 官方教程",
        "deadline": "2026-05-26",
        "priority": "high",
        "notes": "Week 1-2"
      }
    ],
    "status": "draft",
    "created_at": "2026-04-26T10:35:00+00:00"
  }
}
```

### 获取所有草稿
```
GET /chat/drafts?status=draft

响应：
{
  "drafts": [
    { /* draft object */ }
  ]
}
```

### 确认草稿
```
POST /chat/confirm/42
请求：
{
  "draft_id": 42,
  "confirm": true
}

响应：
{
  "status": "confirmed",
  "events_imported": 8,
  "todos_imported": 4,
  "data": {
    "events": [ /* 导入的事件 */ ],
    "todos": [ /* 导入的待办 */ ]
  }
}
```

---

## 7. 关键实现细节

### 7.1 日程冲突检测

在 `services/planner_agent.py` 中实现：

```python
def _check_schedule_conflicts(self, user_id: str, proposed_event: dict) -> list:
    """检测新事件是否与现有事件冲突"""
    events = calendar_db.get_events(user_id)
    conflicts = []
    
    event_date = proposed_event.get('date')
    event_time = proposed_event.get('time')
    event_duration = proposed_event.get('duration_hours', 1)
    
    if not event_date or not event_time:
        return []
    
    try:
        start = datetime.fromisoformat(f"{event_date}T{event_time}")
        end = start + timedelta(hours=event_duration)
    except ValueError:
        return []
    
    for e in events:
        if e.get('date') != event_date:
            continue
        
        e_time = e.get('time')
        if not e_time:
            continue
        
        try:
            e_start = datetime.fromisoformat(f"{e['date']}T{e_time}")
            e_end = e_start + timedelta(hours=1)
            
            # 检查时间范围是否重叠
            if start < e_end and end > e_start:
                conflicts.append(e)
        except ValueError:
            continue
    
    return conflicts
```

### 7.2 空闲时间分析

```python
def _find_free_slots(self, user_id: str, date: str) -> list:
    """找出指定日期的空闲时间槽"""
    events = [e for e in calendar_db.get_events(user_id) if e.get('date') == date]
    
    # 按时间排序
    events = sorted(events, key=lambda x: x.get('time', '00:00'))
    
    busy_slots = []
    for e in events:
        time = e.get('time', '00:00')
        duration = 1  # 默认1小时
        busy_slots.append({
            'start': time,
            'duration': duration
        })
    
    # 计算空闲时间（假设工作时间 9:00-22:00）
    free_slots = []
    current = 9 * 60  # 9:00 AM in minutes
    end = 22 * 60     # 10:00 PM in minutes
    
    for slot in busy_slots:
        start_min = int(slot['start'].split(':')[0]) * 60 + int(slot['start'].split(':')[1])
        duration_min = slot['duration'] * 60
        
        if current < start_min:
            free_slots.append({
                'start': f"{current//60:02d}:{current%60:02d}",
                'duration_hours': (start_min - current) / 60
            })
        current = start_min + duration_min
    
    if current < end:
        free_slots.append({
            'start': f"{current//60:02d}:{current%60:02d}",
            'duration_hours': (end - current) / 60
        })
    
    return free_slots
```

---

## 8. 测试场景

### 场景 1：简单的学习规划
```
用户：我想在2周内学完 Python 数据分析基础
AI：根据你的日程，我建议：
  - 周1-2 每周 3 次 2 小时的学习课程
  - 周末安排练习项目
  - 建议这 3 个时间段：[周一19:00-21:00, 周三19:00-21:00, 周六14:00-16:00]
```

### 场景 2：迭代调整
```
用户：这个时间太多了，能否减少到每周4小时？
AI：当然可以，我调整为：
  - 周1-2 每周 2 次 2 小时
  - 周一和周五晚上 7-9 点
```

### 场景 3：多任务规划
```
用户：我需要同时完成两个项目：A项目（2周）和 B项目（3周）
AI：我为你规划了交错的时间表，避免冲突...
```

---

## 9. 错误处理

关键的错误情况：

| 错误 | HTTP Code | 处理 |
|------|-----------|------|
| Ollama 服务不可达 | 503 | 提示用户启动 Ollama |
| 模型未找到 | 503 | 提示用户拉取模型 |
| 超时 | 504 | 建议重试或增加超时时间 |
| 无效的会话 ID | 404 | 提示用户重新开始对话 |
| JSON 解析失败 | 400 | 重新请求 AI 生成方案 |

---

## 10. 下一步扩展

### 10.1 用户画像管理（模块二）
- 用户兴趣标签管理
- 基于画像的规划优化

### 10.2 智能推荐（模块三）
- arXiv 论文推荐
- GitHub 项目推荐
- Twitter 内容推荐

### 10.3 高级功能
- 多模式规划（学习、工作、娱乐）
- 长期目标分解
- 自适应时间估算
- 规划方案历史版本管理

---

## 总结

这个 AI 规划助手的核心是：
1. **读取日程** → 理解用户的时间约束
2. **对话交互** → 获取用户需求的细节
3. **智能规划** → 生成符合约束的方案
4. **草稿确认** → 用户批准后导入
5. **持久化** → 所有对话和方案都被保存

通过这个系统，用户不仅可以被动地导入日程，还能主动规划未来的时间分配。
