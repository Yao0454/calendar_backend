# arXiv 智能日报功能开发指南（修订版）

## 📋 功能概述（重新定义）

开发一个**AI 智能驱动的学术日报系统**，大模型通过分析用户的日程、待办、历史行为等信息，智能推断用户的学习兴趣，然后**主动调用 arXiv 工具**搜索相关论文，生成个性化日报。

### 核心理念
**不是用户告诉系统想要什么，而是系统通过 AI 推理来主动发现用户需要什么。**

### 功能对比

```
❌ 旧方案（被动）
用户设置 → 偏好（cs.AI, cs.CV）→ 系统按固定分类查论文 → 生成日报

✅ 新方案（主动智能）
用户的日程/待办/历史
    ↓
AI 分析（你要分析什么？）
    ↓
AI 推理出用户兴趣（AI 决定要搜什么）
    ↓
AI 调用 arXiv 工具搜索论文（AI 做的决策）
    ↓
AI 生成个性化日报（结合用户上下文）
```

---

## 🏗️ 重新设计的架构

### 数据结构

```
用户偏好设置（preferences） - 简化版
  ├── enable_daily_report: bool (是否启用日报)
  ├── report_time: str (什么时候推送，如 "09:00")
  └── max_papers: int (每份日报最多多少篇论文)

日程事件表（events）- 已有，用于 AI 分析
  ├── title: str
  ├── date: str
  ├── notes: str
  └── ...

待办事项表（todos）- 已有，用于 AI 分析
  ├── title: str
  ├── deadline: str
  ├── notes: str
  └── ...

论文表（papers）- 动态存储，不仅仅是预设领域
  ├── id: int
  ├── arxiv_id: str (唯一标识)
  ├── title: str
  ├── authors: str (JSON)
  ├── abstract: str
  ├── pdf_url: str
  ├── category: str (cs.AI, cs.CV 等)
  ├── relevance_reason: str (AI 为什么推荐这篇论文)
  ├── published_date: str
  ├── paper_text: TEXT (PDF 转文本)
  ├── created_at: str
  └── updated_at: str

日报表（daily_reports）
  ├── id: int
  ├── user_id: str
  ├── report_date: str
  ├── analysis_context: str (AI 分析的用户兴趣是什么)
  ├── search_queries: str (AI 决定搜索的关键词和领域，JSON)
  ├── summary: str (日报摘要)
  ├── paper_ids: str (JSON，包含的论文 IDs)
  ├── ai_reasoning: str (AI 的推理过程)
  ├── created_at: str
  └── updated_at: str
```

### 模块结构

```
calendar_backend/
├── services/
│   ├── arxiv_tool.py                 ← AI 可以调用的工具（搜索论文）
│   ├── user_interest_analyzer.py      ← 分析用户兴趣（读取日程/待办）
│   ├── report_generator.py            ← 生成日报（大模型，带工具调用）
│   ├── scheduler.py                   ← 定时任务
│   └── ollama.py                      ← 已有，大模型交互
│
├── routes/
│   └── arxiv_router.py                ← API 接口
│
├── data/
│   ├── calendar_db.py                 ← 数据库（修改：简化偏好、添加新字段）
│   └── reports/                       ← 日报存储
│
└── models.py                          ← 数据模型
```

---

## 🤖 核心流程：AI 如何做决策

### 第 1 步：分析用户兴趣

```
系统获取用户的：
  ├── 最近 7 天的日程（标题、描述、地点等）
  ├── 最近 30 天的待办（标题、优先级、截止日期等）
  ├── 过去 3 个月的日报（看过哪些论文）
  └── 用户的搜索历史（曾搜索过什么关键词）

交给大模型分析：
  "根据这个用户的日程、待办和历史行为，推断出这个用户现在最感兴趣的研究领域和具体话题。"

大模型输出：
  {
    "inferred_interests": [
      {
        "topic": "神经网络加速",
        "confidence": 0.9,
        "reason": "用户最近的待办涉及 GPU 优化，3 个日程与深度学习相关"
      },
      {
        "topic": "知识图谱",
        "confidence": 0.7,
        "reason": "用户过去看过关于 NLP 的论文"
      }
    ],
    "suggested_keywords": ["neural network acceleration", "knowledge graph", "deep learning"],
    "relevant_arxiv_categories": ["cs.AI", "cs.LG", "cs.CV"],
    "search_depth": "moderate"
  }
```

