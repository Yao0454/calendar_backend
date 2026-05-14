# Calendar Backend - 系统架构文档

## 一、系统概述

Calendar Backend 是一个基于 FastAPI 的智能日程管理系统，集成了 AI 规划助手、个性化推荐系统和学术日报功能。

### 核心特性
- 🤖 **AI规划助手**：基于 Ollama 的智能日程规划
- 📊 **个性化推荐**：多因子综合评分推荐系统
- 📰 **学术日报**：自动生成 arXiv 论文日报
- 👤 **用户画像**：手动 + AI 自动提取兴趣标签
- 🔐 **安全隔离**：完整的用户数据隔离机制

---

## 二、技术栈

### 后端框架
- **FastAPI** - 现代高性能 Web 框架
- **Uvicorn** - ASGI 服务器
- **Pydantic** - 数据验证

### 数据库
- **SQLite** - 轻量级关系数据库
- **APScheduler** - 定时任务调度

### AI 集成
- **Ollama** - 本地 LLM 推理
- **qwen3-vl:30b** - 主要模型

### 异步处理
- **asyncio** - 协程并发
- **httpx** - 异步 HTTP 客户端
- **feedparser** - RSS/Atom 解析

---

## 三、系统架构

### 3.1 整体架构图

```
┌─────────────────────────────────────────────────────────┐
│                      用户界面层                          │
│                   (前端 / API 客户端)                     │
└─────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────┐
│                      API 路由层                          │
│  ┌──────────┬──────────┬──────────┬──────────┐        │
│  │  auth    │  chat    │ profile  │recommend │        │
│  │  router  │  router  │  router  │  router  │        │
│  └──────────┴──────────┴──────────┴──────────┘        │
└─────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────┐
│                      服务层                              │
│  ┌──────────┬──────────┬──────────┬──────────┐        │
│  │ planner  │recommend │ crawler  │ report   │        │
│  │  agent   │  engine  │          │generator │        │
│  └──────────┴──────────┴──────────┴──────────┘        │
└─────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────┐
│                    数据访问层                            │
│                   calendar_db.py                        │
└─────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────┐
│                    数据存储层                            │
│                      SQLite                             │
└─────────────────────────────────────────────────────────┘
```

### 3.2 后台任务架构

```
┌─────────────────────────────────────────┐
│        Background Task Manager          │
│         (APScheduler)                   │
└─────────────────────────────────────────┘
         ↓              ↓              ↓
┌────────────┐ ┌────────────┐ ┌────────────┐
│  爬虫任务  │ │  推荐任务  │ │  日报任务  │
│  (6小时)   │ │  (1小时)   │ │  (24小时)  │
└────────────┘ └────────────┘ └────────────┘
         ↓              ↓              ↓
┌────────────┐ ┌────────────┐ ┌────────────┐
│ arXiv      │ │  推荐引擎  │ │  AI生成    │
│ GitHub     │ │            │ │  摘要      │
└────────────┘ └────────────┘ └────────────┘
```

---

## 四、目录结构

```
calendar_backend/
├── auth/                   # 认证模块
│   ├── deps.py            # 认证依赖
│   ├── router.py          # 认证路由
│   ├── auth_service.py    # 认证服务
│   ├── models.py          # 认证模型
│   └── stores/            # 存储实现
│       ├── session_store.py
│       └── user_store.py
│
├── data/                   # 数据层
│   └── calendar_db.py     # 数据库操作
│
├── routes/                 # API 路由
│   ├── items_router.py    # 日程管理
│   ├── chat_router.py     # AI规划助手
│   ├── profile_router.py  # 用户画像
│   ├── recommendations_router.py  # 推荐系统
│   └── arxiv_router.py    # arXiv日报
│
├── services/               # 业务服务
│   ├── ollama.py          # Ollama集成
│   ├── extractor.py       # 日程提取
│   ├── planner_agent.py   # AI规划助手
│   ├── profile_extractor.py  # 兴趣提取
│   ├── content_crawler.py # 内容爬虫
│   ├── recommendation_engine.py  # 推荐引擎
│   ├── report_generator.py  # 日报生成
│   ├── background_tasks.py  # 后台任务
│   └── file_handler.py    # 文件处理
│
├── models.py              # 公共模型
├── config.py              # 配置文件
├── main.py                # 应用入口
│
├── API_DOCUMENTATION.md   # API文档
├── SECURITY_AND_PERFORMANCE_REPORT.md  # 安全报告
└── ARCHITECTURE.md        # 本文档
```

