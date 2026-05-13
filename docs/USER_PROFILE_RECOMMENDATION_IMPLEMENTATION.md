# 用户画像和智能推荐系统实现文档

## 概述

本文档详细说明如何构建用户画像管理系统和基于画像的智能内容推荐系统。系统会从 arXiv、GitHub 和 Twitter 爬取内容，根据用户兴趣推荐相关资料。

---

## 架构概览

```
┌────────────────────────────────────────────────────────┐
│  User Profile Management (routes/profile_router.py)    │
│  ├─ POST   /profile/interests     → 添加兴趣标签       │
│  ├─ GET    /profile/interests     → 查看用户画像       │
│  ├─ PUT    /profile/interests/{id}→ 更新兴趣           │
│  └─ DELETE /profile/interests/{id}→ 删除兴趣           │
├────────────────────────────────────────────────────────┤
│  Content Crawler Service (services/content_crawler.py) │
│  ├─ ArxivCrawler                  → arXiv 爬虫         │
│  ├─ GitHubCrawler                 → GitHub 爬虫        │
│  └─ TwitterCrawler                → Twitter 爬虫       │
├────────────────────────────────────────────────────────┤
│  Recommendation Engine                                 │
│  (services/recommendation_engine.py)                   │
│  ├─ calculate_relevance()  → 计算相关度               │
│  ├─ rank_content()         → 排序内容                 │
│  └─ generate_recommendations()  → 生成推荐            │
├────────────────────────────────────────────────────────┤
│  Recommendation Routes (routes/recommendations_router) │
│  ├─ GET  /recommendations/feed       → 获取推荐列表   │
│  ├─ GET  /recommendations/{id}       → 获取内容详情   │
│  └─ POST /recommendations/{id}/read  → 标记已读       │
├────────────────────────────────────────────────────────┤
│  Background Tasks (services/background_tasks.py)       │
│  └─ Periodic crawling and recommendation generation   │
└────────────────────────────────────────────────────────┘
```

---

## 1. 数据库扩展

### 1.1 新增表结构

在 `data/calendar_db.py` 的 `init_db()` 函数中添加：

```sql
-- 用户兴趣标签表
CREATE TABLE IF NOT EXISTS user_interests (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id         TEXT    NOT NULL,
    category        TEXT    NOT NULL,      -- "research" | "project" | "skill"
    tag             TEXT    NOT NULL,      -- 标签名称，如 "PyTorch", "WebAssembly"
    keywords        TEXT    NOT NULL,      -- JSON 数组：多个搜索关键词
    weight          REAL    DEFAULT 1.0,   -- 权重 0-1，影响推荐排序
    created_at      TEXT    NOT NULL,
    updated_at      TEXT    NOT NULL,
    UNIQUE(user_id, category, tag)
);

-- 爬取的内容表
CREATE TABLE IF NOT EXISTS content_items (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    source          TEXT    NOT NULL,      -- "arxiv" | "github" | "twitter"
    source_id       TEXT    NOT NULL UNIQUE,  -- 来源唯一 ID
    title           TEXT    NOT NULL,
    description     TEXT,
    url             TEXT    NOT NULL,
    author          TEXT,
    published_date  TEXT,                  -- YYYY-MM-DD
    content_type    TEXT,                  -- "paper" | "repo" | "tweet"
    tags            TEXT,                  -- JSON 数组：分类标签
    relevance_score REAL    DEFAULT 0.0,   -- 内部使用，计算时填充
    created_at      TEXT    NOT NULL
);

-- 用户推荐记录表
CREATE TABLE IF NOT EXISTS user_recommendations (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id         TEXT    NOT NULL,
    content_id      INTEGER NOT NULL,
    recommendation_score REAL,             -- 对该用户的推荐分数
    read            INTEGER DEFAULT 0,     -- 0 | 1
    clicked         INTEGER DEFAULT 0,     -- 0 | 1，用户点击记录
    saved           INTEGER DEFAULT 0,     -- 0 | 1，用户收藏记录
    created_at      TEXT    NOT NULL,
    updated_at      TEXT    NOT NULL,
    UNIQUE(user_id, content_id),
    FOREIGN KEY (content_id) REFERENCES content_items(id)
);

-- 爬虫任务日志
CREATE TABLE IF NOT EXISTS crawler_logs (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    source          TEXT    NOT NULL,      -- "arxiv" | "github" | "twitter"
    status          TEXT    NOT NULL,      -- "success" | "failed" | "partial"
    items_found     INTEGER DEFAULT 0,
    items_saved     INTEGER DEFAULT 0,
    error_message   TEXT,
    started_at      TEXT    NOT NULL,
    completed_at    TEXT,
    duration_seconds INTEGER
);

-- 索引优化
CREATE INDEX IF NOT EXISTS idx_user_interests ON user_interests(user_id);
CREATE INDEX IF NOT EXISTS idx_content_source ON content_items(source);
CREATE INDEX IF NOT EXISTS idx_content_date ON content_items(published_date);
CREATE INDEX IF NOT EXISTS idx_recommendations_user ON user_recommendations(user_id);
CREATE INDEX IF NOT EXISTS idx_recommendations_score ON user_recommendations(recommendation_score DESC);
CREATE INDEX IF NOT EXISTS idx_crawler_logs_date ON crawler_logs(started_at);
```