### 第 2 步：AI 调用 arXiv 工具搜索论文

```
大模型在与系统交互时，可以调用工具：

工具 1: search_arxiv(keywords, categories, date_range, limit)
  返回：论文列表（标题、作者、摘要、链接）

工具 2: get_paper_full_text(arxiv_id)
  返回：论文全文（前 5000 字）

大模型的对话流程（伪代码）：
  
  系统提示：
    "你可以使用以下工具来帮助用户找论文：
    - search_arxiv(keywords, categories, date_range, limit)
    - get_paper_full_text(arxiv_id)
    
    基于用户的兴趣分析，搜索相关论文，然后生成日报。"
  
  大模型的思考：
    "用户对神经网络加速感兴趣，我应该搜索这个话题。"
  
  大模型的行动：
    Tool: search_arxiv
    Parameters: {
      "keywords": "neural network acceleration GPU",
      "categories": ["cs.LG", "cs.AI"],
      "date_range": "last_7_days",
      "limit": 10
    }
  
  系统返回：
    [论文列表...]
  
  大模型继续：
    "这 10 篇论文很相关。让我再搜索知识图谱的论文。"
  
  大模型的行动：
    Tool: search_arxiv
    Parameters: {
      "keywords": "knowledge graph neural networks",
      "categories": ["cs.AI", "cs.NLP"],
      "date_range": "last_7_days",
      "limit": 5
    }
  
  系统返回：
    [更多论文...]
  
  大模型最终：
    "好的，我找到了 15 篇高相关性的论文。现在我生成日报..."
```

### 第 3 步：生成个性化日报

```
大模型根据：
  ├── 用户的推断兴趣
  ├── 搜索到的论文
  ├── 用户的日程上下文
  └── 用户的历史行为

生成日报：
  "根据你最近的日程，我看到你在准备关于 GPU 优化的项目。
   今天我为你找到了 3 篇最新的神经网络加速论文和 2 篇知识图谱相关的论文。
   这些都与你的项目高度相关..."
```

---

## 💻 代码设计

### Step 1: 创建 `services/arxiv_tool.py` - AI 可以调用的工具

