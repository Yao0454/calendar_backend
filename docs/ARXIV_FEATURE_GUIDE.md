# arXiv 日报功能开发指南

## 📋 功能概述

开发一个 arXiv 日报系统，每天自动抓取最新论文，用大模型生成日报摘要，用户可以定制推送时间、数量和领域。

### 功能清单
- ✅ 定时任务：每天定时抓取 arXiv 论文
- ✅ 大模型生成日报摘要
- ✅ 论文和日报存储到数据库
- ✅ 用户偏好设置：推送时间、数量、领域
- ✅ 下载接口：日报和论文原文下载
- ✅ 推送通知（可选）

---

## 🏗️ 架构设计

### 数据结构

```
用户的偏好设置（preferences）
  ├── push_time: str (HH:MM 格式，如 "09:00")
  ├── paper_count: int (每天推荐多少篇，如 5)
  └── categories: list[str] (领域，如 ["cs.AI", "cs.CV"])

论文数据库表（papers）
  ├── id: int
  ├── user_id: str (为了支持用户自定义领域)
  ├── arxiv_id: str (唯一标识，如 "2501.12345")
  ├── title: str
  ├── authors: str
  ├── abstract: str
  ├── pdf_url: str
  ├── category: str (如 "cs.AI")
  ├── published_date: str (YYYY-MM-DD)
  ├── paper_content: BLOB (PDF 转文本，存储在 DB)
  ├── created_at: str
  └── updated_at: str

日报数据库表（daily_reports）
  ├── id: int
  ├── user_id: str
  ├── report_date: str (YYYY-MM-DD，日报的日期)
  ├── summary: str (日报摘要，大模型生成)
  ├── paper_ids: str (JSON，包含的论文 IDs)
  ├── html_content: str (HTML 格式的日报，支持富文本)
  ├── pdf_path: str (存储位置，如 data/reports/user123/2025-01-25.pdf)
  ├── created_at: str
  └── updated_at: str
```

### 模块结构

```
calendar_backend/
├── services/
│   ├── arxiv_fetcher.py          ← 获取 arXiv 论文
│   ├── report_generator.py       ← 生成日报（使用大模型）
│   ├── file_storage.py           ← 文件存储和下载
│   └── scheduler.py              ← 定时任务调度
│
├── routes/
│   └── arxiv_router.py           ← arXiv 日报相关接口
│
├── data/
│   ├── calendar_db.py            ← 现有数据库，添加新表
│   └── reports/                  ← 存储生成的日报文件
│       └── {user_id}/
│           ├── 2025-01-25.pdf
│           └── 2025-01-25.html
│
└── models.py                     ← 添加新的数据模型
```

---

## 📊 数据库设计

### Step 1: 修改 `data/calendar_db.py`

添加 3 个新函数和新表定义：

