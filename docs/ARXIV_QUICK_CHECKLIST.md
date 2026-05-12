# arXiv 日报功能 - 快速开发清单

## 📋 7 步开发流程

### Step 1️⃣: 数据库 (data/calendar_db.py)
**时间**: 30-45 分钟

```python
# ✅ 添加 3 个新表的 SQL
# ✅ 添加 8 个新的 CRUD 函数
# ✅ 在顶部导入 json
```

**关键函数**:
- `get_arxiv_preference()` - 获取偏好
- `create_or_update_arxiv_preference()` - 保存偏好
- `create_or_update_paper()` - 保存论文
- `get_papers_by_date_and_category()` - 查询论文
- `create_daily_report()` - 创建日报
- `get_daily_report()` / `get_daily_reports_list()` - 查询日报
- `increment_report_download()` - 统计下载

---

### Step 2️⃣: 获取论文 (services/arxiv_fetcher.py)
**时间**: 15-20 分钟

```python
# ✅ 创建新文件
# ✅ 2 个异步函数：
#    - fetch_papers_by_date_and_categories()
#    - download_paper_text()
```

**要点**:
- 使用 `feedparser` 解析 arXiv RSS
- 支持按日期和领域查询
- 返回论文列表（标题、作者、摘要等）

---

### Step 3️⃣: 生成日报 (services/report_generator.py)
**时间**: 20-30 分钟

```python
# ✅ 创建新文件
# ✅ 3 个函数：
#    - generate_daily_report() - 用大模型生成摘要
#    - _markdown_to_html() - 转换格式
#    - generate_pdf_report() - 可选，生成 PDF
```

**要点**:
- 使用 Ollama 生成专业日报
- 支持 Markdown 和 HTML 格式
- Prompt 已写好，直接用

---

### Step 4️⃣: 定时任务 (services/scheduler.py)
**时间**: 15-20 分钟

```python
# ✅ 创建新文件
# ✅ 4 个函数：
#    - init_scheduler() - 启动定时器
#    - shutdown_scheduler() - 关闭定时器
#    - add_daily_report_job() - 添加任务
#    - remove_daily_report_job() - 移除任务
```

**要点**:
- 使用 APScheduler 库
- 每天固定时间生成日报
- 支持动态修改时间

---

### Step 5️⃣: API 接口 (routes/arxiv_router.py)
**时间**: 25-35 分钟

```python
# ✅ 创建新文件
# ✅ 7 个 API 端点：
#    - GET /arxiv/preferences - 获取偏好
#    - POST /arxiv/preferences - 更新偏好
#    - GET /arxiv/reports - 日报列表
#    - GET /arxiv/reports/{date} - 查看日报
#    - GET /arxiv/reports/{date}/download - 下载日报
#    - GET /arxiv/reports/{date}/download-papers - 下载论文
#    - POST /arxiv/manual-generate-report - 手动生成（测试）
```

**用户隔离检查**:
- [ ] 所有端点都用 `Depends(get_current_session)`
- [ ] 所有数据库查询都带 `session.user_id`
- [ ] 每个端点验证所有权

---

### Step 6️⃣: 集成主应用 (main.py)
**时间**: 5-10 分钟

```python
# ✅ 在顶部导入：
from services import scheduler
from routes import arxiv_router

# ✅ 在 lifespan 中：
scheduler.init_scheduler()  # 启动时初始化
scheduler.shutdown_scheduler()  # 关闭时清理

# ✅ 注册路由：
app.include_router(arxiv_router.router)
```

---

### Step 7️⃣: 安装依赖 (requirements.txt)
**时间**: 2-3 分钟

```bash
# ✅ 添加到 requirements.txt：
feedparser>=6.0.10          # 解析 RSS
apscheduler>=3.10.0         # 定时任务
reportlab>=4.0.0            # PDF（可选）
markdown2>=2.4.9            # Markdown 转 HTML

# ✅ 运行：
pip install -r requirements.txt
```

---

## ⏱️ 总耗时

- **数据库**: 30-45 分钟
- **获取论文**: 15-20 分钟
- **生成日报**: 20-30 分钟
- **定时任务**: 15-20 分钟
- **API 接口**: 25-35 分钟
- **集成**: 5-10 分钟
- **依赖**: 2-3 分钟
- **测试**: 30-60 分钟

**总计**: 2.5 - 4 小时（包含测试）

---

## 🧪 快速验证测试

### 1. 创建用户并设置偏好

```bash
# 注册
curl -X POST http://localhost:5522/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username":"test","password":"test123"}'

# 登录
curl -X POST http://localhost:5522/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"test","password":"test123"}'
# → 得到 session_id

# 设置偏好
curl -X POST http://localhost:5522/arxiv/preferences \
  -H "Authorization: Bearer {session_id}" \
  -H "Content-Type: application/json" \
  -d '{
    "push_time":"09:00",
    "paper_count":5,
    "categories":["cs.AI","cs.CV"],
    "is_enabled":true
  }'
# → 200 OK
```

### 2. 手动生成日报