---

## 五、核心模块详解

### 5.1 认证模块 (auth/)

**职责**：用户认证和会话管理

**核心组件**：
- `auth_service.py` - 认证逻辑（注册、登录、密码验证）
- `session_store.py` - 会话存储（内存字典）
- `user_store.py` - 用户存储（SQLite）
- `deps.py` - FastAPI 依赖注入

**认证流程**：
```
1. 用户登录 → 验证密码
2. 生成 JWT token
3. 创建会话（session_store）
4. 返回 token 给客户端
5. 后续请求携带 token
6. get_current_session 验证并注入用户信息
```

**安全特性**：
- bcrypt 密码加密
- JWT token 认证
- 会话过期管理
- 用户数据隔离

---

### 5.2 数据层 (data/)

**职责**：所有数据库操作

**核心文件**：`calendar_db.py`

**数据库表**：

| 表名 | 说明 | 主要字段 |
|------|------|---------|
| events | 日程事件 | id, user_id, title, date, time, location |
| todos | 待办事项 | id, user_id, title, deadline, priority, is_done |
| chat_messages | 对话消息 | id, user_id, session_id, role, content |
| planning_drafts | 规划草稿 | id, user_id, proposed_events, proposed_todos |
| user_interests | 用户兴趣 | id, user_id, category, tag, keywords, weight |
| content_items | 内容项 | id, source, source_id, title, description |
| user_recommendations | 用户推荐 | id, user_id, content_id, recommendation_score |
| crawler_logs | 爬虫日志 | id, source, status, items_found |
| arxiv_preferences | arXiv偏好 | id, user_id, push_time, paper_count |
| daily_reports | 日报 | id, user_id, report_date, summary |

**设计原则**：
- 所有查询都包含 `WHERE user_id=?`（用户隔离）
- 使用参数化查询（防SQL注入）
- 自动时间戳管理
- JSON 字段序列化

---

### 5.3 AI规划助手 (services/planner_agent.py)

**职责**：智能日程规划

**核心类**：`PlannerAgent`

**工作流程**：
```
1. 用户发起请求
   ↓
2. 读取用户现有日程（_get_user_schedule_context）
   ↓
3. 构建系统提示（_build_system_prompt）
   ↓
4. 调用 Ollama 生成规划建议
   ↓
5. 多轮对话优化
   ↓
6. 生成 JSON 格式规划（generate_plan_from_response）
   ↓
7. 创建草稿 → 用户确认 → 导入日程表
```

**特性**：
- 多轮对话支持
- 考虑现有日程避免冲突
- JSON 格式输出解析
- 草稿机制（用户可审核）

---

### 5.4 用户画像 (services/profile_extractor.py)

**职责**：提取和管理用户兴趣标签

**兴趣来源**：
1. **手动编辑** - 用户主动添加
2. **AI自动提取** - 从对话中分析

**AI提取流程**：
```
每天凌晨2:00
   ↓
遍历所有用户
   ↓
获取昨天的聊天记录
   ↓
合并所有会话内容
   ↓
AI分析提取兴趣
   ↓
过滤置信度 >= 0.6
   ↓
保存到用户画像
```

**兴趣分类**：
- `research` - 研究领域（如 Machine Learning）
- `project` - 项目类型（如 Web Development）
- `skill` - 技术技能（如 Python）

---

### 5.5 推荐系统 (services/recommendation_engine.py)

**职责**：个性化内容推荐

**核心算法**：多因子综合评分

```
综合评分 = 相关度×0.4 + 新鲜度×0.2 + 流行度×0.2 + 多样性×0.2
```

**各因子计算**：