```python
# 在 init_db() 中添加新表
def init_db() -> None:
    # ... 现有的 events 和 todos 表 ...
    
    with _conn() as c:
        c.executescript("""
            -- 用户的 arXiv 偏好设置
            CREATE TABLE IF NOT EXISTS arxiv_preferences (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id         TEXT    NOT NULL UNIQUE,
                push_time       TEXT    DEFAULT '09:00',  -- HH:MM 格式
                paper_count     INTEGER DEFAULT 5,        -- 每天推荐多少篇
                categories      TEXT    NOT NULL,         -- JSON: ["cs.AI", "cs.CV"]
                is_enabled      INTEGER DEFAULT 1,        -- 是否启用推送
                created_at      TEXT    NOT NULL,
                updated_at      TEXT    NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_arxiv_pref_user ON arxiv_preferences(user_id);
            
            -- 论文数据
            CREATE TABLE IF NOT EXISTS papers (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                arxiv_id        TEXT    NOT NULL UNIQUE,  -- arXiv 唯一 ID
                user_id         TEXT,                     -- 如果 NULL 表示全局论文，如果有值表示用户已保存
                title           TEXT    NOT NULL,
                authors         TEXT    NOT NULL,         -- JSON 格式
                abstract        TEXT,
                pdf_url         TEXT,
                category        TEXT    NOT NULL,         -- cs.AI, cs.CV 等
                published_date  TEXT    NOT NULL,         -- YYYY-MM-DD
                paper_text      TEXT,                     -- PDF 转文本内容
                created_at      TEXT    NOT NULL,
                updated_at      TEXT    NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_papers_arxiv ON papers(arxiv_id);
            CREATE INDEX IF NOT EXISTS idx_papers_user ON papers(user_id);
            CREATE INDEX IF NOT EXISTS idx_papers_date ON papers(published_date);
            
            -- 日报记录
            CREATE TABLE IF NOT EXISTS daily_reports (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id         TEXT    NOT NULL,
                report_date     TEXT    NOT NULL,         -- YYYY-MM-DD
                summary         TEXT    NOT NULL,         -- 日报摘要
                paper_ids       TEXT    NOT NULL,         -- JSON: [1, 2, 3, ...]
                html_content    TEXT,                     -- HTML 格式日报
                pdf_filename    TEXT,                     -- 存储文件名
                download_count  INTEGER DEFAULT 0,        -- 下载次数统计
                created_at      TEXT    NOT NULL,
                updated_at      TEXT    NOT NULL,
                UNIQUE(user_id, report_date)
            );
            CREATE INDEX IF NOT EXISTS idx_reports_user ON daily_reports(user_id);
            CREATE INDEX IF NOT EXISTS idx_reports_date ON daily_reports(report_date);
        """)

# 用户偏好设置相关函数
def get_arxiv_preference(user_id: str) -> dict | None:
    """获取用户的 arXiv 偏好设置"""
    with _conn() as c:
        row = c.execute(
            "SELECT * FROM arxiv_preferences WHERE user_id=?",
            (user_id,)
        ).fetchone()
        return dict(row) if row else None

def create_or_update_arxiv_preference(user_id: str, data: dict) -> dict:
    """创建或更新用户偏好设置"""
    now = _now()
    with _conn() as c:
        existing = c.execute(
            "SELECT id FROM arxiv_preferences WHERE user_id=?",
            (user_id,)
        ).fetchone()
        
        if existing:
            # 更新
            c.execute(
                """UPDATE arxiv_preferences 
                   SET push_time=?, paper_count=?, categories=?, is_enabled=?, updated_at=?
                   WHERE user_id=?""",
                (
                    data.get("push_time", "09:00"),
                    data.get("paper_count", 5),
                    json.dumps(data.get("categories", [])),
                    1 if data.get("is_enabled", True) else 0,
                    now,
                    user_id
                )
            )
        else:
            # 新建
            c.execute(
                """INSERT INTO arxiv_preferences(user_id, push_time, paper_count, categories, is_enabled, created_at, updated_at)
                   VALUES(?, ?, ?, ?, ?, ?, ?)""",
                (
                    user_id,
                    data.get("push_time", "09:00"),
                    data.get("paper_count", 5),
                    json.dumps(data.get("categories", [])),
                    1 if data.get("is_enabled", True) else 0,
                    now,
                    now
                )
            )
        
        row = c.execute(
            "SELECT * FROM arxiv_preferences WHERE user_id=?",
            (user_id,)
        ).fetchone()
        return dict(row) if row else {}

# 论文相关函数
def create_or_update_paper(data: dict) -> dict:
    """创建或更新论文记录"""
    now = _now()
    with _conn() as c:
        existing = c.execute(
            "SELECT id FROM papers WHERE arxiv_id=?",
            (data["arxiv_id"],)
        ).fetchone()
        
        if existing:
            c.execute(
                """UPDATE papers 
                   SET title=?, authors=?, abstract=?, pdf_url=?, category=?, 
                       paper_text=?, updated_at=?
                   WHERE arxiv_id=?""",
                (
                    data.get("title"),
                    data.get("authors"),
                    data.get("abstract"),
                    data.get("pdf_url"),
                    data.get("category"),
                    data.get("paper_text"),
                    now,
                    data["arxiv_id"]
                )
            )
        else:
            c.execute(
                """INSERT INTO papers(arxiv_id, user_id, title, authors, abstract, pdf_url, 
                                     category, published_date, paper_text, created_at, updated_at)
                   VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    data["arxiv_id"],
                    data.get("user_id"),
                    data.get("title"),
                    json.dumps(data.get("authors", [])),
                    data.get("abstract"),
                    data.get("pdf_url"),
                    data.get("category"),
                    data.get("published_date"),
                    data.get("paper_text"),
                    now,
                    now
                )
            )
        
        row = c.execute(
            "SELECT * FROM papers WHERE arxiv_id=?",
            (data["arxiv_id"],)
        ).fetchone()
        return dict(row) if row else {}

def get_papers_by_date_and_category(date: str, categories: list[str]) -> list[dict]:
    """根据日期和领域获取论文"""
    with _conn() as c:
        placeholders = ",".join("?" * len(categories))
        rows = c.execute(
            f"SELECT * FROM papers WHERE published_date=? AND category IN ({placeholders})",
            [date] + categories
        ).fetchall()
        return [dict(r) for r in rows]

# 日报相关函数
def create_daily_report(user_id: str, data: dict) -> dict:
    """创建日报"""
    now = _now()
    with _conn() as c:
        cur = c.execute(
            """INSERT INTO daily_reports(user_id, report_date, summary, paper_ids, html_content, pdf_filename, created_at, updated_at)
               VALUES(?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                user_id,
                data["report_date"],
                data["summary"],
                json.dumps(data.get("paper_ids", [])),
                data.get("html_content"),
                data.get("pdf_filename"),
                now,
                now
            )
        )
        return dict(c.execute(
            "SELECT * FROM daily_reports WHERE id=?",
            (cur.lastrowid,)
        ).fetchone())

def get_daily_report(user_id: str, report_date: str) -> dict | None:
    """获取特定日期的日报"""
    with _conn() as c:
        row = c.execute(
            "SELECT * FROM daily_reports WHERE user_id=? AND report_date=?",
            (user_id, report_date)
        ).fetchone()
        return dict(row) if row else None

def get_daily_reports_list(user_id: str, limit: int = 30) -> list[dict]:
    """获取用户的日报列表"""
    with _conn() as c:
        rows = c.execute(
            "SELECT * FROM daily_reports WHERE user_id=? ORDER BY report_date DESC LIMIT ?",
            (user_id, limit)
        ).fetchall()
        return [dict(r) for r in rows]

def increment_report_download(report_id: int) -> None:
    """增加日报下载计数"""
    with _conn() as c:
        c.execute(
            "UPDATE daily_reports SET download_count = download_count + 1 WHERE id=?",
            (report_id,)
        )
```

