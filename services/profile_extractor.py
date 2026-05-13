"""Profile Extractor Service - AI自动从对话中提取用户兴趣"""

import json
import logging
from typing import List, Dict

from services import ollama
from data import calendar_db

logger = logging.getLogger(__name__)


class ProfileExtractor:
    """从对话中提取用户兴趣标签"""
    
    def __init__(self):
        self.model_name = "qwen3-vl:30b"
    
    def _build_extraction_prompt(self) -> str:
        return """你是一个用户画像分析专家。你的任务是从用户的对话中提取用户的兴趣标签。

你需要分析用户的对话内容，识别出用户感兴趣的主题、技术、项目或研究领域。

输出格式必须是严格的JSON，不要有任何多余的文字：
{
  "interests": [
    {
      "category": "research" | "project" | "skill",
      "tag": "标签名称",
      "keywords": ["关键词1", "关键词2"],
      "confidence": 0.8
    }
  ]
}

分类说明：
- research: 研究领域（如机器学习、计算机视觉、自然语言处理等）
- project: 项目类型（如Web开发、移动应用、数据分析等）
- skill: 技术技能（如Python、PyTorch、Docker等）

提取规则：
1. 只提取用户明确表达的兴趣，不要推测
2. confidence表示置信度（0-1），只有>=0.6的才提取
3. keywords应该包含相关的搜索关键词
4. 每个兴趣标签应该具体明确，不要太宽泛"""

    async def extract_from_conversation(
        self,
        conversation_history: List[Dict]
    ) -> Dict:
        """从对话历史中提取用户兴趣
        
        Args:
            conversation_history: 对话历史，包含role和content
            
        Returns:
            提取的兴趣标签列表
        """
        if not conversation_history:
            return {"interests": []}
        
        conversation_text = "\n".join([
            f"{msg['role']}: {msg['content']}"
            for msg in conversation_history
        ])
        
        messages = [
            {
                "role": "system",
                "content": self._build_extraction_prompt()
            },
            {
                "role": "user",
                "content": f"请从以下对话中提取用户的兴趣标签：\n\n{conversation_text}"
            }
        ]
        
        try:
            raw_response = await ollama.chat(messages)
            logger.info(f"兴趣提取原始回复：{raw_response[:300]}")
            
            text = raw_response.strip()
            if text.startswith("```"):
                lines = text.splitlines()
                text = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])
            
            result = json.loads(text)
            
            interests = result.get("interests", [])
            valid_interests = [
                i for i in interests
                if i.get("confidence", 0) >= 0.6
            ]
            
            return {"interests": valid_interests}
            
        except (json.JSONDecodeError, ValueError) as e:
            logger.error(f"兴趣提取失败：{e}")
            return {"interests": []}
    
    async def save_extracted_interests(
        self,
        user_id: str,
        extracted_interests: List[Dict]
    ) -> List[Dict]:
        """保存提取的兴趣标签到数据库
        
        Args:
            user_id: 用户ID
            extracted_interests: 提取的兴趣列表
            
        Returns:
            保存成功的兴趣列表
        """
        saved = []
        
        for interest in extracted_interests:
            try:
                result = calendar_db.create_or_update_interest(
                    user_id=user_id,
                    category=interest["category"],
                    tag=interest["tag"],
                    keywords=interest.get("keywords", []),
                    weight=interest.get("confidence", 0.7)
                )
                if result:
                    saved.append(result)
                    logger.info(f"保存兴趣标签：{interest['tag']}")
            except Exception as e:
                logger.error(f"保存兴趣失败：{e}")
        
        return saved
    
    async def extract_interests_from_all_chat_sessions(
        self,
        date: str | None = None
    ) -> Dict:
        """从所有用户的聊天会话中批量提取兴趣（每天凌晨执行）
        
        Args:
            date: 日期（YYYY-MM-DD），默认为今天
            
        Returns:
            提取统计
        """
        from datetime import datetime
        
        if not date:
            date = datetime.now().strftime("%Y-%m-%d")
        
        logger.info(f"开始批量提取用户兴趣（日期：{date}）")
        
        stats = {
            "date": date,
            "total_users": 0,
            "users_processed": 0,
            "interests_extracted": 0,
            "errors": 0
        }
        
        try:
            all_interests = calendar_db.get_user_interests("")
            user_ids = set(i["user_id"] for i in all_interests)
            
            if not user_ids:
                logger.info("没有找到任何用户")
                return stats
            
            stats["total_users"] = len(user_ids)
            
            for user_id in user_ids:
                try:
                    sessions = self._get_user_chat_sessions(user_id, date)
                    
                    if not sessions:
                        continue
                    
                    all_conversations = []
                    for session_id in sessions:
                        history = calendar_db.get_chat_history(user_id, session_id)
                        if history:
                            all_conversations.extend(history)
                    
                    if not all_conversations:
                        continue
                    
                    extracted = await self.extract_from_conversation(all_conversations)
                    
                    if extracted.get("interests"):
                        saved = await self.save_extracted_interests(
                            user_id,
                            extracted["interests"]
                        )
                        stats["interests_extracted"] += len(saved)
                    
                    stats["users_processed"] += 1
                    logger.info(f"用户 {user_id}: 提取了 {len(extracted.get('interests', []))} 个兴趣")
                    
                except Exception as e:
                    logger.error(f"处理用户 {user_id} 失败：{e}")
                    stats["errors"] += 1
            
            logger.info(f"批量提取完成：{stats}")
            return stats
            
        except Exception as e:
            logger.error(f"批量提取失败：{e}")
            return stats
    
    def _get_user_chat_sessions(self, user_id: str, date: str) -> List[str]:
        """获取用户在指定日期的所有聊天会话
        
        Args:
            user_id: 用户ID
            date: 日期（YYYY-MM-DD）
            
        Returns:
            会话ID列表
        """
        import sqlite3
        from pathlib import Path
        
        db_path = Path(__file__).parent.parent / "data" / "calendar.db"
        
        try:
            conn = sqlite3.connect(str(db_path))
            cursor = conn.cursor()
            
            cursor.execute(
                """SELECT DISTINCT session_id FROM chat_messages 
                   WHERE user_id=? AND date(created_at)=?
                   ORDER BY created_at""",
                (user_id, date)
            )
            
            sessions = [row[0] for row in cursor.fetchall()]
            conn.close()
            
            return sessions
            
        except Exception as e:
            logger.error(f"获取用户会话失败：{e}")
            return []


profile_extractor = ProfileExtractor()