1. **相关度分数**（40%）
   - 基于用户兴趣关键词匹配
   - 考虑兴趣权重
   - 归一化到 0-1

2. **时间新鲜度**（20%）
   - 指数衰减函数
   - 30天半衰期
   - 新内容分数更高

3. **流行度分数**（20%）
   - GitHub: 基于 stars 数
   - arXiv: 默认 0.5
   - log10 归一化

4. **多样性惩罚**（20%）
   - 基于标签相似度（Jaccard系数）
   - 避免推荐太相似的内容

**推荐流程**：
```
1. 获取用户兴趣标签
   ↓
2. 获取所有未推荐内容
   ↓
3. 计算每个内容的综合评分
   ↓
4. 过滤分数 >= 0.3 的内容
   ↓
5. 按分数降序排序
   ↓
6. 返回 Top N 推荐
```

---

### 5.6 内容爬虫 (services/content_crawler.py)

**职责**：从外部源抓取内容

**爬虫类型**：

#### ArxivCrawler
- **数据源**：arXiv API
- **搜索方式**：关键词 + 分类 + 时间范围
- **返回内容**：论文（标题、摘要、作者、分类）

#### GitHubCrawler
- **数据源**：GitHub API
- **搜索方式**：关键词 + 语言 + 时间范围
- **返回内容**：仓库（标题、描述、作者、stars）

**执行频率**：每6小时

---

### 5.7 日报生成 (services/report_generator.py)

**职责**：生成学术日报

**生成流程**：
```
1. 获取用户推荐（复用推荐引擎）
   ↓
2. 筛选 arXiv 论文
   ↓
3. 取 Top N（用户偏好数量）
   ↓
4. AI 生成专业摘要
   ↓
5. Markdown → HTML 转换
   ↓
6. 保存日报
```

**AI摘要生成**：
- 使用 Ollama 生成中文摘要
- 包含论文标题、作者、核心创新点
- Markdown 格式输出

**执行频率**：每24小时

---

### 5.8 后台任务 (services/background_tasks.py)

**职责**：定时任务调度

**任务列表**：

| 任务 | 频率 | 说明 |
|------|------|------|
| run_crawlers | 每6小时 | 运行内容爬虫 |
| generate_recommendations | 每1小时 | 生成用户推荐 |
| generate_daily_reports | 每24小时 | 生成学术日报 |
| extract_interests | 每天凌晨2:00 | 从对话提取兴趣 |

**调度器**：APScheduler（AsyncIOScheduler）

**生命周期管理**：
- 应用启动时启动调度器
- 应用关闭时停止调度器

---

## 六、数据流图

### 6.1 AI规划流程

```
用户请求
   ↓
POST /chat/start
   ↓
PlannerAgent.start_conversation()
   ↓
读取用户日程 → 构建提示 → Ollama推理
   ↓
返回AI建议 + session_id
   ↓
[多轮对话优化]
   ↓
POST /chat/draft
   ↓
生成JSON格式规划 → 创建草稿
   ↓
POST /chat/confirm/{id}
   ↓
导入事件和待办到日程表
```

### 6.2 推荐生成流程

```
定时任务触发（每小时）
   ↓
遍历所有用户
   ↓
获取用户兴趣标签
   ↓
获取未推荐内容
   ↓
计算综合评分
   ├─ 相关度分数
   ├─ 新鲜度分数
   ├─ 流行度分数
   └─ 多样性分数
   ↓
排序筛选 → 保存推荐
```

### 6.3 日报生成流程

```
定时任务触发（每天）
   ↓
获取用户推荐
   ↓
筛选arXiv论文
   ↓
AI生成摘要
   ↓
Markdown → HTML
   ↓
保存日报
```

---

## 七、安全架构

### 7.1 认证授权

```
请求 → Bearer Token → JWT验证 → 会话验证 → 用户注入
```

**保护范围**：所有业务API

### 7.2 用户隔离

**实现方式**：
- 所有数据库查询包含 `WHERE user_id=?`
- 所有路由使用 `Depends(get_current_session)`
- 自动注入当前用户ID

### 7.3 输入验证