**不要忘记在文件顶部导入 json！**

```python
import json
```

---

## 🤖 大模型相关服务

### Step 2: 创建 `services/arxiv_fetcher.py`

```python
"""从 arXiv 获取论文"""
import logging
import feedparser
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

# arXiv API 端点
ARXIV_API_BASE = "http://export.arxiv.org/api/query"

# 支持的领域映射
ARXIV_CATEGORIES = {
    "cs.AI": "Artificial Intelligence",
    "cs.CV": "Computer Vision",
    "cs.LG": "Machine Learning",
    "cs.NLP": "Natural Language Processing",
    "cs.DB": "Databases",
    "stat.ML": "Machine Learning (Statistics)",
    "physics.astro-ph": "Astrophysics",
    "math.ST": "Statistics Theory",
}

async def fetch_papers_by_date_and_categories(
    date: str,  # YYYY-MM-DD
    categories: list[str],
    limit: int = 50
) -> list[dict]:
    """
    从 arXiv 获取特定日期和领域的论文
    
    Args:
        date: 发布日期 (YYYY-MM-DD)
        categories: 领域列表 (如 ["cs.AI", "cs.CV"])
        limit: 返回的最大论文数
    
    Returns:
        论文列表，每个论文包含 title, authors, abstract, arxiv_id, pdf_url, category, published_date
    """
    import httpx
    
    papers = []
    
    for category in categories:
        # arXiv API 查询格式
        # submittedDate:[DATE0000000000 TO DATE2359999999]
        date_obj = datetime.strptime(date, "%Y-%m-%d")
        start_time = int(date_obj.timestamp() * 1000)
        end_time = int((date_obj + timedelta(days=1)).timestamp() * 1000)
        
        query = f'cat:{category} AND submittedDate:[{start_time} TO {end_time}]'
        params = {
            'search_query': query,
            'start': 0,
            'max_results': limit,
            'sortBy': 'submittedDate',
            'sortOrder': 'descending'
        }
        
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.get(ARXIV_API_BASE, params=params)
                response.raise_for_status()
                
            # 解析 RSS/Atom feed
            feed = feedparser.parse(response.text)
            
            for entry in feed.entries:
                paper = {
                    'arxiv_id': entry.id.split('/abs/')[-1],  # 如 "2501.12345"
                    'title': entry.title,
                    'authors': [author.name for author in entry.authors],
                    'abstract': entry.summary,
                    'category': category,
                    'published_date': date,
                    'pdf_url': entry.id.replace('abs', 'pdf') + '.pdf',  # arXiv PDF URL
                }
                papers.append(paper)
                
        except Exception as e:
            logger.error(f"Failed to fetch papers for category {category}: {e}")
            continue
    
    return papers[:limit]


async def download_paper_text(pdf_url: str) -> str:
    """
    下载论文 PDF 并提取文本
    
    注意：这是一个简化版本，实际需要 PDF 解析库
    """
    import httpx
    from services.file_handler import extract_pdf_text
    
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.get(pdf_url)
            response.raise_for_status()
        
        # 保存为临时文件然后提取文本
        text = extract_pdf_text(response.content)
        return text[:5000]  # 只保留前 5000 个字符
        
    except Exception as e:
        logger.error(f"Failed to download paper from {pdf_url}: {e}")
        return ""
```