```python
"""
arXiv 工具 - 供大模型调用来搜索论文
这是一个 Tool Use 的实现
"""
import logging
import json
import feedparser
import httpx
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

ARXIV_API_BASE = "http://export.arxiv.org/api/query"

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

async def search_arxiv(
    keywords: str,
    categories: list[str] = None,
    date_range: str = "last_7_days",
    limit: int = 10
) -> dict:
    """
    在 arXiv 上搜索论文
    
    Args:
        keywords: 搜索关键词
        categories: 分类列表，如 ["cs.AI", "cs.LG"]
        date_range: 时间范围
        limit: 最多返回多少篇
    
    Returns:
        {
            "success": bool,
            "papers": [
                {
                    "arxiv_id": "2501.12345",
                    "title": "...",
                    "authors": [...],
                    "abstract": "...",
                    "pdf_url": "...",
                    "published_date": "2025-01-25",
                    "category": "cs.AI"
                }
            ],
            "total": int,
            "query_used": str
        }
    """
    try:
        # 构建查询
        query_parts = []
        
        # 关键词
        query_parts.append(f'all:"{keywords}"')
        
        # 分类
        if categories:
            cat_query = " OR ".join([f"cat:{cat}" for cat in categories])
            query_parts.append(f"({cat_query})")
        
        # 日期范围
        date_query = _get_date_query(date_range)
        if date_query:
            query_parts.append(date_query)
        
        query = " AND ".join(query_parts)
        
        logger.info(f"Searching arXiv with query: {query}")
        
        params = {
            'search_query': query,
            'start': 0,
            'max_results': min(limit, 50),
            'sortBy': 'submittedDate',
            'sortOrder': 'descending'
        }
        
        async with httpx.AsyncClient(timeout=15) as client:
            response = await client.get(ARXIV_API_BASE, params=params)
            response.raise_for_status()
        
        # 解析结果
        feed = feedparser.parse(response.text)
        papers = []
        
        for entry in feed.entries:
            paper = {
                'arxiv_id': entry.id.split('/abs/')[-1],
                'title': entry.title,
                'authors': [author.name for author in entry.authors],
                'abstract': entry.summary,
                'pdf_url': entry.id.replace('abs', 'pdf') + '.pdf',
                'published_date': datetime.fromisoformat(
                    entry.published.replace('Z', '+00:00')
                ).strftime('%Y-%m-%d'),
                'category': entry.arxiv_primary_category.get('term', 'unknown'),
                'url': entry.id
            }
            papers.append(paper)
        
        return {
            "success": True,
            "papers": papers,
            "total": len(papers),
            "query_used": query,
            "keywords": keywords,
            "categories": categories or []
        }
        
    except Exception as e:
        logger.error(f"Failed to search arXiv: {e}")
        return {
            "success": False,
            "error": str(e),
            "papers": []
        }

def _get_date_query(date_range: str) -> str:
    """生成日期范围查询"""
    now = datetime.now()
    
    if date_range == "last_1_day":
        delta = timedelta(days=1)
    elif date_range == "last_7_days":
        delta = timedelta(days=7)
    elif date_range == "last_30_days":
        delta = timedelta(days=30)
    else:
        return ""
    
    start_date = (now - delta).strftime('%Y%m%d0000')
    end_date = now.strftime('%Y%m%d2359')
    
    return f'submittedDate:[{start_date} TO {end_date}]'

async def get_paper_details(arxiv_id: str) -> dict:
    """获取单篇论文的详细信息"""
    try:
        params = {
            'search_query': f'arxiv:{arxiv_id}',
            'start': 0,
            'max_results': 1
        }
        
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.get(ARXIV_API_BASE, params=params)
            response.raise_for_status()
        
        feed = feedparser.parse(response.text)
        if not feed.entries:
            return {"success": False, "error": "论文未找到"}
        
        entry = feed.entries[0]
        return {
            "success": True,
            "paper": {
                'arxiv_id': entry.id.split('/abs/')[-1],
                'title': entry.title,
                'authors': [author.name for author in entry.authors],
                'abstract': entry.summary,
                'pdf_url': entry.id.replace('abs', 'pdf') + '.pdf',
                'published_date': entry.published,
                'category': entry.arxiv_primary_category.get('term', 'unknown'),
                'url': entry.id
            }
        }
        
    except Exception as e:
        logger.error(f"Failed to get paper details: {e}")
        return {"success": False, "error": str(e)}
```

### Step 2: 创建 `services/user_interest_analyzer.py` - 分析用户兴趣

