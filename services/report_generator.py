"""Daily Report Generator - 基于推荐系统生成日报"""

import logging
import json
from datetime import datetime
from typing import List, Dict

from data import calendar_db
from services import ollama

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
5. 不要有多余的解释或前言，直接开始日报内容"""


async def generate_daily_report_from_recommendations(
    user_id: str,
    report_date: str | None = None
) -> Dict:
    """基于推荐系统生成日报
    
    Args:
        user_id: 用户ID
        report_date: 日报日期（YYYY-MM-DD），默认为今天
        
    Returns:
        生成的日报信息
    """
    if not report_date:
        report_date = datetime.now().strftime("%Y-%m-%d")
    
    preference = calendar_db.get_arxiv_preference(user_id)
    if not preference:
        preference = {
            "paper_count": 5,
            "is_enabled": 1
        }
    
    recommendations = calendar_db.get_user_recommendations(user_id, unread_only=True)
    
    arxiv_papers = [
        r for r in recommendations
        if r.get("source") == "arxiv"
    ]
    
    paper_count = preference.get("paper_count", 5)
    top_papers = arxiv_papers[:paper_count]
    
    if not top_papers:
        logger.warning(f"用户 {user_id} 没有可用的arXiv推荐")
        return {
            "status": "skipped",
            "reason": "没有可用的arXiv推荐"
        }
    
    summary = await generate_report_summary(top_papers, report_date)
    
    paper_ids = [p.get("content_id") or p.get("id") for p in top_papers]
    
    html_content = _markdown_to_html(summary)
    
    report = calendar_db.create_daily_report(user_id, {
        "report_date": report_date,
        "summary": summary,
        "paper_ids": paper_ids,
        "html_content": html_content,
        "pdf_filename": None
    })
    
    logger.info(f"为用户 {user_id} 生成了日报，包含 {len(top_papers)} 篇论文")
    
    return {
        "status": "success",
        "report": report,
        "paper_count": len(top_papers)
    }


async def generate_report_summary(
    papers: List[Dict],
    report_date: str
) -> str:
    """使用AI生成日报摘要
    
    Args:
        papers: 论文列表
        report_date: 日报日期
        
    Returns:
        日报摘要（Markdown格式）
    """
    papers_info = []
    for i, paper in enumerate(papers, 1):
        title = paper.get("title", "未知标题")
        description = paper.get("description", "") or paper.get("abstract", "")
        author = paper.get("author", "未知作者")
        
        info = f"""
{i}. 标题：{title}
   作者：{author}
   摘要：{description[:300]}...
"""
        papers_info.append(info)
    
    user_message = f"""请根据以下论文生成今天的学术日报（日期：{report_date}）：

{''.join(papers_info)}

请生成一份清晰、专业的日报摘要。"""
    
    messages = [
        {"role": "system", "content": _SYSTEM_PROMPT},
        {"role": "user", "content": user_message}
    ]
    
    try:
        raw = await ollama.chat(messages)
        summary = raw.strip()
        
        logger.info(f"成功生成日报摘要")
        return summary
        
    except Exception as e:
        logger.error(f"生成日报摘要失败: {e}")
        return f"# arXiv 学术日报 - {report_date}\n\n今日共推荐 {len(papers)} 篇论文。\n\n生成摘要失败，请查看论文列表。"


def _markdown_to_html(markdown_text: str) -> str:
    """将Markdown转换为HTML（简单版本）
    
    Args:
        markdown_text: Markdown文本
        
    Returns:
        HTML文本
    """
    import html
    
    text = html.escape(markdown_text)
    
    lines = text.split('\n')
    html_lines = []
    
    for line in lines:
        if line.startswith('# '):
            html_lines.append(f'<h1>{line[2:]}</h1>')
        elif line.startswith('## '):
            html_lines.append(f'<h2>{line[3:]}</h2>')
        elif line.startswith('### '):
            html_lines.append(f'<h3>{line[4:]}</h3>')
        elif line.startswith('- '):
            html_lines.append(f'<li>{line[2:]}</li>')
        elif line.startswith('1. ') or line.startswith('2. ') or line.startswith('3. '):
            html_lines.append(f'<p>{line}</p>')
        elif line.strip() == '':
            html_lines.append('<br>')
        else:
            html_lines.append(f'<p>{line}</p>')
    
    return '\n'.join(html_lines)


async def generate_reports_for_all_users() -> Dict:
    """为所有启用日报的用户生成日报
    
    Returns:
        生成统计
    """
    logger.info("开始为所有用户生成日报")
    
    stats = {
        "total_users": 0,
        "success": 0,
        "skipped": 0,
        "failed": 0
    }
    
    try:
        all_interests = calendar_db.get_user_interests("")
        user_ids = set(i["user_id"] for i in all_interests)
        
        stats["total_users"] = len(user_ids)
        
        for user_id in user_ids:
            preference = calendar_db.get_arxiv_preference(user_id)
            
            if preference and not preference.get("is_enabled", 1):
                stats["skipped"] += 1
                continue
            
            try:
                result = await generate_daily_report_from_recommendations(user_id)
                
                if result.get("status") == "success":
                    stats["success"] += 1
                else:
                    stats["skipped"] += 1
                    
            except Exception as e:
                logger.error(f"为用户 {user_id} 生成日报失败: {e}")
                stats["failed"] += 1
        
        logger.info(f"日报生成完成: {stats}")
        return stats
        
    except Exception as e:
        logger.error(f"批量生成日报失败: {e}")
        return stats


report_generator = type('ReportGenerator', (), {
    'generate_daily_report': generate_daily_report_from_recommendations,
    'generate_for_all_users': generate_reports_for_all_users
})()