### 1.2 数据库操作函数

在 `data/calendar_db.py` 末尾添加：

```python
# ─────────────────────────────────────────────────────────────────────────────
# User Interests
# ─────────────────────────────────────────────────────────────────────────────

def create_or_update_interest(
    user_id: str,
    category: str,      # "research" | "project" | "skill"
    tag: str,
    keywords: list,
    weight: float = 1.0
) -> dict:
    """创建或更新用户兴趣。"""
    now = _now()
    with _conn() as c:
        c.execute(
            """INSERT OR REPLACE INTO user_interests
               (user_id, category, tag, keywords, weight, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (user_id, category, tag, json.dumps(keywords), weight, now, now)
        )
        result = c.execute(
            "SELECT * FROM user_interests WHERE user_id=? AND category=? AND tag=?",
            (user_id, category, tag)
        ).fetchone()
    return dict(result) if result else None


def get_user_interests(user_id: str, category: str | None = None) -> list:
    """获取用户的所有兴趣或特定分类的兴趣。"""
    with _conn() as c:
        c.row_factory = sqlite3.Row
        if category:
            rows = c.execute(
                """SELECT * FROM user_interests WHERE user_id=? AND category=?
                   ORDER BY weight DESC""",
                (user_id, category)
            ).fetchall()
        else:
            rows = c.execute(
                """SELECT * FROM user_interests WHERE user_id=?
                   ORDER BY category, weight DESC""",
                (user_id,)
            ).fetchall()
    result = []
    for row in rows:
        d = dict(row)
        d["keywords"] = json.loads(d["keywords"])
        result.append(d)
    return result


def delete_interest(user_id: str, interest_id: int) -> bool:
    """删除用户兴趣。"""
    with _conn() as c:
        c.execute(
            "DELETE FROM user_interests WHERE id=? AND user_id=?",
            (interest_id, user_id)
        )
    return True


# ─────────────────────────────────────────────────────────────────────────────
# Content Items
# ─────────────────────────────────────────────────────────────────────────────

def create_or_update_content(
    source: str,           # "arxiv" | "github" | "twitter"
    source_id: str,
    title: str,
    description: str | None,
    url: str,
    author: str | None,
    published_date: str | None,
    content_type: str,     # "paper" | "repo" | "tweet"
    tags: list | None = None
) -> dict | None:
    """创建或更新内容项。"""
    now = _now()
    try:
        with _conn() as c:
            c.execute(
                """INSERT OR IGNORE INTO content_items
                   (source, source_id, title, description, url, author, 
                    published_date, content_type, tags, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    source,
                    source_id,
                    title,
                    description,
                    url,
                    author,
                    published_date,
                    content_type,
                    json.dumps(tags or []),
                    now
                )
            )
            result = c.execute(
                "SELECT * FROM content_items WHERE source=? AND source_id=?",
                (source, source_id)
            ).fetchone()
        return dict(result) if result else None
    except sqlite3.IntegrityError:
        # source_id 已存在
        return None


def get_content_items(
    source: str | None = None,
    limit: int = 50,
    offset: int = 0
) -> list:
    """获取内容项。"""
    with _conn() as c:
        c.row_factory = sqlite3.Row
        if source:
            rows = c.execute(
                """SELECT * FROM content_items WHERE source=?
                   ORDER BY published_date DESC
                   LIMIT ? OFFSET ?""",
                (source, limit, offset)
            ).fetchall()
        else:
            rows = c.execute(
                """SELECT * FROM content_items
                   ORDER BY published_date DESC
                   LIMIT ? OFFSET ?""",
                (limit, offset)
            ).fetchall()
    result = []
    for row in rows:
        d = dict(row)
        d["tags"] = json.loads(d.get("tags", "[]"))
        result.append(d)
    return result


def get_content_by_id(content_id: int) -> dict | None:
    """获取单个内容项。"""
    with _conn() as c:
        c.row_factory = sqlite3.Row
        row = c.execute(
            "SELECT * FROM content_items WHERE id=?",
            (content_id,)
        ).fetchone()
    if not row:
        return None
    result = dict(row)
    result["tags"] = json.loads(result.get("tags", "[]"))
    return result


# ─────────────────────────────────────────────────────────────────────────────
# User Recommendations
# ─────────────────────────────────────────────────────────────────────────────

def create_recommendation(
    user_id: str,
    content_id: int,
    recommendation_score: float
) -> dict | None:
    """为用户创建推荐记录。"""
    now = _now()
    try:
        with _conn() as c:
            c.execute(
                """INSERT OR REPLACE INTO user_recommendations
                   (user_id, content_id, recommendation_score, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?)""",
                (user_id, content_id, recommendation_score, now, now)
            )
            result = c.execute(
                "SELECT * FROM user_recommendations WHERE user_id=? AND content_id=?",
                (user_id, content_id)
            ).fetchone()
        return dict(result) if result else None
    except sqlite3.IntegrityError:
        return None


def get_user_recommendations(user_id: str, unread_only: bool = False) -> list:
    """获取用户的推荐列表。"""
    with _conn() as c:
        c.row_factory = sqlite3.Row
        if unread_only:
            rows = c.execute(
                """SELECT ur.*, ci.* FROM user_recommendations ur
                   JOIN content_items ci ON ur.content_id = ci.id
                   WHERE ur.user_id=? AND ur.read=0
                   ORDER BY ur.recommendation_score DESC""",
                (user_id,)
            ).fetchall()
        else:
            rows = c.execute(
                """SELECT ur.*, ci.* FROM user_recommendations ur
                   JOIN content_items ci ON ur.content_id = ci.id
                   WHERE ur.user_id=?
                   ORDER BY ur.recommendation_score DESC""",
                (user_id,)
            ).fetchall()
    return [dict(row) for row in rows]


def mark_recommendation_read(user_id: str, content_id: int) -> bool:
    """标记推荐为已读。"""
    with _conn() as c:
        c.execute(
            """UPDATE user_recommendations SET read=1, updated_at=?
               WHERE user_id=? AND content_id=?""",
            (_now(), user_id, content_id)
        )
    return True


def mark_recommendation_saved(user_id: str, content_id: int) -> bool:
    """标记推荐为已保存（收藏）。"""
    with _conn() as c:
        c.execute(
            """UPDATE user_recommendations SET saved=1, updated_at=?
               WHERE user_id=? AND content_id=?""",
            (_now(), user_id, content_id)
        )
    return True


# ─────────────────────────────────────────────────────────────────────────────
# Crawler Logs
# ─────────────────────────────────────────────────────────────────────────────

def log_crawler_run(
    source: str,
    status: str,
    items_found: int,
    items_saved: int,
    error_message: str | None = None,
    duration_seconds: int | None = None
) -> None:
    """记录爬虫运行日志。"""
    with _conn() as c:
        c.execute(
            """INSERT INTO crawler_logs
               (source, status, items_found, items_saved, error_message, 
                started_at, completed_at, duration_seconds)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                source,
                status,
                items_found,
                items_saved,
                error_message,
                _now(),
                _now(),
                duration_seconds
            )
        )
```