```python
"""
用户兴趣分析器 - 从日程、待办等推断用户的研究兴趣
"""
import logging
from datetime import datetime, timedelta
from data import calendar_db
from services import ollama

logger = logging.getLogger(__name__)

async def analyze_user_interests(user_id: str) -> dict:
    """
    分析用户的研究兴趣
    
    Returns:
        {
            "inferred_interests": [
                {
                    "topic": "神经网络加速",
                    "confidence": 0.9,
                    "reason": "..."
                }
            ],
            "suggested_search_keywords": ["..."],
            "relevant_categories": ["cs.AI", "cs.LG"],
            "analysis_timestamp": "2025-01-25T10:00:00"
        }
    """
    try:
        # 收集用户数据
        user_data = _collect_user_context(user_id)
        
        # 用大模型分析
        analysis = await _analyze_with_llm(user_data)
        
        logger.info(f"Analyzed interests for user {user_id}: {analysis}")
        return analysis
        
    except Exception as e:
        logger.error(f"Failed to analyze user interests: {e}")
        raise

def _collect_user_context(user_id: str) -> dict:
    """收集用户的日程、待办等信息"""
    
    # 获取最近 7 天的日程
    all_events = calendar_db.get_events(user_id)
    recent_events = [
        e for e in all_events
        if e.get('date') and 
        datetime.strptime(e['date'], '%Y-%m-%d') >= (datetime.now() - timedelta(days=7))
    ]
    
    # 获取最近 30 天的待办
    all_todos = calendar_db.get_todos(user_id)
    recent_todos = [
        t for t in all_todos
        if t.get('deadline') and
        datetime.strptime(t['deadline'], '%Y-%m-%d') >= (datetime.now() - timedelta(days=30))
    ]
    
    return {
        "events": recent_events[:10],  # 最多 10 条
        "todos": recent_todos[:15],    # 最多 15 条
        "timestamp": datetime.now().isoformat()
    }

async def _analyze_with_llm(user_data: dict) -> dict:
    """使用大模型分析用户兴趣"""
    
    prompt = f"""基于用户的日程和待办事项，推断出用户可能感兴趣的学术研究领域和具体话题。

用户的日程事项：
{_format_events(user_data['events'])}

用户的待办事项：
{_format_todos(user_data['todos'])}

请分析并返回 JSON 格式的结果，包括：
1. inferred_interests：推断出的研究兴趣列表（每个包括 topic、confidence 0-1、reason）
2. suggested_search_keywords：建议搜索的关键词列表（英文）
3. relevant_arxiv_categories：相关的 arXiv 分类（如 cs.AI、cs.LG）
4. search_depth：搜索深度（shallow/moderate/deep）

注意：
- 只返回 JSON，没有其他文字
- confidence 范围是 0-1
- 最多 5 个兴趣话题
- 关键词要具体、可搜索

示例输出：
{{
    "inferred_interests": [
        {{"topic": "Neural Network Acceleration", "confidence": 0.9, "reason": "..."}},
        {{"topic": "Knowledge Graphs", "confidence": 0.7, "reason": "..."}}
    ],
    "suggested_search_keywords": ["neural network acceleration", "GPU optimization"],
    "relevant_arxiv_categories": ["cs.LG", "cs.AI"],
    "search_depth": "moderate"
}}"""
    
    messages = [
        {"role": "system", "content": "You are an expert at analyzing user interests from their calendar and task data. Return only valid JSON."},
        {"role": "user", "content": prompt}
    ]
    
    raw_response = await ollama.chat(messages)
    
    # 解析 JSON
    import json
    try:
        # 处理可能的 markdown 代码块
        if raw_response.startswith('```'):
            raw_response = raw_response.split('```')[1]
            if raw_response.startswith('json'):
                raw_response = raw_response[4:]
        
        analysis = json.loads(raw_response)
        analysis['analysis_timestamp'] = datetime.now().isoformat()
        return analysis
        
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse LLM response: {e}")
        raise ValueError("模型返回格式异常")

def _format_events(events: list) -> str:
    """格式化日程事项"""
    if not events:
        return "（无）"
    
    lines = []
    for e in events:
        line = f"- [{e.get('date')}] {e.get('title')}"
        if e.get('notes'):
            line += f"（备注：{e['notes']}）"
        lines.append(line)
    
    return "\n".join(lines)

def _format_todos(todos: list) -> str:
    """格式化待办事项"""
    if not todos:
        return "（无）"
    
    lines = []
    for t in todos:
        line = f"- [{t.get('deadline')}] {t.get('title')} (优先级: {t.get('priority')})"
        if t.get('notes'):
            line += f"（备注：{t['notes']}）"
        lines.append(line)
    
    return "\n".join(lines)
```

### Step 3: 修改 `services/report_generator.py` - 带工具调用的日报生成

```python
"""
日报生成器 - 使用大模型结合工具调用来生成个性化日报
"""
import logging
import json
import re
from services import ollama, arxiv_tool, user_interest_analyzer
from data import calendar_db

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = """你是一个学术研究助手。你的任务是根据用户的兴趣和日程，为用户推荐最相关的学术论文。

你可以使用以下工具：
1. search_arxiv - 在 arXiv 上搜索论文
2. get_paper_details - 获取论文详细信息

工作流程：
1. 分析用户的研究兴趣（基于提供的信息）
2. 使用 search_arxiv 工具搜索相关论文
3. 筛选最相关的论文
4. 为用户生成个性化的日报

生成日报时：
- 解释为什么这些论文与用户相关
- 突出论文的创新点
- 用用户能理解的方式总结

关键要求：
- 调用工具时使用 JSON 格式
- 最多搜索 15 篇论文
- 最终日报中最多包含 10 篇论文
"""

