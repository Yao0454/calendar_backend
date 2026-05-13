# 快速开始指南

## 📋 阅读顺序

### 第一步：了解整体概况（5分钟）
📄 **docs/README.md** - 项目概述
- 核心功能介绍
- 快速安装步骤
- API 端点一览

### 第二步：实现 AI 规划助手（最重要）（30分钟阅读 + 1-2周开发）
📄 **docs/AI_PLANNING_AGENT_IMPLEMENTATION.md**
- 详细的架构设计
- 完整的代码示例
- 数据库 Schema 扩展
- 路由实现细节
- 工作流程示例

**关键任务：**
1. 在 `data/calendar_db.py` 中添加 `chat_messages` 和 `planning_drafts` 表
2. 创建 `services/planner_agent.py` 文件
3. 创建 `routes/chat_router.py` 文件
4. 在 `main.py` 中注册路由

### 第三步：实现用户画像（可选）（20分钟阅读 + 1周开发）
📄 **docs/USER_PROFILE_RECOMMENDATION_IMPLEMENTATION.md**
- 用户画像管理
- 内容爬虫实现
- 推荐引擎
- 后台任务

**关键任务：**
1. 添加用户兴趣表
2. 实现爬虫服务
3. 实现推荐路由

### 第四步：部署和运维（10分钟阅读）
📄 **docs/COMPLETE_SYSTEM_ARCHITECTURE.md**
- 系统架构概览
- 部署步骤
- 故障排查
- 性能优化

---

## 🚀 5分钟快速体验

### 前置准备
```bash
# 安装 Ollama
# 访问 https://ollama.ai 下载安装

# 拉取模型
ollama pull qwen3-vl:30b
```

### 启动应用
```bash
# 终端 1：启动 Ollama
ollama serve

# 终端 2：启动应用
cd calendar_backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload
```

### 测试 API
```bash
# 注册用户
curl -X POST http://localhost:5522/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username":"test","password":"pass123"}'

# 登录（获取 token）
curl -X POST http://localhost:5522/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"test","password":"pass123"}'

# 创建事件（测试基础功能）
curl -X POST http://localhost:5522/items/events \
  -H "Authorization: Bearer <your_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "title":"会议",
    "date":"2026-04-28",
    "time":"14:00"
  }'
```

### 在浏览器测试
访问 `http://localhost:5522/docs` 查看 API 文档

---

## 📁 我为你生成的文件

```
docs/
├── README.md                                      # 项目概述
├── AI_PLANNING_AGENT_IMPLEMENTATION.md           # AI 规划助手详细文档
├── USER_PROFILE_RECOMMENDATION_IMPLEMENTATION.md # 用户画像和推荐详细文档
├── COMPLETE_SYSTEM_ARCHITECTURE.md               # 系统架构和部署指南
└── QUICK_START.md                                # 本文件

// 待实现的文件
services/
├── planner_agent.py                  # AI 规划助手
├── content_crawler.py                # 内容爬虫
├── recommendation_engine.py          # 推荐引擎
└── background_tasks.py               # 后台任务

routes/
├── chat_router.py                    # 对话路由
├── profile_router.py                 # 用户画像路由
└── recommendations_router.py         # 推荐路由
```

---

## 🎯 实现顺序建议

### Week 1: AI 规划助手基础
- [ ] Day 1-2: 研究文档，设计数据库 Schema
- [ ] Day 3-4: 实现 `planner_agent.py`
- [ ] Day 5: 实现 `chat_router.py`
- [ ] Day 6-7: 测试和集成

### Week 2: AI 规划助手完善
- [ ] Day 1-2: 冲突检测和空闲时间分析
- [ ] Day 3-4: 前端对话界面开发
- [ ] Day 5-7: 测试和优化

### Week 3: 用户画像（可选）
- [ ] Day 1-2: 用户兴趣管理
- [ ] Day 3-4: 前端编辑界面
- [ ] Day 5-7: 测试

### Week 4-6: 内容推荐（可选）
- [ ] Week 4: 爬虫实现
- [ ] Week 5: 推荐引擎
- [ ] Week 6: 后台任务和前端推荐展示

---

## 💡 实现技巧

### 1. 数据库扩展
```python
# 在 data/calendar_db.py 的 init_db() 中添加你的 SQL
# 遵循现有的表设计模式

CREATE TABLE IF NOT EXISTS your_table (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT NOT NULL,
    -- 添加你的字段
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_your_table_user ON your_table(user_id);
```

### 2. 实现路由
```python
# 遵循现有的路由模式
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/your_prefix", tags=["your_tag"])

class YourSchema(BaseModel):
    # 定义请求/响应模型
    pass

@router.get("")
async def your_endpoint(
    session: SessionPrincipal = Depends(get_current_session)
):
    # 实现逻辑
    pass
```

