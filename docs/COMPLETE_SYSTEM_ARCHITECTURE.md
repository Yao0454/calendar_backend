# 完整系统架构和部署指南

## 项目总体架构

你的日程管理系统分为三个主要模块：

```
┌──────────────────────────────────────────────────────────────────┐
│                    Calendar Backend System                        │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌────────────────────────┐  ┌────────────────────────────────┐│
│  │  模块一：日程管理       │  │  模块二：AI 规划助手            ││
│  ├────────────────────────┤  ├────────────────────────────────┤│
│  │ • 事件管理             │  │ • 多轮对话                     ││
│  │ • 待办管理             │  │ • 智能规划                     ││
│  │ • 导入/导出            │  │ • 规划草稿管理                 ││
│  │ • 搜索/筛选            │  │ • 导入日程                     ││
│  └────────────────────────┘  └────────────────────────────────┘│
│                                                                  │
│  ┌────────────────────────┐  ┌────────────────────────────────┐│
│  │  模块三：用户画像       │  │  模块四：智能推荐系统          ││
│  ├────────────────────────┤  ├────────────────────────────────┤│
│  │ • 兴趣标签管理         │  │ • arXiv 爬虫                   ││
│  │ • 画像编辑             │  │ • GitHub 爬虫                  ││
│  │ • 分类统计             │  │ • Twitter 爬虫                 ││
│  │                        │  │ • 推荐引擎                     ││
│  │                        │  │ • 后台任务                     ││
│  └────────────────────────┘  └────────────────────────────────┘│
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

---

## 核心技术栈

### 后端框架
- **FastAPI** - 现代 Python Web 框架
- **SQLite** - 本地数据库
- **Ollama** - 本地大模型推理
- **APScheduler** - 后台定时任务
- **httpx** - 异步 HTTP 客户端

### 关键库
```
fastapi>=0.111.0
uvicorn[standard]>=0.29.0
httpx>=0.27.0
Pillow>=10.0.0
pymupdf>=1.24.0
pydantic>=2.0.0
bcrypt>=4.0.0
apscheduler>=3.10.0
feedparser>=6.0.0
```

---

## 文件结构

```
calendar_backend/
├── main.py                          # 主应用入口
├── config.py                        # 配置文件
├── models.py                        # 数据模型
├── requirements.txt                 # 依赖列表
│
├── auth/                            # 用户认证模块
│   ├── __init__.py
│   ├── auth_service.py             # 认证服务
│   ├── password_service.py         # 密码管理
│   ├── deps.py                     # 依赖注入
│   ├── models.py                   # 模型定义
│   ├── router.py                   # 认证路由
│   └── stores/                     # 数据存储
│       ├── session_store.py
│       └── user_store.py
│
├── data/                            # 数据层
│   ├── __init__.py
│   ├── calendar_db.py              # 数据库操作（扩展版）
│   └── calendar.db                 # SQLite 数据库文件
│
├── routes/                          # 路由层
│   ├── __init__.py
│   ├── items_router.py             # 日程/待办路由（已有）
│   ├── chat_router.py              # 对话路由（新增）
│   ├── profile_router.py           # 用户画像路由（新增）
│   └── recommendations_router.py   # 推荐路由（新增）
│
├── services/                        # 服务层
│   ├── __init__.py
│   ├── extractor.py                # 日程提取（已有）
│   ├── ollama.py                   # Ollama 集成（已有）
│   ├── file_handler.py             # 文件处理（已有）
│   ├── report_generator.py         # 报告生成（已有）
│   ├── arxiv_tool.py               # arXiv 工具（已有）
│   ├── planner_agent.py            # AI 规划助手（新增）
│   ├── content_crawler.py          # 内容爬虫（新增）
│   ├── recommendation_engine.py    # 推荐引擎（新增）
│   └── background_tasks.py         # 后台任务（新增）
│
├── docs/                            # 文档
│   ├── AI_PLANNING_AGENT_IMPLEMENTATION.md
│   └── USER_PROFILE_RECOMMENDATION_IMPLEMENTATION.md
│
└── start.sh                         # 启动脚本
```

---

## 实现顺序和优先级

### 第一阶段：AI 规划助手（核心功能）
**预计时间：1-2 周**

1. 扩展数据库 Schema（chat_messages、planning_drafts 表）
2. 实现 `services/planner_agent.py`
3. 实现 `routes/chat_router.py`
4. 集成到主应用
5. 测试和调试

**关键文件：**
- `data/calendar_db.py` - 数据库操作函数
- `services/planner_agent.py` - 规划逻辑
- `routes/chat_router.py` - API 端点

**API 端点：**
- POST /chat/start
- POST /chat/message
- GET /chat/history/{session_id}
- POST /chat/draft
- POST /chat/confirm/{draft_id}

---

### 第二阶段：用户画像管理（基础功能）
**预计时间：1 周**

1. 扩展数据库 Schema（user_interests 表）
2. 实现 `routes/profile_router.py`
3. 前端编辑界面
4. 测试

**关键文件：**
- `routes/profile_router.py` - 用户画像 API
- `data/calendar_db.py` - 兴趣管理函数

**API 端点：**
- POST /profile/interests
- GET /profile/interests
- PUT /profile/interests/{id}
- DELETE /profile/interests/{id}

---

### 第三阶段：内容爬虫和推荐系统（高级功能）
**预计时间：2-3 周**

1. 扩展数据库 Schema（content_items、user_recommendations 等表）
2. 实现 `services/content_crawler.py`
3. 实现 `services/recommendation_engine.py`
4. 实现 `services/background_tasks.py`
5. 实现 `routes/recommendations_router.py`
6. 后台任务部署和监控
7. 前端推荐展示页面

**关键文件：**
- `services/content_crawler.py` - 爬虫实现
- `services/recommendation_engine.py` - 推荐算法
- `services/background_tasks.py` - 定时任务
- `routes/recommendations_router.py` - 推荐 API

**API 端点：**
- GET /recommendations/feed
- GET /recommendations/{content_id}
- POST /recommendations/{content_id}/read
- POST /recommendations/{content_id}/save
- GET /recommendations/stats/summary

---

## 依赖库更新

更新 `requirements.txt`：

```txt
fastapi>=0.111.0
uvicorn[standard]>=0.29.0
httpx>=0.27.0
Pillow>=10.0.0
pymupdf>=1.24.0
python-multipart>=0.0.9
pydantic>=2.0.0
bcrypt>=4.0.0
apscheduler>=3.10.0
feedparser>=6.0.0
```

安装新依赖：
```bash
pip install apscheduler feedparser
```

---

## 数据库初始化流程

当应用启动时，会自动执行以下初始化：

```python
# main.py 中的 lifespan
@asynccontextmanager
async def lifespan(app: FastAPI):
    # 初始化数据库
    calendar_db.init_db()  # 创建所有表
    logger.info("Calendar DB initialised")
    
    # 启动后台任务
    background_manager.start()
    
    # 检查 Ollama 可用性
    if await is_available():
        logger.info("Ollama is reachable at startup")
    else:
        logger.warning("Ollama is NOT reachable")
    
    yield
    
    # 关闭后台任务
    background_manager.shutdown()