async def generate_daily_report(user_id: str, report_date: str) -> dict:
    """
    为用户生成个性化日报
    
    流程：
    1. 分析用户兴趣
    2. 根据兴趣搜索论文（AI 决定搜什么）
    3. 生成日报
    """
    
    try:
        # Step 1: 分析用户兴趣
        logger.info(f"Analyzing interests for user {user_id}...")
        interests = await user_interest_analyzer.analyze_user_interests(user_id)
        
        # Step 2: AI 驱动的论文搜索
        logger.info(f"Searching papers based on interests...")
        papers = await _search_papers_with_ai(user_id, interests)
        
        # Step 3: 生成日报
        logger.info(f"Generating report...")
        report = await _generate_report_text(user_id, interests, papers)
        
        # 保存论文和日报到数据库
        paper_ids = await _save_papers(papers)
        
        saved_report = calendar_db.create_daily_report(user_id, {
            'report_date': report_date,
            'summary': report['summary'],
            'paper_ids': paper_ids,
            'html_content': report.get('html_content'),
            'analysis_context': json.dumps(interests, ensure_ascii=False),
            'search_queries': json.dumps(interests.get('suggested_search_keywords', []), ensure_ascii=False),
        })
        
        logger.info(f"Report generated for user {user_id}: {len(paper_ids)} papers")
        return saved_report
        
    except Exception as e:
        logger.error(f"Failed to generate report: {e}")
        raise

async def _search_papers_with_ai(user_id: str, interests: dict) -> list:
    """
    让 AI 根据兴趣分析调用工具搜索论文
    
    这里的关键是：AI 不是简单地执行预定义的搜索，
    而是根据分析的结果动态决定搜索什么
    """
    
    all_papers = []
    
    # 方案 1: 让 AI 逐个搜索感兴趣的话题
    for interest in interests.get('inferred_interests', [])[:3]:  # 最多搜 3 个话题
        topic = interest['topic']
        confidence = interest['confidence']
        
        # 只搜索高置信度的兴趣（>0.5）
        if confidence < 0.5:
            continue
        
        logger.info(f"Searching papers for topic: {topic} (confidence: {confidence})")
        
        # 调用 arXiv 工具
        result = await arxiv_tool.search_arxiv(
            keywords=topic,
            categories=interests.get('relevant_arxiv_categories', []),
            date_range='last_7_days',
            limit=5
        )
        
        if result['success']:
            # 为每篇论文添加相关性说明
            for paper in result['papers']:
                paper['relevance_reason'] = f"与你的研究兴趣 '{topic}' 高度相关"
                all_papers.append(paper)
    
    # 方案 2: 还可以让 AI 搜索特定的关键词组合
    for keyword in interests.get('suggested_search_keywords', [])[:2]:  # 最多搜 2 个关键词
        logger.info(f"Searching papers for keyword: {keyword}")
        
        result = await arxiv_tool.search_arxiv(
            keywords=keyword,
            date_range='last_7_days',
            limit=3
        )
        
        if result['success']:
            for paper in result['papers']:
                # 避免重复
                if not any(p['arxiv_id'] == paper['arxiv_id'] for p in all_papers):
                    paper['relevance_reason'] = f"与你搜索的关键词 '{keyword}' 相关"
                    all_papers.append(paper)
    
    # 去重并限制数量
    unique_papers = []
    seen_ids = set()
    for paper in all_papers:
        if paper['arxiv_id'] not in seen_ids:
            unique_papers.append(paper)
            seen_ids.add(paper['arxiv_id'])
    
    return unique_papers[:15]  # 最多 15 篇

async def _generate_report_text(user_id: str, interests: dict, papers: list) -> dict:
    """生成日报文本"""
    
    # 构建提示词
    interests_text = "\n".join([
        f"- {i['topic']} (置信度: {i['confidence']}, 原因: {i['reason']})"
        for i in interests.get('inferred_interests', [])
    ])
    
    papers_text = "\n".join([
        f"""
标题：{p['title']}
作者：{', '.join(p['authors'][:3])}{'...' if len(p['authors']) > 3 else ''}
摘要：{p['abstract'][:300]}
相关性：{p.get('relevance_reason', 'N/A')}
""" for p in papers[:10]  # 最多 10 篇
    ])
    
    prompt = f"""根据以下信息为用户生成一份个性化的学术日报：

用户推断的研究兴趣：
{interests_text}

找到的相关论文：
{papers_text}

请生成一份日报，包括：
1. 开场段落：解释为什么这些论文与用户相关
2. 论文摘要：按相关性排序，简要介绍每篇论文
3. 总结段落：给出建议和后续行动

用户相关的日期：今天
使用中文生成日报。"""
    
    messages = [
        {"role": "system", "content": "你是一个学术日报编辑，能够以清晰、专业的方式为研究人员总结论文。"},
        {"role": "user", "content": prompt}
    ]
    
    raw = await ollama.chat(messages)
    
    return {
        'summary': raw.strip(),
        'html_content': _markdown_to_html(raw.strip())
    }

