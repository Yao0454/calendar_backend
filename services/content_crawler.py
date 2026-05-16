"""Content Crawler Service - 从 arXiv、GitHub 爬取内容"""

import asyncio
import logging
import httpx
import feedparser
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from typing import List, Dict

from data import calendar_db

logger = logging.getLogger(__name__)


class ContentCrawler(ABC):
    """内容爬虫基类"""

    def __init__(self):
        self.source = ""
        self.timeout = 30

    @abstractmethod
    async def search(self, keywords: List[str], limit: int = 10) -> List[Dict]:
        """搜索内容"""
        pass


class ArxivCrawler(ContentCrawler):
    """arXiv 论文爬虫"""

    def __init__(self):
        super().__init__()
        self.source = "arxiv"
        self.base_url = "https://export.arxiv.org/api/query"

    async def search(
        self,
        keywords: List[str],
        categories: List[str] | None = None,
        days: int = 7,
        limit: int = 10
    ) -> List[Dict]:
        """搜索 arXiv 论文
        
        Args:
            keywords: 搜索关键词列表
            categories: arXiv 分类，如 ['cs.AI', 'cs.LG']
            days: 搜索最近 N 天的论文
            limit: 返回结果数量
        """
        query_parts = []
        for kw in keywords:
            query_parts.append(f'all:"{kw}"')
        query = " OR ".join(query_parts)

        if categories:
            cat_query = " OR ".join([f"cat:{cat}" for cat in categories])
            query = f"({query}) AND ({cat_query})"

        now = datetime.utcnow()
        start_date = now - timedelta(days=days)
        date_query = f'submittedDate:[{start_date.strftime("%Y%m%d0000")} TO {now.strftime("%Y%m%d2359")}]'
        query = f"({query}) AND {date_query}"

        logger.info(f"arXiv 搜索: {query}")

        try:
            async with httpx.AsyncClient(timeout=self.timeout, follow_redirects=True) as client:
                response = await client.get(
                    self.base_url,
                    params={
                        "search_query": query,
                        "start": 0,
                        "max_results": limit,
                        "sortBy": "submittedDate",
                        "sortOrder": "descending"
                    }
                )
                response.raise_for_status()

                feed = feedparser.parse(response.text)
                
                results = []
                for entry in feed.entries:
                    arxiv_id = entry.id.split("/abs/")[-1]
                    paper = {
                        "source": self.source,
                        "source_id": arxiv_id,
                        "title": entry.title,
                        "description": entry.summary,
                        "url": entry.id,
                        "author": ", ".join([author.name for author in entry.authors]) if hasattr(entry, 'authors') else "",
                        "published_date": entry.published.split("T")[0] if hasattr(entry, 'published') else "",
                        "content_type": "paper",
                        "tags": [tag.term for tag in entry.tags] if hasattr(entry, 'tags') else [],
                        "stars": 0
                    }
                    results.append(paper)
                
                logger.info(f"arXiv 找到 {len(results)} 篇论文")
                return results

        except Exception as e:
            logger.error(f"arXiv 搜索失败: {e}")
            return []


class GitHubCrawler(ContentCrawler):
    """GitHub 仓库爬虫"""

    def __init__(self, token: str | None = None):
        super().__init__()
        self.source = "github"
        self.base_url = "https://api.github.com"
        self.token = token
        self.headers = {
            "Accept": "application/vnd.github.v3+json",
        }
        if token:
            self.headers["Authorization"] = f"token {token}"

    async def search(
        self,
        keywords: List[str],
        language: str | None = None,
        days: int = 7,
        limit: int = 10
    ) -> List[Dict]:
        """搜索 GitHub 仓库
        
        Args:
            keywords: 搜索关键词
            language: 编程语言过滤
            days: 搜索最近 N 天创建的仓库
            limit: 返回结果数量
        """
        # Use single-word keywords with OR (multi-word terms break GitHub OR syntax)
        single_kws = [kw.strip() for kw in keywords if kw.strip() and " " not in kw.strip()]
        if not single_kws:
            single_kws = ["LLM", "transformer"]
        kw_query = " OR ".join(single_kws[:6])
        query_parts = [kw_query]

        if language:
            query_parts.append(f"language:{language}")

        query_parts.append("stars:>10")
        query = " ".join(query_parts)
        logger.info(f"GitHub 搜索: {query}")

        try:
            async with httpx.AsyncClient(timeout=30, follow_redirects=True, headers=self.headers) as client:
                response = await client.get(
                    f"{self.base_url}/search/repositories",
                    params={
                        "q": query,
                        "sort": "stars",
                        "order": "desc",
                        "per_page": limit
                    }
                )
                response.raise_for_status()
                data = response.json()

                results = []
                for item in data.get("items", []):
                    repo = {
                        "source": self.source,
                        "source_id": str(item["id"]),
                        "title": item["full_name"],
                        "description": item.get("description", ""),
                        "url": item["html_url"],
                        "author": item["owner"]["login"],
                        "published_date": item["created_at"].split("T")[0],
                        "content_type": "repo",
                        "tags": item.get("topics", []),
                        "stars": item.get("stargazers_count", 0)
                    }
                    results.append(repo)

                logger.info(f"GitHub 找到 {len(results)} 个仓库")
                return results

        except Exception as e:
            logger.error(f"GitHub 搜索失败: {e}")
            return []




class HuggingFaceCrawler(ContentCrawler):
    """HuggingFace 每日论文爬虫 - 免费公开接口"""

    def __init__(self):
        super().__init__()
        self.source = "huggingface"
        self.base_url = "https://huggingface.co/api/daily_papers"

    async def search(
        self,
        keywords: List[str] | None = None,
        limit: int = 30
    ) -> List[Dict]:
        """获取 HuggingFace 每日热门论文"""
        try:
            async with httpx.AsyncClient(timeout=60, follow_redirects=True) as client:
                response = await client.get(self.base_url)
                response.raise_for_status()
                data = response.json()
                if not isinstance(data, list):
                    logger.warning(f"HuggingFace: unexpected response type {type(data)}")
                    return []

            results = []
            for item in data[:limit]:
                paper = item.get("paper", {})
                arxiv_id = paper.get("id", "")
                authors = paper.get("authors", [])
                author_str = ", ".join(
                    [a.get("name", "") for a in authors[:3]]
                )
                pub_date = paper.get("publishedAt", "")
                if pub_date:
                    pub_date = pub_date[:10]

                results.append({
                    "source": self.source,
                    "source_id": f"hf_{arxiv_id}",
                    "title": paper.get("title", ""),
                    "description": paper.get("summary", ""),
                    "url": f"https://huggingface.co/papers/{arxiv_id}",
                    "author": author_str,
                    "published_date": pub_date,
                    "content_type": "paper",
                    "tags": paper.get("categories", []),
                    "stars": item.get("upvotes", 0),
                })

            logger.info(f"HuggingFace: 获取到 {len(results)} 篇每日论文")
            return results

        except Exception as e:
            logger.error(f"HuggingFace 爬虫失败: {e}")
            return []

arxiv_crawler = ArxivCrawler()
github_crawler = GitHubCrawler()

huggingface_crawler = HuggingFaceCrawler()