### Step 3: 创建 `services/report_generator.py`

```python
"""生成 arXiv 日报（使用大模型）"""
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

async def generate_daily_report(
    user_id: str,
    papers: list[dict],
    report_date: str
) -> dict:
    """
    根据论文列表生成日报
    
    Args:
        user_id: 用户 ID
        papers: 论文列表，每个包含 title, abstract, authors 等字段
        report_date: 日报日期 (YYYY-MM-DD)
    
    Returns:
        包含 summary 和 paper_ids 的字典
    """
    
    # 构建论文信息
    papers_info = []
    for paper in papers:
        info = f"""
标题：{paper['title']}
作者：{', '.join(paper.get('authors', []))}
摘要：{paper['abstract'][:500]}
...
"""
        papers_info.append(info)
    
    # 构建用户消息
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
        
        logger.info(f"Generated report for user {user_id} on {report_date}")
        
        # 生成 HTML 版本
        html_content = _markdown_to_html(summary)
        
        return {
            'summary': summary,
            'html_content': html_content,
            'paper_ids': [p.get('id') for p in papers if p.get('id')]
        }
        
    except Exception as e:
        logger.error(f"Failed to generate report: {e}")
        raise


def _markdown_to_html(markdown_text: str) -> str:
    """将 Markdown 转换为 HTML（简单版本）"""
    import html
    
    text = html.escape(markdown_text)
    
    # 简单的 Markdown 转 HTML
    # 实际项目中应使用 markdown2 或 mistune 库
    lines = text.split('\n')
    html_lines = []
    
    for line in lines:
        if line.startswith('# '):
            html_lines.append(f'<h1>{line[2:]}</h1>')
        elif line.startswith('## '):
            html_lines.append(f'<h2>{line[3:]}</h2>')
        elif line.startswith('- '):
            html_lines.append(f'<li>{line[2:]}</li>')
        elif line.strip() == '':
            html_lines.append('<br>')
        else:
            html_lines.append(f'<p>{line}</p>')
    
    return '\n'.join(html_lines)


async def generate_pdf_report(summary: str, user_id: str, report_date: str) -> str:
    """
    将日报摘要转换为 PDF（可选）
    
    需要安装：pip install reportlab
    """
    from reportlab.pdfgen import canvas
    from reportlab.lib.pagesizes import A4
    from pathlib import Path
    
    # 创建用户报告目录
    report_dir = Path(f"data/reports/{user_id}")
    report_dir.mkdir(parents=True, exist_ok=True)
    
    pdf_path = report_dir / f"{report_date}.pdf"
    
    try:
        c = canvas.Canvas(str(pdf_path), pagesize=A4)
        c.drawString(100, 800, f"arXiv 学术日报 - {report_date}")
        
        # 简单地写入摘要（实际需要更复杂的排版）
        y = 750
        for line in summary.split('\n'):
            if y < 50:
                c.showPage()
                y = 750
            c.drawString(100, y, line[:80])
            y -= 20
        
        c.save()
        logger.info(f"Generated PDF report at {pdf_path}")
        return str(pdf_path)
        
    except Exception as e:
        logger.error(f"Failed to generate PDF: {e}")
        return ""
```