---

## 2. 内容爬虫服务

### 2.1 基础爬虫框架

创建文件 `services/content_crawler.py`：

```python
"""Content Crawler Service - 从 arXiv、GitHub、Twitter 爬取内容"""

import asyncio
import json
import logging
import httpx
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from typing import Optional, List, Dict

from data import calendar_db

logger = logging.getLogger(__name__)


class ContentCrawler(ABC):
    """内容爬虫基类"""

    def __init__(self):
        self.source = ""
        self.timeout = 15

    @abstractmethod
    async def search(self, keywords: List[str], limit: int = 10) -> List[Dict]:
        """搜索内容"""
        pass

    @abstractmethod
    async def get_details(self, source_id: str) -> Dict:
        """获取内容详情"""
        pass

    async def _fetch(self, url: str, params: dict = None) -> dict | None:
        """发送 HTTP 请求"""
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(url, params=params)
                response.raise_for_status()
                return response.json()
        except Exception as e:
            logger.error(f"HTTP 请求失败 ({self.source}): {url} - {e}")
            return None


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
        # 构建查询
        query_parts = []
        for kw in keywords:
            query_parts.append(f'all:"{kw}"')
        query = " OR ".join(query_parts)

        # 添加分类过滤
        if categories:
            cat_query = " OR ".join([f"cat:{cat}" for cat in categories])
            query = f"({query}) AND ({cat_query})"

        # 添加日期范围
        now = datetime.utcnow()
        start_date = now - timedelta(days=days)
        date_query = f'submittedDate:[{start_date.strftime("%Y%m%d0000")} TO {now.strftime("%Y%m%d2359")}]'
        query = f"({query}) AND {date_query}"

        logger.info(f"arXiv 搜索: {query}")

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
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

                # 解析 Atom XML 格式（arXiv 返回 XML）
                import feedparser
                feed = feedparser.parse(response.text)
                
                results = []
                for entry in feed.entries:
                    paper = {
                        "source": self.source,
                        "source_id": entry.id.split("/abs/")[-1],
                        "title": entry.title,
                        "description": entry.summary,
                        "url": entry.id,
                        "author": ", ".join([author.name for author in entry.authors]) if hasattr(entry, 'authors') else "",
                        "published_date": entry.published.split("T")[0],
                        "content_type": "paper",
                        "tags": [tag.term for tag in entry.tags] if hasattr(entry, 'tags') else []
                    }
                    results.append(paper)
                
                return results

        except Exception as e:
            logger.error(f"arXiv 搜索失败: {e}")
            return []

    async def get_details(self, arxiv_id: str) -> Dict | None:
        """获取论文详情（包括 PDF URL）"""
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    self.base_url,
                    params={"id_list": arxiv_id, "max_results": 1}
                )
                response.raise_for_status()
                
                import feedparser
                feed = feedparser.parse(response.text)
                if feed.entries:
                    entry = feed.entries[0]
                    return {
                        "arxiv_id": arxiv_id,
                        "title": entry.title,
                        "pdf_url": f"https://arxiv.org/pdf/{arxiv_id}.pdf",
                        "abstract": entry.summary
                    }
        except Exception as e:
            logger.error(f"获取 arXiv 详情失败: {e}")
        return None


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
        # 构建查询
        query_parts = [f'"{" ".join(keywords)}"']
        
        if language:
            query_parts.append(f"language:{language}")
        
        # 日期范围
        start_date = (datetime.utcnow() - timedelta(days=days)).strftime("%Y-%m-%d")
        query_parts.append(f"created:>={start_date}")

        query = " ".join(query_parts)
        logger.info(f"GitHub 搜索: {query}")

        try:
            async with httpx.AsyncClient(timeout=self.timeout, headers=self.headers) as client:
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
                        "description": item["description"] or "",
                        "url": item["html_url"],
                        "author": item["owner"]["login"],
                        "published_date": item["created_at"].split("T")[0],
                        "content_type": "repo",
                        "tags": item.get("topics", [])
                    }
                    results.append(repo)

                return results

        except Exception as e:
            logger.error(f"GitHub 搜索失败: {e}")
            return []

    async def get_details(self, repo_full_name: str) -> Dict | None:
        """获取仓库详情"""
        try:
            async with httpx.AsyncClient(timeout=self.timeout, headers=self.headers) as client:
                response = await client.get(f"{self.base_url}/repos/{repo_full_name}")
                response.raise_for_status()
                data = response.json()
                
                return {
                    "repo": repo_full_name,
                    "stars": data["stargazers_count"],
                    "language": data["language"],
                    "description": data["description"],
                    "url": data["html_url"]
                }
        except Exception as e:
            logger.error(f"获取 GitHub 仓库详情失败: {e}")
        return None


class TwitterCrawler(ContentCrawler):
    """Twitter 推文爬虫"""

    def __init__(self, bearer_token: str):
        super().__init__()
        self.source = "twitter"
        self.base_url = "https://api.twitter.com/2"
        self.bearer_token = bearer_token
        self.headers = {
            "Authorization": f"Bearer {bearer_token}"
        }

    async def search(
        self,
        keywords: List[str],
        days: int = 7,
        limit: int = 10
    ) -> List[Dict]:
        """搜索 Twitter 推文"""
        # 注意: Twitter API v2 需要付费 Essential 及以上
        # 这是示例实现，实际使用需要有效的 API 密钥
        
        query = " ".join(keywords)
        start_time = (datetime.utcnow() - timedelta(days=days)).isoformat() + "Z"

        logger.info(f"Twitter 搜索: {query}")

        try:
            async with httpx.AsyncClient(timeout=self.timeout, headers=self.headers) as client:
                response = await client.get(
                    f"{self.base_url}/tweets/search/recent",
                    params={
                        "query": query,
                        "max_results": min(limit, 100),
                        "start_time": start_time,
                        "tweet.fields": "created_at,public_metrics",
                        "expansions": "author_id",
                        "user.fields": "username"
                    }
                )
                
                if response.status_code == 429:
                    logger.warning("Twitter API 速率限制")
                    return []
                
                response.raise_for_status()
                data = response.json()

                results = []
                users = {user["id"]: user["username"] for user in data.get("includes", {}).get("users", [])}
                
                for tweet in data.get("data", []):
                    tweet_obj = {
                        "source": self.source,
                        "source_id": tweet["id"],
                        "title": tweet["text"][:100],
                        "description": tweet["text"],
                        "url": f"https://twitter.com/i/web/status/{tweet['id']}",
                        "author": users.get(tweet["author_id"], "Unknown"),
                        "published_date": tweet["created_at"].split("T")[0],
                        "content_type": "tweet",
                        "tags": []
                    }
                    results.append(tweet_obj)

                return results

        except Exception as e:
            logger.error(f"Twitter 搜索失败: {e}")
            return []

    async def get_details(self, tweet_id: str) -> Dict | None:
        """获取推文详情"""
        try:
            async with httpx.AsyncClient(timeout=self.timeout, headers=self.headers) as client:
                response = await client.get(
                    f"{self.base_url}/tweets/{tweet_id}",
                    params={
                        "tweet.fields": "created_at,public_metrics",
                        "expansions": "author_id"
                    }
                )
                response.raise_for_status()
                data = response.json()
                
                tweet = data["data"]
                return {
                    "id": tweet["id"],
                    "text": tweet["text"],
                    "likes": tweet["public_metrics"]["like_count"],
                    "retweets": tweet["public_metrics"]["retweet_count"]
                }
        except Exception as e:
            logger.error(f"获取推文详情失败: {e}")
        return None
```