```bash
curl -X POST http://localhost:5522/arxiv/manual-generate-report \
  -H "Authorization: Bearer {session_id}"
# → 生成日报（使用 Ollama 调用大模型，可能需要 30 秒）
```

### 3. 查看和下载

```bash
# 获取日报列表
curl http://localhost:5522/arxiv/reports \
  -H "Authorization: Bearer {session_id}"

# 查看某个日报
curl http://localhost:5522/arxiv/reports/2025-01-25 \
  -H "Authorization: Bearer {session_id}"

# 下载日报
curl http://localhost:5522/arxiv/reports/2025-01-25/download \
  -H "Authorization: Bearer {session_id}"
```

---

## ✅ 检查清单

### 数据库层
- [ ] 创建了 3 个新表（arxiv_preferences, papers, daily_reports）
- [ ] 添加了所有索引
- [ ] 编写了 8 个 CRUD 函数
- [ ] 测试了数据库操作

### 服务层
- [ ] 创建了 `arxiv_fetcher.py` - 获取论文正常
- [ ] 创建了 `report_generator.py` - 生成摘要正常
- [ ] 创建了 `scheduler.py` - 定时任务正常
- [ ] 所有异步函数都是 `async def`

### 路由层
- [ ] 创建了 `arxiv_router.py`
- [ ] 所有 7 个端点都实现了
- [ ] 所有端点都用了 `Depends(get_current_session)`
- [ ] 所有数据库查询都带了 `WHERE user_id = ?`

### 集成
- [ ] 修改了 `main.py` 导入和注册
- [ ] 修改了 `requirements.txt` 添加依赖
- [ ] 安装了新依赖（`pip install -r requirements.txt`）

### 用户隔离
- [ ] ✅ 所有新表都有 `user_id` 字段
- [ ] ✅ 所有 SELECT 都有 `WHERE user_id = ?`
- [ ] ✅ 所有 DELETE/UPDATE 都验证所有权
- [ ] ✅ 路由层都从 `session.user_id` 获取用户

### 测试
- [ ] 能正常创建用户和登录
- [ ] 能设置偏好并取回
- [ ] 能手动生成日报
- [ ] 能查看和下载日报
- [ ] 用户 A 看不到用户 B 的日报

---

## 🚀 开发建议

### 先做什么
1. **Step 1 (数据库)** - 最重要，为后续奠基
2. **Step 2 (获取论文)** - 确保能从 arXiv 拉到数据
3. **Step 3 (生成日报)** - 测试大模型调用
4. **Step 5 (API)** - 最早测试完整流程
5. **Step 4 (定时)** - 可以先跳过，后续再加

### 测试顺序
1. 数据库操作（直接查询数据库）
2. 获取论文函数（打印结果）
3. 生成日报函数（检查输出）
4. API 端点（使用 curl）
5. 完整流程（从设置到下载）

### 常见坑
- [ ] 忘记在 `main.py` 导入新模块 → `ImportError`
- [ ] 忘记添加依赖 → `ModuleNotFoundError`
- [ ] Ollama 没启动 → 大模型调用失败
- [ ] 忘记初始化数据库 → 找不到表
- [ ] 忘记用户隔离 → 用户可以看到别人数据

---

## 📖 文件导航

| 文件 | 行数 | 说明 |
|------|------|------|
| ARXIV_FEATURE_GUIDE.md | 1100+ | 完整指南（你现在看的） |
| data/calendar_db.py | +150 | 添加新表和函数 |
| services/arxiv_fetcher.py | ~80 | 新建，获取论文 |
| services/report_generator.py | ~120 | 新建，生成日报 |
| services/scheduler.py | ~100 | 新建，定时任务 |
| routes/arxiv_router.py | ~180 | 新建，所有接口 |
| main.py | +5 | 修改，集成模块 |
| requirements.txt | +4 | 修改，添加依赖 |

---

## 💡 参考代码已全部提供

你只需要：
1. ✅ 复制粘贴数据库代码到 `calendar_db.py`
2. ✅ 复制粘贴服务代码到各个 `services/*.py`
3. ✅ 复制粘贴路由代码到 `routes/arxiv_router.py`
4. ✅ 修改 `main.py` 和 `requirements.txt`
5. ✅ 运行测试

**所有代码都在 ARXIV_FEATURE_GUIDE.md 中，现成的！**

---

## 🎯 成功标志

当你看到这些，说明功能完成了：

```bash
# 1. 创建用户
curl -X POST http://localhost:5522/auth/register ...
→ {"ok": true, "message": "注册成功"}

# 2. 登录
curl -X POST http://localhost:5522/auth/login ...
→ {"session_id": "...", "username": "...", ...}

# 3. 设置偏好
curl -X POST http://localhost:5522/arxiv/preferences ...
→ {"push_time": "09:00", "paper_count": 5, ...}

# 4. 生成日报
curl -X POST http://localhost:5522/arxiv/manual-generate-report ...
→ {"id": 1, "report_date": "2025-01-25", "summary": "...", ...}

# 5. 下载日报
curl http://localhost:5522/arxiv/reports/2025-01-25/download ...
→ <HTML 或 PDF 内容>
```

祝你开发顺利！💪