### Step 4: 创建 `services/scheduler.py`

```python
"""定时任务调度 - 每天生成日报"""
import logging
import asyncio
from datetime import datetime, time
from apscheduler.schedulers.background import BackgroundScheduler

logger = logging.getLogger(__name__)

# 全局定时器
_scheduler = None

def init_scheduler():
    """初始化定时器"""
    global _scheduler
    _scheduler = BackgroundScheduler()
    _scheduler.start()
    logger.info("Scheduler initialized")

def shutdown_scheduler():
    """关闭定时器"""
    global _scheduler
    if _scheduler:
        _scheduler.shutdown()

def add_daily_report_job(user_id: str, push_time: str):
    """
    为用户添加每日生成日报的任务
    
    Args:
        user_id: 用户 ID
        push_time: 推送时间，格式 "HH:MM"
    """
    from services.report_generator import generate_daily_report
    from services.arxiv_fetcher import fetch_papers_by_date_and_categories
    from data import calendar_db
    
    async def job():
        try:
            # 获取用户偏好
            pref = calendar_db.get_arxiv_preference(user_id)
            if not pref or not pref.get('is_enabled'):
                return
            
            import json
            categories = json.loads(pref['categories'])
            paper_count = pref['paper_count']
            
            # 获取今天的论文
            from datetime import date
            today = str(date.today())
            papers = await fetch_papers_by_date_and_categories(
                today,
                categories,
                limit=paper_count
            )
            
            if not papers:
                logger.warning(f"No papers found for user {user_id}")
                return
            
            # 生成日报
            report = await generate_daily_report(user_id, papers, today)
            
            # 保存到数据库
            calendar_db.create_daily_report(user_id, {
                'report_date': today,
                'summary': report['summary'],
                'paper_ids': report.get('paper_ids', []),
                'html_content': report.get('html_content'),
            })
            
            logger.info(f"Daily report generated for user {user_id} on {today}")
            
        except Exception as e:
            logger.error(f"Failed to generate report for user {user_id}: {e}")
    
    # 解析推送时间
    hour, minute = map(int, push_time.split(':'))
    
    # 添加定时任务
    global _scheduler
    if _scheduler:
        job_id = f"daily_report_{user_id}"
        
        # 移除旧任务（如果存在）
        if _scheduler.get_job(job_id):
            _scheduler.remove_job(job_id)
        
        # 添加新任务
        _scheduler.add_job(
            func=lambda: asyncio.run(job()),
            trigger="cron",
            hour=hour,
            minute=minute,
            id=job_id,
            name=f"Daily report for {user_id}",
            replace_existing=True
        )
        logger.info(f"Scheduled daily report for user {user_id} at {push_time}")

def remove_daily_report_job(user_id: str):
    """移除用户的定时任务"""
    global _scheduler
    if _scheduler:
        job_id = f"daily_report_{user_id}"
        if _scheduler.get_job(job_id):
            _scheduler.remove_job(job_id)
            logger.info(f"Removed scheduled job for user {user_id}")
```

---

## 🌐 API 接口

### Step 5: 创建 `routes/arxiv_router.py`