---

## 3. 推荐引擎

创建文件 `services/recommendation_engine.py`：

```python
"""Recommendation Engine - 基于用户画像生成推荐"""

import logging
import math
from typing import List, Dict

from data import calendar_db

logger = logging.getLogger(__name__)


class RecommendationEngine:
    """推荐引擎"""

    def __init__(self):
        self.min_relevance_score = 0.3

    def calculate_relevance(
        self,
        user_interests: List[Dict],
        content: Dict
    ) -> float:
        """计算内容与用户兴趣的相关度
        
        Args:
            user_interests: 用户的兴趣列表
            content: 内容对象
            
        Returns:
            相关度分数 0-1
        """
        if not user_interests:
            return 0.0

        content_text = (
            (content.get("title") or "") + " " +
            (content.get("description") or "")
        ).lower()

        total_score = 0.0
        max_weight = 0.0

        for interest in user_interests:
            weight = interest.get("weight", 1.0)
            max_weight += weight

            keywords = interest.get("keywords", [])
            interest_score = 0.0

            # 关键词匹配
            for keyword in keywords:
                keyword_lower = keyword.lower()
                if keyword_lower in content_text:
                    # 出现次数越多，分数越高
                    count = content_text.count(keyword_lower)
                    interest_score += min(count * 0.2, 1.0)

            # 取平均分
            if keywords:
                interest_score = min(interest_score / len(keywords), 1.0)

            total_score += interest_score * weight

        # 归一化
        if max_weight > 0:
            return min(total_score / max_weight, 1.0)

        return 0.0

    def rank_content(
        self,
        user_id: str,
        content_list: List[Dict],
        limit: int = 20
    ) -> List[Dict]:
        """为用户排序和筛选内容
        
        Args:
            user_id: 用户 ID
            content_list: 内容列表
            limit: 返回的最大结果数
            
        Returns:
            排序后的推荐内容列表
        """
        # 获取用户兴趣
        user_interests = calendar_db.get_user_interests(user_id)
        if not user_interests:
            logger.warning(f"用户 {user_id} 没有设置兴趣")
            return []

        # 计算每个内容的相关度
        scored_content = []
        for content in content_list:
            score = self.calculate_relevance(user_interests, content)
            if score >= self.min_relevance_score:
                content_copy = content.copy()
                content_copy["relevance_score"] = score
                scored_content.append(content_copy)

        # 按相关度排序
        scored_content.sort(key=lambda x: x["relevance_score"], reverse=True)

        return scored_content[:limit]

    async def generate_recommendations(
        self,
        user_id: str,
        batch_size: int = 50
    ) -> Dict:
        """为用户生成推荐
        
        Args:
            user_id: 用户 ID
            batch_size: 一次处理的内容数量
            
        Returns:
            生成的推荐统计
        """
        # 获取用户兴趣
        user_interests = calendar_db.get_user_interests(user_id)
        if not user_interests:
            return {"status": "skipped", "reason": "用户未设置兴趣"}

        stats = {
            "total_processed": 0,
            "recommendations_created": 0,
            "sources": {}
        }

        # 优先级顺序: arXiv > GitHub > Twitter
        sources = ["arxiv", "github", "twitter"]

        for source in sources:
            # 获取该来源的所有未推荐过的内容
            all_content = calendar_db.get_content_items(source=source, limit=1000)
            
            # 过滤已推荐过的
            new_content = []
            for content in all_content:
                existing = calendar_db.get_user_recommendations(user_id)
                existing_ids = {r["content_id"] for r in existing}
                if content["id"] not in existing_ids:
                    new_content.append(content)

            # 排序
            ranked = self.rank_content(user_id, new_content, limit=50)

            source_count = 0
            for content in ranked:
                score = content.get("relevance_score", 0.0)
                calendar_db.create_recommendation(user_id, content["id"], score)
                source_count += 1

            stats["total_processed"] += len(all_content)
            stats["recommendations_created"] += source_count
            stats["sources"][source] = source_count

            if source_count >= 10:  # 每个来源至少推荐 10 个
                break

        return stats
```