### 3. 调用 Ollama
```python
# 已有的 ollama 模块可直接使用
from services import ollama

messages = [
    {"role": "system", "content": "..."},
    {"role": "user", "content": "..."}
]
response = await ollama.chat(messages)
```

### 4. 错误处理
```python
# 遵循现有的错误处理模式
from services.ollama import (
    OllamaUnavailableError,
    OllamaTimeoutError,
    OllamaModelNotFoundError
)

try:
    result = await ollama.chat(messages)
except OllamaUnavailableError:
    raise HTTPException(status_code=503, detail="Ollama 服务不可达")
```

---

## 📊 开发检查清单

### 第一阶段：AI 规划助手
- [ ] 数据库表创建成功
- [ ] 能够保存和检索对话记录
- [ ] AI 能生成规划建议
- [ ] 草稿导入正常工作
- [ ] API 文档完整
- [ ] 单元测试通过
- [ ] 集成测试通过

### 第二阶段：用户画像
- [ ] 兴趣标签增删改查工作
- [ ] 权重配置有效
- [ ] 前端管理界面完成
- [ ] 用户隔离正确

### 第三阶段：推荐系统
- [ ] 爬虫能正常获取内容
- [ ] 推荐引擎计算分数正确
- [ ] 后台任务定时运行
- [ ] 推荐结果相关度高

---

## 🔍 调试技巧

### 查看应用日志
```python
# 在 main.py 中添加日志配置
import logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
```

### 数据库查询
```bash
# 连接数据库
sqlite3 data/calendar.db

# 查看表结构
.schema table_name

# 查询数据
SELECT * FROM table_name WHERE user_id='xxx';
```

### 测试 API
```bash
# 使用 curl
curl -v http://localhost:5522/your-endpoint

# 使用 httpie
http POST http://localhost:5522/your-endpoint

# 使用 Postman
导入 API 集合并测试
```

### 性能分析
```python
# 添加计时装饰器
import time
from functools import wraps

def timer(func):
    @wraps(func)
    async def wrapper(*args, **kwargs):
        start = time.time()
        result = await func(*args, **kwargs)
        print(f"{func.__name__} 耗时: {time.time() - start:.2f}s")
        return result
    return wrapper
```

---

## 📞 常见问题

### Q: 如何修改爬虫的搜索关键词？
A: 在 `services/background_tasks.py` 中的爬虫方法里修改关键词列表

### Q: 推荐算法如何调整权重？
A: 修改 `services/recommendation_engine.py` 中的权重计算逻辑

### Q: 如何增加新的内容来源？
A: 在 `services/content_crawler.py` 中继承 `ContentCrawler` 基类实现新爬虫

### Q: 如何改变爬虫运行频率？
A: 修改 `services/background_tasks.py` 中的 `CronTrigger` 参数

### Q: 如何限制 API 访问速率？
A: 使用 `slowapi` 库在路由上添加 `@limiter.limit()` 装饰器

---

## 📚 推荐学习资源

### 必读
- [FastAPI 官方教程](https://fastapi.tiangolo.com/zh/)
- [Pydantic 文档](https://docs.pydantic.dev/)
- [SQLite 官方文档](https://www.sqlite.org/docs.html)

### 可选
- [Ollama 项目介绍](https://github.com/ollama/ollama)
- [APScheduler 文档](https://apscheduler.readthedocs.io/)
- [arXiv API 使用](https://arxiv.org/help/api)

---

## ✅ 完成检验

当你完成实现后，应该能够：

1. ✅ 启动应用并访问 API 文档
2. ✅ 创建用户和登录
3. ✅ 与 AI 进行规划对话
4. ✅ 生成和确认规划草稿
5. ✅ 设置用户兴趣标签
6. ✅ 接收个性化推荐内容
7. ✅ 查看爬虫运行日志

---

## 🎉 下一步行动

1. **立即开始**：
   - 仔细阅读 `AI_PLANNING_AGENT_IMPLEMENTATION.md`
   - 运行现有代码确保环境配置正确
   - 开始实现第一个新功能

2. **每天进度**：
   - 早：规划当天任务
   - 中：编写和测试代码
   - 晚：代码审查和文档更新

3. **遇到问题**：
   - 查看 `COMPLETE_SYSTEM_ARCHITECTURE.md` 的故障排查部分
   - 检查日志文件
   - 参考相似的代码实现

---

## 📞 需要帮助？

- 问题 1：API 端点不工作 → 检查 `main.py` 的路由注册
- 问题 2：数据库错误 → 查看 `data/calendar_db.py` 的 SQL 脚本
- 问题 3：AI 不响应 → 检查 Ollama 是否运行
- 问题 4：推荐为空 → 查看爬虫日志和用户兴趣

---

**祝你开发顺利！** 🚀

如果有任何问题，欢迎随时提问。