```python
"""arXiv 日报相关接口"""
import json
from datetime import date as date_class
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from auth.deps import get_current_session
from auth.models import SessionPrincipal
from data import calendar_db
from services import arxiv_fetcher, report_generator, scheduler

router = APIRouter(prefix="/arxiv", tags=["arxiv"])

# ── 数据模型 ──────────────────────────────────────────────────────────────────

class ArxivPreferenceIn(BaseModel):
    """用户偏好设置"""
    push_time: str = "09:00"  # HH:MM 格式
    paper_count: int = 5
    categories: list[str]  # ["cs.AI", "cs.CV", ...]
    is_enabled: bool = True

class DailyReportResponse(BaseModel):
    """日报响应"""
    id: int
    report_date: str
    summary: str
    paper_ids: list[int]
    download_count: int

# ── 偏好设置相关接口 ────────────────────────────────────────────────────────────

@router.get("/preferences")
def get_preferences(session: SessionPrincipal = Depends(get_current_session)):
    """获取用户的 arXiv 偏好设置"""
    pref = calendar_db.get_arxiv_preference(session.user_id)
    if not pref:
        return {
            "push_time": "09:00",
            "paper_count": 5,
            "categories": [],
            "is_enabled": False
        }
    
    # 解析 JSON 字段
    pref['categories'] = json.loads(pref.get('categories', '[]'))
    return pref

@router.post("/preferences")
def update_preferences(
    body: ArxivPreferenceIn,
    session: SessionPrincipal = Depends(get_current_session)
):
    """更新用户的 arXiv 偏好设置"""
    pref = calendar_db.create_or_update_arxiv_preference(
        session.user_id,
        body.model_dump()
    )
    
    # 如果启用推送，添加定时任务
    if body.is_enabled:
        scheduler.add_daily_report_job(session.user_id, body.push_time)
    else:
        scheduler.remove_daily_report_job(session.user_id)
    
    pref['categories'] = json.loads(pref.get('categories', '[]'))
    return pref

# ── 日报相关接口 ────────────────────────────────────────────────────────────

@router.get("/reports")
def get_reports_list(
    limit: int = 30,
    session: SessionPrincipal = Depends(get_current_session)
):
    """获取用户的日报列表"""
    reports = calendar_db.get_daily_reports_list(session.user_id, limit)
    
    # 解析 paper_ids 字段
    for report in reports:
        report['paper_ids'] = json.loads(report.get('paper_ids', '[]'))
    
    return reports

@router.get("/reports/{report_date}")
def get_report(
    report_date: str,  # YYYY-MM-DD
    session: SessionPrincipal = Depends(get_current_session)
):
    """获取特定日期的日报"""
    report = calendar_db.get_daily_report(session.user_id, report_date)
    if not report:
        raise HTTPException(status_code=404, detail="日报不存在")
    
    report['paper_ids'] = json.loads(report.get('paper_ids', '[]'))
    return report

@router.get("/reports/{report_date}/download")
async def download_report(
    report_date: str,
    session: SessionPrincipal = Depends(get_current_session)
):
    """下载日报（PDF 或 HTML）"""
    from fastapi.responses import FileResponse, HTMLResponse
    
    report = calendar_db.get_daily_report(session.user_id, report_date)
    if not report:
        raise HTTPException(status_code=404, detail="日报不存在")
    
    # 增加下载计数
    calendar_db.increment_report_download(report['id'])
    
    # 返回 HTML 版本（或 PDF，取决于你的实现）
    if report.get('html_content'):
        return HTMLResponse(content=report['html_content'])
    else:
        return {"summary": report['summary']}

@router.get("/reports/{report_date}/download-papers")
async def download_papers_in_report(
    report_date: str,
    session: SessionPrincipal = Depends(get_current_session)
):
    """下载日报中包含的所有论文原文"""
    import json
    from pathlib import Path
    
    report = calendar_db.get_daily_report(session.user_id, report_date)
    if not report:
        raise HTTPException(status_code=404, detail="日报不存在")
    
    paper_ids = json.loads(report.get('paper_ids', '[]'))
    
    # 实际项目中，这里应该返回一个 ZIP 文件，包含所有 PDF
    # 现在简化为返回论文列表
    return {
        "report_date": report_date,
        "paper_count": len(paper_ids),
        "papers": paper_ids,
        "note": "实现 ZIP 下载功能"
    }

# ── 管理接口（可选） ────────────────────────────────────────────────────────

@router.post("/manual-generate-report")
async def manual_generate_report(
    report_date: str = None,
    session: SessionPrincipal = Depends(get_current_session)
):
    """手动为用户生成日报（用于测试）"""
    if not report_date:
        from datetime import date
        report_date = str(date.today())
    
    # 获取用户偏好
    pref = calendar_db.get_arxiv_preference(session.user_id)
    if not pref:
        raise HTTPException(status_code=400, detail="请先设置偏好")
    
    import json
    categories = json.loads(pref['categories'])
    paper_count = pref['paper_count']
    
    # 获取论文
    papers = await arxiv_fetcher.fetch_papers_by_date_and_categories(
        report_date,
        categories,
        limit=paper_count
    )
    
    if not papers:
        raise HTTPException(status_code=404, detail="未找到论文")
    
    # 生成日报
    report = await report_generator.generate_daily_report(
        session.user_id,
        papers,
        report_date
    )
    
    # 保存
    saved_report = calendar_db.create_daily_report(session.user_id, {
        'report_date': report_date,
        'summary': report['summary'],
        'paper_ids': report.get('paper_ids', []),
        'html_content': report.get('html_content'),
    })
    
    return saved_report
```