---

## 4. 用户画像路由

创建文件 `routes/profile_router.py`：

```python
"""User Profile Management Routes"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from auth.deps import get_current_session
from auth.models import SessionPrincipal
from data import calendar_db

router = APIRouter(prefix="/profile", tags=["profile"])


# ── Schemas ───────────────────────────────────────────────────────────────────

class InterestIn(BaseModel):
    """添加兴趣请求"""
    category: str      # "research" | "project" | "skill"
    tag: str           # 标签名称
    keywords: list     # 关键词列表
    weight: float = 1.0


class InterestUpdate(BaseModel):
    """更新兴趣请求"""
    keywords: list | None = None
    weight: float | None = None


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get("/interests")
async def get_interests(
    category: str | None = None,
    session: SessionPrincipal = Depends(get_current_session)
):
    """获取用户的兴趣标签"""
    interests = calendar_db.get_user_interests(session.user_id, category)
    return {
        "user_id": session.user_id,
        "interests": interests,
        "total": len(interests)
    }


@router.post("/interests", status_code=201)
async def create_interest(
    req: InterestIn,
    session: SessionPrincipal = Depends(get_current_session)
):
    """添加新兴趣"""
    interest = calendar_db.create_or_update_interest(
        session.user_id,
        req.category,
        req.tag,
        req.keywords,
        req.weight
    )
    if not interest:
        raise HTTPException(status_code=400, detail="Failed to create interest")
    
    return {
        "status": "created",
        "interest": interest
    }


@router.put("/interests/{interest_id}")
async def update_interest(
    interest_id: int,
    req: InterestUpdate,
    session: SessionPrincipal = Depends(get_current_session)
):
    """更新兴趣"""
    # 先获取现有兴趣
    interests = calendar_db.get_user_interests(session.user_id)
    target = None
    for interest in interests:
        if interest["id"] == interest_id:
            target = interest
            break

    if not target:
        raise HTTPException(status_code=404, detail="Interest not found")

    # 更新字段
    keywords = req.keywords or target["keywords"]
    weight = req.weight if req.weight is not None else target["weight"]

    updated = calendar_db.create_or_update_interest(
        session.user_id,
        target["category"],
        target["tag"],
        keywords,
        weight
    )

    return {
        "status": "updated",
        "interest": updated
    }


@router.delete("/interests/{interest_id}", status_code=204)
async def delete_interest(
    interest_id: int,
    session: SessionPrincipal = Depends(get_current_session)
):
    """删除兴趣"""
    calendar_db.delete_interest(session.user_id, interest_id)
    return {"status": "deleted"}


@router.get("/summary")
async def get_profile_summary(
    session: SessionPrincipal = Depends(get_current_session)
):
    """获取用户画像摘要"""
    interests = calendar_db.get_user_interests(session.user_id)
    
    # 按分类统计
    summary = {
        "research": [],
        "project": [],
        "skill": []
    }
    
    for interest in interests:
        category = interest["category"]
        if category in summary:
            summary[category].append(interest["tag"])

    return {
        "user_id": session.user_id,
        "total_interests": len(interests),
        "summary": summary
    }
```

