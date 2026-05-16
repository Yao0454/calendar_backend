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
        self.model_name = "qwen3-vl:30b"

    def _get_user_schedule_context(self, user_id: str, days: int = 14) -> str:
        events = calendar_db.get_events(user_id)
        todos = calendar_db.get_todos(user_id)

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

重要交互规则（必须遵守）：
- 只用自然语言与用户对话，清晰描述规划方案。
- 绝对不要在聊天消息中输出 JSON 格式数据。
- 绝对不要让用户回复任何特定文字（如"接受规划"）来确认。
- 用户会通过 App 界面上的「生成草稿」按钮来生成结构化数据并导入日历，无需任何文字回复。
- 当你认为规划方案已经完整时，直接告诉用户：「方案已完整，您可以点击下方的生成草稿按钮导入日历。」"""

    async def start_conversation(self, user_id: str, user_request: str) -> dict:
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
        messages = [
            {
                "role": "system",
                "content": self._build_system_prompt()
            }
        ]
        
        for msg in conversation_history:
            messages.append({
                "role": msg["role"],
                "content": msg["content"]
            })
        
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

        raw_response = await ollama.chat(messages)
        logger.info(f"规划生成原始回复：{raw_response[:300]}")

        try:
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

        for msg in conversation_history:
            messages.append({
                "role": msg["role"],
                "content": msg["content"]
            })

        messages.append({
            "role": "user",
            "content": refinement_request
        })

        ai_response = await ollama.chat(messages)
        return ai_response


planner = PlannerAgent()