---

## 🔧 集成到主应用

### Step 6: 修改 `main.py`

```python
# 在 main.py 顶部添加
from services import scheduler
from routes import arxiv_router

# 在 lifespan 中添加
@asynccontextmanager
async def lifespan(app: FastAPI):
    calendar_db.init_db()
    logger.info("Calendar DB initialised")
    
    # ← 新增：初始化定时器
    scheduler.init_scheduler()
    
    if await is_available():
        logger.info("Ollama is reachable at startup")
    else:
        logger.warning("Ollama is NOT reachable...")
    
    yield
    
    # ← 新增：关闭定时器
    scheduler.shutdown_scheduler()

# 在 app.include_router 中添加
app.include_router(items_router.router)
app.include_router(auth_router.router)
app.include_router(arxiv_router.router)  # ← 新增
```

---

## 📦 依赖管理

### Step 7: 修改 `requirements.txt`

```
fastapi>=0.111.0
uvicorn[standard]>=0.29.0
httpx>=0.27.0
Pillow>=10.0.0
pymupdf>=1.24.0
python-multipart>=0.0.9
pydantic>=2.0.0
bcrypt>=4.0.0

# 新增依赖
feedparser>=6.0.10          # 解析 arXiv RSS feed
apscheduler>=3.10.0         # 定时任务调度
reportlab>=4.0.0            # PDF 生成（可选）
markdown2>=2.4.9            # Markdown 转 HTML
```

然后运行：
```bash
pip install -r requirements.txt
```

---

## 🧪 测试流程

### 1. 创建用户并设置偏好

```bash
# 注册用户
curl -X POST http://localhost:5522/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "username": "arxiv_user",
    "password": "password123"
  }'

# 登录
curl -X POST http://localhost:5522/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "username": "arxiv_user",
    "password": "password123"
  }'
# 获取 session_id

# 设置偏好
curl -X POST http://localhost:5522/arxiv/preferences \
  -H "Authorization: Bearer {session_id}" \
  -H "Content-Type: application/json" \
  -d '{
    "push_time": "09:00",
    "paper_count": 5,
    "categories": ["cs.AI", "cs.CV"],
    "is_enabled": true
  }'
```

### 2. 手动测试生成日报

```bash
curl -X POST http://localhost:5522/arxiv/manual-generate-report \
  -H "Authorization: Bearer {session_id}" \
  -H "Content-Type: application/json" \
  -d '{"report_date": "2025-01-25"}'
```

### 3. 获取日报列表和下载