---

## 5. 推荐路由

创建文件 `routes/recommendations_router.py`：

```python
"""Content Recommendations Routes"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from auth.deps import get_current_session
from auth.models import SessionPrincipal
from data import calendar_db

router = APIRouter(prefix="/recommendations", tags=["recommendations"])


# ── Schemas ───────────────────────────────────────────────────────────────────

class ContentAction(BaseModel):
    """内容操作"""
    action: str  # "read" | "save" | "like"


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get("/feed")
async def get_recommendation_feed(
    unread_only: bool = False,
    limit: int = 20,
    offset: int = 0,
    session: SessionPrincipal = Depends(get_current_session)
):
    """获取推荐内容列表"""
    recommendations = calendar_db.get_user_recommendations(session.user_id, unread_only)
    
    # 分页
    paginated = recommendations[offset:offset + limit]
    
    return {
        "total": len(recommendations),
        "limit": limit,
        "offset": offset,
        "items": paginated
    }


@router.get("/{content_id}")
async def get_content_detail(
    content_id: int,
    session: SessionPrincipal = Depends(get_current_session)
):
    """获取内容详情"""
    content = calendar_db.get_content_by_id(content_id)
    if not content:
        raise HTTPException(status_code=404, detail="Content not found")
    
    return {"content": content}


@router.post("/{content_id}/read", status_code=204)
async def mark_as_read(
    content_id: int,
    session: SessionPrincipal = Depends(get_current_session)
):
    """标记推荐为已读"""
    calendar_db.mark_recommendation_read(session.user_id, content_id)
    return {"status": "marked_read"}


@router.post("/{content_id}/save", status_code=204)
async def save_content(
    content_id: int,
    session: SessionPrincipal = Depends(get_current_session)
):
    """收藏内容"""
    calendar_db.mark_recommendation_saved(session.user_id, content_id)
    return {"status": "saved"}


@router.get("/stats/summary")
async def get_stats_summary(
    session: SessionPrincipal = Depends(get_current_session)
):
    """获取推荐统计"""
    recommendations = calendar_db.get_user_recommendations(session.user_id)
    
    stats = {
        "total_recommendations": len(recommendations),
        "unread": sum(1 for r in recommendations if not r.get("read")),
        "saved": sum(1 for r in recommendations if r.get("saved")),
        "by_source": {}
    }
    
    # 按来源统计
    for r in recommendations:
        source = r.get("source", "unknown")
        if source not in stats["by_source"]:
            stats["by_source"][source] = {"total": 0, "unread": 0}
        
        stats["by_source"][source]["total"] += 1
        if not r.get("read"):
            stats["by_source"][source]["unread"] += 1
    
    return stats
```

