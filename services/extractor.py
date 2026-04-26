import json
import logging

from services import ollama

logger = logging.getLogger(__name__)

_BASE_PROMPT = """你是日程和待办提取助手。从用户提供的内容中提取所有日程安排和待办事项。

严格按以下 JSON 格式返回，不要有任何多余的文字、解释或 markdown 代码块：
{
  "events": [
    {"title": "", "date": "YYYY-MM-DD", "time": "HH:MM", "location": "", "notes": ""}
  ],
  "todos": [
    {"title": "", "deadline": "YYYY-MM-DD", "priority": "high/medium/low", "notes": ""}
  ]
}

规则：
- 日程 = 有具体时间/日期的事件（会议、课程、活动等）
- 待办 = 需要完成的任务（可能有或没有截止日期）
- 同一件事如果既是日程又是待办，两个数组都加
- 无法确定的字段填 null，不要猜测或编造
- 日期统一转为 YYYY-MM-DD 格式，时间统一转为 HH:MM 格式（24小时制）
- priority 根据截止紧迫程度判断：今明两天 high，一周内 medium，更远 low
- 正确推算"今天/明天/后天/大后天/下周X/下下周/X天后"等相对日期"""


def _system_prompt(current_date: str | None) -> str:
    if not current_date:
        return _BASE_PROMPT
    return _BASE_PROMPT + f"\n\n当前日期：{current_date}（请基于此推算所有相对日期）"


def _parse_response(raw: str) -> dict:
    text = raw.strip()
    # Strip markdown code fences if model adds them anyway
    if text.startswith("```"):
        lines = text.splitlines()
        text = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])
    return json.loads(text)


async def extract_from_text(text: str, current_date: str | None = None) -> dict:
    messages = [
        {"role": "system", "content": _system_prompt(current_date)},
        {"role": "user", "content": text},
    ]
    return await _run_with_retry(messages)


async def extract_from_image(image_b64: str, mime: str, current_date: str | None = None) -> dict:
    messages = [
        {"role": "system", "content": _system_prompt(current_date)},
        {
            "role": "user",
            "content": "请从截图中提取日程和待办",
            "images": [image_b64],
        },
    ]
    return await _run_with_retry(messages)


async def _run_with_retry(messages: list[dict]) -> dict:
    for attempt in range(2):
        raw = await ollama.chat(messages)
        logger.info("Ollama raw response (attempt %d): %s", attempt + 1, raw[:200])
        try:
            return _parse_response(raw)
        except (json.JSONDecodeError, KeyError, ValueError) as exc:
            logger.warning("JSON parse failed (attempt %d): %s", attempt + 1, exc)
            if attempt == 1:
                raise ValueError("模型返回格式异常") from exc
    raise ValueError("模型返回格式异常")