```

---

## 环境变量配置

创建 `.env` 文件或设置环境变量：

```bash
# Ollama 配置
OLLAMA_BASE_URL=http://localhost:11434
MODEL_NAME=qwen3-vl:30b

# 服务器配置
HOST=0.0.0.0
PORT=5522
REQUEST_TIMEOUT=120

# API 密钥（可选）
GITHUB_API_TOKEN=your_github_token
TWITTER_BEARER_TOKEN=your_twitter_token

# 爬虫配置
ARXIV_FETCH_LIMIT=50
GITHUB_FETCH_LIMIT=50
TWITTER_FETCH_LIMIT=20
```

---

## 部署步骤

### 1. 本地开发环境

```bash
# 克隆项目
git clone <repo-url>
cd calendar_backend

# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Linux/Mac
# 或
venv\Scripts\activate  # Windows

# 安装依赖
pip install -r requirements.txt

# 启动 Ollama（另一个终端）
ollama serve

# 运行应用
python main.py
# 或
uvicorn main:app --reload --host 0.0.0.0 --port 5522
```

### 2. Docker 部署

创建 `Dockerfile`：

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "5522"]
```

创建 `docker-compose.yml`：

```yaml
version: '3.8'

services:
  backend:
    build: .
    ports:
      - "5522:5522"
    environment:
      - OLLAMA_BASE_URL=http://ollama:11434
      - MODEL_NAME=qwen3-vl:30b
    depends_on:
      - ollama
    volumes:
      - ./data:/app/data

  ollama:
    image: ollama/ollama:latest
    ports:
      - "11434:11434"
    volumes:
      - ollama_data:/root/.ollama

volumes:
  ollama_data:
```

启动：
```bash
docker-compose up -d
```

---

## API 测试

### 使用 curl 测试

```bash
# 注册用户
curl -X POST http://localhost:5522/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username":"test","password":"pass123"}'

# 登录
curl -X POST http://localhost:5522/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"test","password":"pass123"}'

# 开始对话
curl -X POST http://localhost:5522/chat/start \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"user_request":"我想在2周内学完PyTorch基础"}'

# 添加兴趣
curl -X POST http://localhost:5522/profile/interests \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "category":"research",
    "tag":"Machine Learning",
    "keywords":["deep learning","neural network"],
    "weight":1.0
  }'

# 获取推荐
curl -X GET "http://localhost:5522/recommendations/feed?limit=10" \
  -H "Authorization: Bearer <token>"
```

### 使用 Postman 或 Thunder Client

1. 导入 API 集合
2. 设置基础 URL：`http://localhost:5522`
3. 设置认证令牌
4. 逐个测试端点

---

## 监控和日志

### 日志配置