---

## 6. 后台任务

创建文件 `services/background_tasks.py`：

```python
"""Background Tasks - 定时爬虫和推荐生成"""

import asyncio
import logging
from datetime import datetime, timedelta
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from data import calendar_db
from services.content_crawler import ArxivCrawler, GitHubCrawler
from services.recommendation_engine import RecommendationEngine

logger = logging.getLogger(__name__)


class BackgroundTaskManager:
    """后台任务管理器"""

    def __init__(self):
        self.scheduler = AsyncIOScheduler()
        self.arxiv_crawler = ArxivCrawler()
        self.github_crawler = GitHubCrawler()
        self.recommendation_engine = RecommendationEngine()

    def start(self):
        """启动后台任务"""
        # 每天早上 7:00 执行爬虫
        self.scheduler.add_job(
            self.run_crawlers,
            CronTrigger(hour=7, minute=0),
            id="daily_crawl",
            name="Daily Content Crawl"
        )

        # 每小时执行一次推荐生成
        self.scheduler.add_job(
            self.generate_recommendations_for_all_users,
            CronTrigger(minute=0),
            id="hourly_recommendations",
            name="Generate Recommendations"
        )

        self.scheduler.start()
        logger.info("Background tasks started")

    async def run_crawlers(self):
        """运行所有爬虫"""
        logger.info("开始运行爬虫任务")
        
        start_time = datetime.now()
        
        # 运行 arXiv 爬虫
        await self._run_arxiv_crawler()
        
        # 运行 GitHub 爬虫
        await self._run_github_crawler()

        duration = (datetime.now() - start_time).total_seconds()
        logger.info(f"爬虫任务完成，耗时 {duration} 秒")

    async def _run_arxiv_crawler(self):
        """运行 arXiv 爬虫"""
        try:
            keywords = ["machine learning", "deep learning", "neural networks"]
            categories = ["cs.LG", "cs.AI"]
            
            papers = await self.arxiv_crawler.search(
                keywords,
                categories=categories,
                days=7,
                limit=50
            )
            
            saved_count = 0
            for paper in papers:
                result = calendar_db.create_or_update_content(
                    source=paper["source"],
                    source_id=paper["source_id"],
                    title=paper["title"],
                    description=paper["description"],
                    url=paper["url"],
                    author=paper["author"],
                    published_date=paper["published_date"],
                    content_type=paper["content_type"],
                    tags=paper.get("tags", [])
                )
                if result:
                    saved_count += 1
            
            calendar_db.log_crawler_run(
                source="arxiv",
                status="success",
                items_found=len(papers),
                items_saved=saved_count,
                duration_seconds=None
            )
            
            logger.info(f"arXiv: 找到 {len(papers)} 篇论文，保存 {saved_count} 篇")
            
        except Exception as e:
            logger_error = f"arXiv 爬虫错误: {e}"
            logger.error(logger_error)
            calendar_db.log_crawler_run(
                source="arxiv",
                status="failed",
                items_found=0,
                items_saved=0,
                error_message=str(e)
            )

    async def _run_github_crawler(self):
        """运行 GitHub 爬虫"""
        try:
            keywords = ["pytorch", "tensorflow", "machine-learning"]
            
            repos = await self.github_crawler.search(
                keywords,
                language="Python",
                days=7,
                limit=50
            )
            
            saved_count = 0
            for repo in repos:
                result = calendar_db.create_or_update_content(
                    source=repo["source"],
                    source_id=repo["source_id"],
                    title=repo["title"],
                    description=repo["description"],
                    url=repo["url"],
                    author=repo["author"],
                    published_date=repo["published_date"],
                    content_type=repo["content_type"],
                    tags=repo.get("tags", [])
                )
                if result:
                    saved_count += 1
            
            calendar_db.log_crawler_run(
                source="github",
                status="success",
                items_found=len(repos),
                items_saved=saved_count,
                duration_seconds=None
            )
            
            logger.info(f"GitHub: 找到 {len(repos)} 个仓库，保存 {saved_count} 个")
            
        except Exception as e:
            logger_error = f"GitHub 爬虫错误: {e}"
            logger.error(logger_error)
            calendar_db.log_crawler_run(
                source="github",
                status="failed",
                items_found=0,
                items_saved=0,
                error_message=str(e)
            )

    async def generate_recommendations_for_all_users(self):
        """为所有用户生成推荐"""
        logger.info("开始生成推荐")
        
        # 这里需要遍历所有用户
        # 注意: 实际实现中需要从用户表中获取用户列表
        # 这里只是示例
        logger.info("推荐生成完成")

    def shutdown(self):
        """关闭后台任务"""
        self.scheduler.shutdown()
        logger.info("Background tasks stopped")


# 全局实例
background_manager = BackgroundTaskManager()
```