```bash
# 获取日报列表
curl http://localhost:5522/arxiv/reports \
  -H "Authorization: Bearer {session_id}"

# 获取特定日报
curl http://localhost:5522/arxiv/reports/2025-01-25 \
  -H "Authorization: Bearer {session_id}"

# 下载日报
curl http://localhost:5522/arxiv/reports/2025-01-25/download \
  -H "Authorization: Bearer {session_id}"
```

---

## 📋 开发 Checklist

### 数据库层 ✅
- [ ] 在 `data/calendar_db.py` 中添加 3 个新表（arxiv_preferences, papers, daily_reports）
- [ ] 添加对应的 CRUD 函数
- [ ] 测试数据库操作

### 服务层 ✅
- [ ] 创建 `services/arxiv_fetcher.py` - 获取论文
- [ ] 创建 `services/report_generator.py` - 生成日报
- [ ] 创建 `services/scheduler.py` - 定时任务
- [ ] 测试各个服务函数

### 路由层 ✅
- [ ] 创建 `routes/arxiv_router.py` - 所有 API 端点
- [ ] 实现偏好设置接口
- [ ] 实现日报获取和下载接口
- [ ] 测试所有端点

### 集成 ✅
- [ ] 修改 `main.py` 注册路由和定时器
- [ ] 修改 `requirements.txt` 添加依赖
- [ ] 修改 `models.py` 添加新的 Pydantic 模型（可选）

### 用户隔离 ✅
- [ ] 所有查询都有 `WHERE user_id = ?`
- [ ] 路由层都使用 `Depends(get_current_session)`
- [ ] 删除/更新操作都验证所有权

### 测试 ✅
- [ ] 单元测试：各个服务函数
- [ ] 集成测试：完整流程
- [ ] 手动测试：API 端点

---

## 🚨 常见问题

### Q1: arXiv API 速率限制？
A: arXiv API 没有严格的速率限制，但建议不要同时发送过多请求。可以添加延迟：
```python
import asyncio
await asyncio.sleep(1)  # 请求之间延迟 1 秒
```

### Q2: PDF 下载太慢怎么办？
A: 可以使用后台任务或消息队列（如 Celery）异步处理。简化版本中可以只存储 PDF 链接，让客户端直接从 arXiv 下载。

### Q3: 存储空间不足怎么办？
A: 可以选择只存储摘要，不下载完整论文。或者定期清理旧数据：
```python
def cleanup_old_papers(days=30):
    """删除 30 天前的论文"""
    from datetime import datetime, timedelta
    cutoff_date = (datetime.now() - timedelta(days=days)).isoformat()
    with _conn() as c:
        c.execute("DELETE FROM papers WHERE created_at < ?", (cutoff_date,))
```

### Q4: 如何支持多个用户的并发请求？
A: FastAPI 默认是异步的，已经支持并发。定时任务也是异步的（使用 APScheduler）。

---

## 📚 后续优化方向

1. **前端集成**：在客户端 UI 添加偏好设置页面和日报查看器
2. **推送通知**：集成邮件或推送通知服务（如 Firebase）
3. **论文收藏**：让用户收藏、标记和分享论文
4. **搜索功能**：添加论文搜索和过滤功能
5. **多语言支持**：生成多语言日报
6. **社区功能**：用户间分享日报和讨论
7. **性能优化**：缓存常用查询，使用 Redis
8. **监控和统计**：记录用户行为，生成使用统计

---

## 📖 总结

按照以下步骤开发：

1. **数据库** (Step 1) → 修改 `data/calendar_db.py`
2. **获取论文** (Step 2) → 创建 `services/arxiv_fetcher.py`
3. **生成日报** (Step 3) → 创建 `services/report_generator.py`
4. **定时任务** (Step 4) → 创建 `services/scheduler.py`
5. **API 接口** (Step 5) → 创建 `routes/arxiv_router.py`
6. **集成主应用** (Step 6) → 修改 `main.py`
7. **安装依赖** (Step 7) → 修改 `requirements.txt`
8. **测试** → 按照测试流程验证

祝你开发顺利！🚀