**Pydantic模型验证**：
- 类型检查
- 必填字段
- 格式验证
- 长度限制

### 7.4 SQL注入防护

**参数化查询**：
```python
c.execute("SELECT * FROM events WHERE user_id=?", (user_id,))
```

### 7.5 XSS防护

**HTML转义**：
```python
html.escape(markdown_text)
```

---

## 八、性能优化

### 8.1 异步架构

- **asyncio** - 协程并发
- **httpx** - 异步HTTP客户端
- **后台任务** - 不阻塞主请求

### 8.2 数据库优化

- **索引** - user_id, published_date 等
- **批量操作** - bulk_insert_events/todos
- **连接池** - SQLite连接管理

### 8.3 推荐算法优化

- **时间复杂度**：O(n*m + k log k)
  - n = 用户兴趣数（< 10）
  - m = 关键词数（< 20）
  - k = 候选内容数（< 100）

### 8.4 建议优化

1. **添加Redis缓存**
   - 缓存推荐结果
   - 缓存用户画像
   - 缓存日报内容

2. **数据库读写分离**
   - 读操作使用从库
   - 写操作使用主库

3. **配置Ollama并发**
   ```bash
   export OLLAMA_NUM_PARALLEL=4
   ```

---

## 九、部署架构

### 9.1 单机部署

```
┌─────────────────────────────┐
│      单机服务器              │
│  ┌───────────────────────┐ │
│  │   Nginx (反向代理)     │ │
│  └───────────────────────┘ │
│           ↓                 │
│  ┌───────────────────────┐ │
│  │  Uvicorn (ASGI)       │ │
│  │  FastAPI Application  │ │
│  └───────────────────────┘ │
│           ↓                 │
│  ┌───────────────────────┐ │
│  │  Ollama (LLM推理)      │ │
│  └───────────────────────┘ │
│           ↓                 │
│  ┌───────────────────────┐ │
│  │  SQLite (数据存储)     │ │
│  └───────────────────────┘ │
└─────────────────────────────┘
```

### 9.2 生产部署建议

```bash
# 1. 使用Gunicorn多进程
gunicorn main:app -w 4 -k uvicorn.workers.UvicornWorker

# 2. 启用HTTPS
certbot --nginx -d yourdomain.com

# 3. 配置Ollama并发
export OLLAMA_NUM_PARALLEL=4

# 4. 启动服务
uvicorn main:app --host 0.0.0.0 --port 5522
```

---

## 十、监控与日志

### 10.1 日志配置

```python
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
```

### 10.2 关键日志点

- 用户认证（登录、注册）
- AI推理（请求、响应、耗时）
- 后台任务（启动、完成、错误）
- 数据库操作（错误）

### 10.3 性能监控

- 响应时间
- AI推理时间
- 数据库查询时间
- 内存占用

---

## 十一、扩展性设计

### 11.1 模块化架构

- 认证模块可替换（auth/）
- 数据库可替换（data/）
- 推荐算法可替换（services/recommendation_engine.py）
- 爬虫可扩展（services/content_crawler.py）

### 11.2 新增数据源

```python
class NewCrawler(ContentCrawler):
    async def search(self, keywords, limit):
        # 实现新的爬虫
        ...
```

### 11.3 新增推荐算法

```python
class NewRecommendationEngine:
    def calculate_score(self, user, content):
        # 实现新的推荐算法
        ...
```

---

## 十二、技术债务

### 当前限制

1. **单机架构** - 无法水平扩展
2. **SQLite** - 并发写入限制
3. **内存会话** - 重启丢失
4. **无缓存** - 性能受限

### 改进方向

1. **Redis** - 会话存储 + 缓存
2. **PostgreSQL** - 替代SQLite
3. **消息队列** - Celery/RQ
4. **微服务** - 拆分AI服务

---

## 十三、版本历史

| 版本 | 日期 | 说明 |
|------|------|------|
| v1.0 | 2026-05-13 | 初始版本，包含所有核心功能 |

---

**文档维护者**：开发团队  
**最后更新**：2026-05-13  
**文档版本**：v1.0