def _markdown_to_html(text: str) -> str:
    """简单的 Markdown 转 HTML"""
    import html
    text = html.escape(text)
    lines = text.split('\n')
    html_lines = []
    
    for line in lines:
        if line.startswith('## '):
            html_lines.append(f'<h2>{line[3:]}</h2>')
        elif line.startswith('# '):
            html_lines.append(f'<h1>{line[2:]}</h1>')
        elif line.startswith('- '):
            html_lines.append(f'<li>{line[2:]}</li>')
        elif line.strip() == '':
            html_lines.append('<br>')
        else:
            html_lines.append(f'<p>{line}</p>')
    
    return '\n'.join(html_lines)

async def _save_papers(papers: list) -> list:
    """保存论文到数据库，返回 paper_ids"""
    paper_ids = []
    
    for paper in papers:
        result = calendar_db.create_or_update_paper({
            'arxiv_id': paper['arxiv_id'],
            'title': paper['title'],
            'authors': json.dumps(paper['authors']),
            'abstract': paper['abstract'],
            'pdf_url': paper['pdf_url'],
            'category': paper['category'],
            'published_date': paper['published_date'],
            'paper_text': '',  # 可选：后续可以获取全文
            'relevance_reason': paper.get('relevance_reason', '')
        })
        
        paper_ids.append(result['id'])
    
    return paper_ids
```

---

## 📊 数据库修改

### 修改 `data/calendar_db.py`

```python
def init_db() -> None:
    with _conn() as c:
        c.executescript("""
            -- 简化的用户偏好设置（只保留基本选项）
            CREATE TABLE IF NOT EXISTS arxiv_preferences (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id         TEXT    NOT NULL UNIQUE,
                report_time     TEXT    DEFAULT '09:00',
                max_papers      INTEGER DEFAULT 10,
                enable_report   INTEGER DEFAULT 1,
                created_at      TEXT    NOT NULL,
                updated_at      TEXT    NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_pref_user ON arxiv_preferences(user_id);
            
            -- 论文表（支持任意 arXiv 论文，不仅仅是预设分类）
            CREATE TABLE IF NOT EXISTS papers (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                arxiv_id        TEXT    NOT NULL UNIQUE,
                title           TEXT    NOT NULL,
                authors         TEXT    NOT NULL,
                abstract        TEXT,
                pdf_url         TEXT,
                category        TEXT,
                published_date  TEXT,
                paper_text      TEXT,
                relevance_reason TEXT,  -- AI 为什么推荐这篇
                created_at      TEXT    NOT NULL,
                updated_at      TEXT    NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_papers_arxiv ON papers(arxiv_id);
            CREATE INDEX IF NOT EXISTS idx_papers_date ON papers(published_date);
            
            -- 日报表（包含 AI 分析过程）
            CREATE TABLE IF NOT EXISTS daily_reports (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id         TEXT    NOT NULL,
                report_date     TEXT    NOT NULL,
                summary         TEXT    NOT NULL,
                paper_ids       TEXT    NOT NULL,
                analysis_context TEXT,  -- AI 分析的用户兴趣（JSON）
                search_queries  TEXT,   -- AI 搜索的关键词（JSON）
                created_at      TEXT    NOT NULL,
                updated_at      TEXT    NOT NULL,
                UNIQUE(user_id, report_date)
            );
            CREATE INDEX IF NOT EXISTS idx_reports_user ON daily_reports(user_id);
            CREATE INDEX IF NOT EXISTS idx_reports_date ON daily_reports(report_date);
        """)
```

---

## 🌐 API 接口

### `routes/arxiv_router.py`

```python
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from auth.deps import get_current_session
from auth.models import SessionPrincipal
from data import calendar_db
from services import user_interest_analyzer

router = APIRouter(prefix="/arxiv", tags=["arxiv"])

class PreferenceIn(BaseModel):
    report_time: str = "09:00"
    max_papers: int = 10
    enable_report: bool = True

