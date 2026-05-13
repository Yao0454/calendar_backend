import logging
import json
from services import ollama
from data import calendar_db

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = """你是一个专业的学术日报编辑。你的任务是根据提供的论文信息生成一份清晰、简洁、信息量大的学术日报。

要求：
1. 用中文生成日报
2. 每篇论文用一个段落总结，包括：
   - 论文标题和作者
   - 核心创新点（用一句话）
   - 实验结果或主要贡献
3. 使用 Markdown 格式
4. 最后添加"今日论文推荐指数"部分，评价今天论文的质量
5. 不要有多余的解释或前言，直接开始日报内容
"""

async def generate_report(user_od: str, papers: list[dict], report_date: str):
    logger.info("Generating report...")
    papers_info = []
    for paper in papers:
        info = {
            "标题": paper["title"],
            "作者": paper["authors"],
            "摘要": paper["abstract"],            
        }
        papers_info.append(info)
    