---

## 7. 集成到主应用

在 `main.py` 中添加：

```python
from routes import profile_router, recommendations_router
from services.background_tasks import background_manager

# 在 app.include_router 部分添加：
app.include_router(profile_router.router)
app.include_router(recommendations_router.router)

# 在 lifespan 中启动后台任务：
@asynccontextmanager
async def lifespan(app: FastAPI):
    calendar_db.init_db()
    logger.info("Calendar DB initialised")
    
    # 启动后台任务
    background_manager.start()
    
    if await is_available():
        logger.info("Ollama is reachable at startup")
    else:
        logger.warning("Ollama is NOT reachable — start 'ollama serve' before sending requests")
    
    yield
    
    # 关闭后台任务
    background_manager.shutdown()
```

---

## 8. 环境变量配置

在 `.env` 或 `config.py` 中添加：

```python
# GitHub API Token (可选，用于提高 API 速率限制)
GITHUB_API_TOKEN = os.getenv("GITHUB_API_TOKEN", "")

# Twitter Bearer Token (可选)
TWITTER_BEARER_TOKEN = os.getenv("TWITTER_BEARER_TOKEN", "")

# 爬虫配置
ARXIV_FETCH_LIMIT = int(os.getenv("ARXIV_FETCH_LIMIT", "50"))
GITHUB_FETCH_LIMIT = int(os.getenv("GITHUB_FETCH_LIMIT", "50"))
TWITTER_FETCH_LIMIT = int(os.getenv("TWITTER_FETCH_LIMIT", "20"))
```

---

## 9. API 端点参考

### 用户画像管理

```
# 添加兴趣
POST /profile/interests
{
  "category": "research",
  "tag": "PyTorch",
  "keywords": ["deep learning", "neural network", "pytorch"],
  "weight": 1.0
}

# 获取兴趣
GET /profile/interests?category=research

# 更新兴趣
PUT /profile/interests/1
{
  "weight": 0.8
}

# 删除兴趣
DELETE /profile/interests/1

# 获取画像摘要
GET /profile/summary
```

### 推荐内容

```
# 获取推荐列表
GET /recommendations/feed?unread_only=true&limit=20

# 获取内容详情
GET /recommendations/42

# 标记已读
POST /recommendations/42/read

# 收藏内容
POST /recommendations/42/save

# 获取统计
GET /recommendations/stats/summary
```

---

## 10. 工作流程示例

```
┌─────────────────────────────────────┐
│ 1. 用户设置兴趣标签                  │
│    POST /profile/interests          │
└────────────┬────────────────────────┘
             │
             ▼
┌─────────────────────────────────────┐
│ 2. 后台爬虫定时运行                  │
│    - arXiv 搜索相关论文              │
│    - GitHub 搜索相关项目             │
│    - 保存到数据库                    │
└────────────┬────────────────────────┘
             │
             ▼
┌─────────────────────────────────────┐
│ 3. 推荐引擎计算相关度                │
│    - 关键词匹配                      │
│    - 权重加权                        │
│    - 排序和筛选                      │
└────────────┬────────────────────────┘
             │
             ▼
┌─────────────────────────────────────┐
│ 4. 生成推荐记录                      │
│    保存到 user_recommendations       │
└────────────┬────────────────────────┘
             │
             ▼
┌─────────────────────────────────────┐
│ 5. 用户查看推荐                      │
│    GET /recommendations/feed        │
└────────────┬────────────────────────┘
             │
             ▼
┌─────────────────────────────────────┐
│ 6. 用户交互（标记已读、收藏等）      │
│    POST /recommendations/{id}/read  │
└─────────────────────────────────────┘
```

---

## 总结

这个推荐系统的核心是：
1. **用户画像** → 记录用户的兴趣和偏好
2. **内容爬取** → 从多个来源收集内容
3. **相关度计算** → 基于关键词匹配
4. **智能排序** → 将最相关的内容推荐给用户
5. **用户反馈** → 记录用户的交互行为

通过这个系统，用户可以发现与自己兴趣相关的最新研究成果和技术项目。