@router.get("/preferences")
def get_preferences(session: SessionPrincipal = Depends(get_current_session)):
    """获取用户偏好"""
    pref = calendar_db.get_arxiv_preference(session.user_id)
    return pref or {
        "report_time": "09:00",
        "max_papers": 10,
        "enable_report": True
    }

@router.post("/preferences")
def update_preferences(
    body: PreferenceIn,
    session: SessionPrincipal = Depends(get_current_session)
):
    """更新用户偏好"""
    pref = calendar_db.create_or_update_arxiv_preference(session.user_id, body.model_dump())
    return pref

@router.get("/analyze-interests")
async def analyze_interests(session: SessionPrincipal = Depends(get_current_session)):
    """分析用户的研究兴趣"""
    interests = await user_interest_analyzer.analyze_user_interests(session.user_id)
    return interests

@router.post("/generate-report-manual")
async def generate_report_manual(
    report_date: str,
    session: SessionPrincipal = Depends(get_current_session)
):
    """手动生成日报（用于测试）"""
    from services import report_generator
    
    try:
        report = await report_generator.generate_daily_report(session.user_id, report_date)
        return report
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/reports")
def get_reports(
    limit: int = 30,
    session: SessionPrincipal = Depends(get_current_session)
):
    """获取用户的日报列表"""
    reports = calendar_db.get_daily_reports_list(session.user_id, limit)
    for report in reports:
        report['analysis_context'] = json.loads(report.get('analysis_context', '{}'))
        report['search_queries'] = json.loads(report.get('search_queries', '[]'))
    return reports

@router.get("/reports/{report_date}")
def get_report(
    report_date: str,
    session: SessionPrincipal = Depends(get_current_session)
):
    """获取特定日期的日报"""
    report = calendar_db.get_daily_report(session.user_id, report_date)
    if not report:
        raise HTTPException(status_code=404, detail="日报不存在")
    
    report['analysis_context'] = json.loads(report.get('analysis_context', '{}'))
    report['search_queries'] = json.loads(report.get('search_queries', '[]'))
    return report
```

---

## ✅ 核心差异总结

### 旧方案 vs 新方案

| 方面 | 旧方案 | 新方案 |
|------|--------|--------|
| **用户输入** | 设置感兴趣的领域（cs.AI, cs.CV） | 仅设置推送时间和论文数量 |
| **兴趣推断** | 无，完全靠用户选择 | **AI 分析日程/待办推断** |
| **论文搜索** | 按预设分类固定搜索 | **AI 决定搜什么关键词和分类** |
| **搜索方式** | 被动，系统拉取 | **主动，AI 调用工具** |
| **个性化程度** | 低，所有兴趣相同的用户看同样论文 | **高，根据个人日程定制** |
| **可扩展性** | 难，需要手动添加分类 | **易，AI 可推断任意话题** |

---

## 🎯 现在的架构

```
用户的日程/待办
    ↓
AI 分析（使用大模型）
    ↓
AI 推断兴趣（生成：话题、置信度、原因）
    ↓
AI 调用工具搜索（search_arxiv）
    ↓
获得论文列表
    ↓
AI 生成日报（个性化解释）
    ↓
存储到数据库
    ↓
用户下载/查看
```

**关键点**：AI 在整个流程中做决策，而不是执行预定义的命令。

---

## 📝 后续可能的增强

1. **反馈循环**：用户点赞/踩论文 → AI 学习优化推荐
2. **论文关联**：AI 找出论文间的联系，生成知识图谱
3. **时间学习**：AI 分析用户最活跃的学习时间，优化推送
4. **协作学习**：多用户共同研究课题，AI 汇总论文推荐
5. **深度阅读**：AI 可调用 `get_paper_full_text` 工具深度分析论文

---

这样设计的好处是什么？

✅ **智能自适应**：系统随着用户日程变化而动态调整
✅ **减少配置**：用户不需要手动设置感兴趣的领域
✅ **真正个性化**：不同用户即使日期相同，推荐也完全不同
✅ **可扩展**：新增 AI 能力时不需要修改数据库或预设分类
✅ **工具思维**：大模型不是黑盒，而是通过工具与系统交互
✅ **可解释**：知道 AI 为什么推荐这篇论文（relevance_reason）

祝你重新实现！这个设计更符合真实的 AI 应用场景。🚀
