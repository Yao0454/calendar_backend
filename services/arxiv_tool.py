import logging
import json
import feedparser
import httpx
import re
from datetime import datetime, timedelta, timezone

logger = logging.getLogger(__name__)

ARXIV_API_URL = "https://export.arxiv.org/api/query"
# 可用的工具定义（供大模型使用）
AVAILABLE_TOOLS = {
    "search_arxiv": {
        "description": "在 arXiv 上搜索论文。可以按关键词、分类、日期范围搜索。",
        "parameters": {
            "keywords": {
                "type": "string",
                "description": "搜索关键词，如 'neural network acceleration' 或 'knowledge graph'",
                "required": True
            },
            "categories": {
                "type": "array",
                "description": "arXiv 分类，如 ['cs.AI', 'cs.LG']。不指定则搜索所有分类。",
                "required": False,
                "default": []
            },
            "date_range": {
                "type": "string",
                "enum": ["last_1_day", "last_7_days", "last_30_days", "any_time"],
                "description": "搜索范围",
                "default": "last_7_days"
            },
            "limit": {
                "type": "integer",
                "description": "返回结果数量，最多 50",
                "default": 10
            }
        }
    },
    "get_paper_details": {
        "description": "获取某篇论文的完整摘要和信息",
        "parameters": {
            "arxiv_id": {
                "type": "string",
                "description": "论文的 arXiv ID，如 '2501.12345'",
                "required": True
            }
        }
    }
}


def _get_date_query(date_range: str) -> str:
    now = datetime.now(timezone.utc)

    match = re.match(r"last_(\d+)_days?", date_range)
    if match:
        days = int(match.group(1))
        delta = timedelta(days=days)
    else:
        return ""

    start_date = (now - delta).strftime('%Y%m%d0000')
    end_date = now.strftime('%Y%m%d2359')

    return f'submittedDate:[{start_date} TO {end_date}]'

async def search_arxiv(
    keywords: str,
    categories: list = None,
    date_range: str = "last_7_days",
    limit: int = 10
) -> dict:
    try:
        query_parts = []
        query_parts.append(f'all:"{keywords}"')
        if categories:
            cat_query = " OR ".join([f"cat:{cat}" for cat in categories])
            query_parts.append(cat_query)
        date_query = _get_date_query(date_range)
        if date_query:
            query_parts.append(date_query)
        query = " AND ".join(query_parts)

        logger.info(f"Searching arXiv with query: {query}")

        params = {
            "search_query": query,
            "start": 0,
            "max_results": limit,
            "sortBy": "submittedDate",
            "sortOrder": "descending"
        }

        async with httpx.AsyncClient(timeout=15) as arxiv_client:
            response = await arxiv_client.get(ARXIV_API_URL, params=params)
            response.raise_for_status()
            data = response.json()



async def get_paper_details():
    pass