修改 `main.py` 中的日志配置：

```python
import logging.config

LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "standard": {
            "format": "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "standard",
        },
        "file": {
            "class": "logging.FileHandler",
            "filename": "logs/app.log",
            "formatter": "standard",
        },
    },
    "root": {
        "handlers": ["console", "file"],
        "level": "INFO",
    },
}

logging.config.dictConfig(LOGGING_CONFIG)
```

### 后台任务监控

在数据库中查看爬虫运行日志：

```sql
SELECT * FROM crawler_logs ORDER BY started_at DESC LIMIT 10;
```

---

## 性能优化建议

### 1. 数据库优化
- 定期清理旧的对话记录
- 定期删除过期的推荐记录
- 设置适当的索引

```sql
-- 清理 30 天前的对话
DELETE FROM chat_messages 
WHERE datetime(created_at) < datetime('now', '-30 days');

-- 清理已读的推荐
DELETE FROM user_recommendations 
WHERE read=1 AND datetime(created_at) < datetime('now', '-60 days');
```

### 2. 缓存优化
```python
from functools import lru_cache

@lru_cache(maxsize=128)
def get_user_interests(user_id: str):
    # 缓存用户兴趣
    pass
```

### 3. API 限流
```python
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter

@app.post("/chat/start")
@limiter.limit("10/minute")
async def start_chat(...):
    pass
```

### 4. 爬虫限制
- 设置合理的请求间隔
- 实现指数退避算法
- 尊重 robots.txt

---

## 故障排查指南

### 问题 1：Ollama 连接失败
```
症状: OllamaUnavailableError
解决方案:
1. 确认 Ollama 正在运行: ollama serve
2. 检查 OLLAMA_BASE_URL 配置
3. 测试连接: curl http://localhost:11434/api/tags
```

### 问题 2：模型未找到
```
症状: OllamaModelNotFoundError
解决方案:
1. 拉取模型: ollama pull qwen3-vl:30b
2. 列出已有模型: ollama list
3. 更新 MODEL_NAME 配置
```

### 问题 3：数据库锁定
```
症状: database is locked
解决方案:
1. 减少并发数
2. 增加超时时间
3. 重启应用
```

### 问题 4：推荐结果为空
```
症状: 没有推荐内容返回
解决方案:
1. 检查爬虫日志: SELECT * FROM crawler_logs
2. 检查用户兴趣是否设置
3. 检查推荐引擎日志
```

---

## 安全最佳实践

### 1. 认证和授权
- 使用强密码
- 定期轮换密钥
- 实现 CORS 限制

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://yourdomain.com"],  # 限制域名
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
    max_age=600,
)
```

### 2. 数据加密
- 保护敏感数据（密码、令牌）
- 使用 HTTPS
- 加密数据库备份

### 3. API 安全
- 实现速率限制
- 验证输入数据
- 记录所有 API 调用

```python
from pydantic import Field, validator

class InterestIn(BaseModel):
    tag: str = Field(..., min_length=1, max_length=100)
    keywords: list = Field(..., max_items=10)
    
    @validator('keywords')
    def validate_keywords(cls, v):
        if not all(isinstance(k, str) for k in v):
            raise ValueError('All keywords must be strings')
        return v
```

---

## 扩展功能建议

### 短期（1-2 月）
- [ ] 推荐系统优化（协同过滤）
- [ ] 规划方案版本控制
- [ ] 爬虫内容去重
- [ ] 推荐算法 A/B 测试

### 中期（3-6 月）
- [ ] 用户行为分析
- [ ] 个性化推荐优化
- [ ] 日程冲突预警
- [ ] 智能提醒系统

### 长期（6-12 月）
- [ ] 多语言支持
- [ ] 移动应用适配
- [ ] 团队协作功能
- [ ] 高级分析报告

---

## 参考资源

### 官方文档
- [FastAPI 文档](https://fastapi.tiangolo.com/)
- [SQLite 文档](https://www.sqlite.org/docs.html)
- [Ollama 文档](https://github.com/ollama/ollama)
- [APScheduler 文档](https://apscheduler.readthedocs.io/)

### API 文档
- [arXiv API](https://arxiv.org/help/api)
- [GitHub API](https://docs.github.com/en/rest)
- [Twitter API v2](https://developer.twitter.com/en/docs/twitter-api)

### 其他资源
- [Pydantic 文档](https://docs.pydantic.dev/)
- [httpx 文档](https://www.python-httpx.org/)
- [feedparser 文档](https://feedparser.readthedocs.io/)

---

## 总结

这个日程管理系统通过以下方式提供价值：

1. **自动化日程管理** - 从多种格式导入日程
2. **AI 智能规划** - 基于现有日程生成个性化规划
3. **用户画像** - 记录用户的兴趣和偏好
4. **智能推荐** - 推送相关的研究成果和技术项目

系统采用模块化设计，每个功能都是独立且可扩展的。你可以根据需求逐步实现各个模块。

祝你的项目开发顺利！
