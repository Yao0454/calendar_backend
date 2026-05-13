# Calendar Backend API 接口文档

## 基础信息

- **Base URL**: `http://localhost:5522`
- **认证方式**: Bearer Token (JWT)
- **数据格式**: JSON
- **编码**: UTF-8

---

## 目录

1. [认证相关](#1-认证相关)
2. [日程管理](#2-日程管理)
3. [AI规划助手](#3-ai规划助手)
4. [用户画像](#4-用户画像)
5. [推荐系统](#5-推荐系统)
6. [arXiv日报](#6-arxiv日报)

---

## 1. 认证相关

### 1.1 用户注册

**接口名称**：用户注册

**功能描述**：创建新用户账号

**请求方法**：POST

**URL地址**：`/auth/register`

**请求参数**：

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| username | string | 是 | 用户名，3-20字符 |
| password | string | 是 | 密码，6-50字符 |

**请求示例**：
```json
{
  "username": "testuser",
  "password": "password123"
}
```

**响应格式**：

**成功响应** (201 Created)：
```json
{
  "message": "User registered successfully",
  "username": "testuser"
}
```

**错误响应** (400 Bad Request)：
```json
{
  "detail": "Username already exists"
}
```

**错误码说明**：

| 状态码 | 说明 |
|--------|------|
| 201 | 注册成功 |
| 400 | 用户名已存在或参数错误 |

---

### 1.2 用户登录

**接口名称**：用户登录

**功能描述**：用户登录获取访问令牌

**请求方法**：POST

**URL地址**：`/auth/login`

**请求参数**：

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| username | string | 是 | 用户名 |
| password | string | 是 | 密码 |

**请求示例**：
```json
{
  "username": "testuser",
  "password": "password123"
}
```

**响应格式**：

**成功响应** (200 OK)：
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "username": "testuser"
}
```

**错误响应** (401 Unauthorized)：
```json
{
  "detail": "Invalid credentials"
}
```

**错误码说明**：

| 状态码 | 说明 |
|--------|------|
| 200 | 登录成功 |
| 401 | 用户名或密码错误 |

---

## 2. 日程管理

### 2.1 获取日程列表

**接口名称**：获取日程列表

**功能描述**：获取用户的所有事件和待办事项

**请求方法**：GET

**URL地址**：`/items/`

**认证**：需要Bearer Token

**请求参数**：无

**请求示例**：
```bash
curl -X GET "http://localhost:5522/items/" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

**响应格式**：

**成功响应** (200 OK)：
```json
{
  "events": [
    {
      "id": 1,
      "user_id": "user123",
      "title": "团队会议",
      "date": "2026-05-15",
      "time": "14:00",
      "location": "会议室A",
      "notes": "讨论项目进度",
      "is_pinned": false,
      "created_at": "2026-05-13T10:00:00",
      "updated_at": "2026-05-13T10:00:00"
    }
  ],
  "todos": [
    {
      "id": 1,
      "user_id": "user123",
      "title": "完成报告",
      "deadline": "2026-05-20",
      "priority": "high",
      "notes": "季度总结报告",
      "is_done": false,
      "is_pinned": true,
      "created_at": "2026-05-13T10:00:00",
      "updated_at": "2026-05-13T10:00:00"
    }
  ]
}
```

**错误码说明**：

| 状态码 | 说明 |
|--------|------|
| 200 | 获取成功 |
| 401 | 未授权 |

---

### 2.2 创建事件

**接口名称**：创建事件

**功能描述**：创建新的日程事件

**请求方法**：POST

**URL地址**：`/items/events`

**认证**：需要Bearer Token

**请求参数**：

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| title | string | 是 | 事件标题 |
| date | string | 是 | 日期（YYYY-MM-DD） |
| time | string | 否 | 时间（HH:MM） |
| location | string | 否 | 地点 |
| notes | string | 否 | 备注 |

**请求示例**：
```json
{
  "title": "项目评审会议",
  "date": "2026-05-20",
  "time": "15:00",
  "location": "会议室B",
  "notes": "评审第一阶段成果"
}
```

**响应格式**：

**成功响应** (201 Created)：
```json
{
  "id": 2,
  "user_id": "user123",
  "title": "项目评审会议",
  "date": "2026-05-20",
  "time": "15:00",
  "location": "会议室B",
  "notes": "评审第一阶段成果",
  "is_pinned": false,
  "created_at": "2026-05-13T11:00:00",
  "updated_at": "2026-05-13T11:00:00"
}
```

**错误码说明**：

| 状态码 | 说明 |
|--------|------|
| 201 | 创建成功 |
| 400 | 参数错误 |
| 401 | 未授权 |

---

### 2.3 创建待办

**接口名称**：创建待办事项

**功能描述**：创建新的待办任务

**请求方法**：POST

**URL地址**：`/items/todos`

**认证**：需要Bearer Token

**请求参数**：

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| title | string | 是 | 待办标题 |
| deadline | string | 是 | 截止日期（YYYY-MM-DD） |
| priority | string | 否 | 优先级（high/medium/low），默认medium |
| notes | string | 否 | 备注 |

**请求示例**：
```json
{
  "title": "学习PyTorch",
  "deadline": "2026-05-30",
  "priority": "high",
  "notes": "完成官方教程"
}
```

**响应格式**：

**成功响应** (201 Created)：
```json
{
  "id": 2,
  "user_id": "user123",
  "title": "学习PyTorch",
  "deadline": "2026-05-30",
  "priority": "high",
  "notes": "完成官方教程",
  "is_done": false,
  "is_pinned": false,
  "created_at": "2026-05-13T11:00:00",
  "updated_at": "2026-05-13T11:00:00"
}
```

---

## 3. AI规划助手

### 3.1 开始对话

**接口名称**：开始AI规划对话

**功能描述**：与AI助手开始新的规划对话

**请求方法**：POST

**URL地址**：`/chat/start`

**认证**：需要Bearer Token

**请求参数**：

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| user_request | string | 是 | 用户请求描述 |

**请求示例**：
```json
{
  "user_request": "我想在2周内学习完Python基础"
}
```

**响应格式**：

**成功响应** (201 Created)：
```json
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "ai_response": "好的，我来帮你制定一个2周的Python学习计划...",
  "schedule_context": "当前日期：2026-05-13\n\n【现有日程】\n..."
}
```

**错误响应** (503 Service Unavailable)：
```json
{
  "detail": "Ollama 服务不可达"
}
```

**错误码说明**：

| 状态码 | 说明 |
|--------|------|
| 201 | 对话开始成功 |
| 503 | Ollama服务不可用 |
| 504 | Ollama推理超时 |

---

### 3.2 发送消息

**接口名称**：继续对话

**功能描述**：在现有会话中发送消息

**请求方法**：POST

**URL地址**：`/chat/message`

**认证**：需要Bearer Token

**请求参数**：

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| session_id | string | 是 | 会话ID |
| message | string | 是 | 用户消息 |

**请求示例**：
```json
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "message": "这个计划看起来不错，能详细说明第一周的学习内容吗？"
}
```

**响应格式**：

**成功响应** (200 OK)：
```json
{
  "message": "这个计划看起来不错...",
  "ai_response": "当然可以，第一周我们将重点学习..."
}
```

---

### 3.3 创建规划草稿

**接口名称**：创建规划草稿

**功能描述**：从对话生成可导入的规划草稿

**请求方法**：POST

**URL地址**：`/chat/draft`

**认证**：需要Bearer Token

**请求参数**：

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| session_id | string | 是 | 会话ID |
| message | string | 是 | 确认消息 |

**请求示例**：
```json
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "message": "我确认这个规划方案"
}
```

**响应格式**：

**成功响应** (200 OK)：
```json
{
  "draft_id": 1,
  "draft": {
    "id": 1,
    "user_id": "user123",
    "title": "AI规划方案",
    "description": "基于对话的规划方案",
    "proposed_events": [
      {
        "title": "Python基础学习",
        "date": "2026-05-20",
        "time": "19:00"
      }
    ],
    "proposed_todos": [
      {
        "title": "完成Python教程",
        "deadline": "2026-05-25",
        "priority": "high"
      }
    ],
    "status": "draft"
  }
}
```

---

### 3.4 确认草稿

**接口名称**：确认并导入草稿

**功能描述**：确认草稿并导入到日程表

**请求方法**：POST

**URL地址**：`/chat/confirm/{draft_id}`

**认证**：需要Bearer Token

**路径参数**：

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| draft_id | integer | 是 | 草稿ID |

**请求参数**：

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| draft_id | integer | 是 | 草稿ID |
| confirm | boolean | 是 | 是否确认（true/false） |

**请求示例**：
```json
{
  "draft_id": 1,
  "confirm": true
}
```

**响应格式**：

**成功响应** (200 OK)：
```json
{
  "status": "confirmed",
  "events_imported": 2,
  "todos_imported": 3,
  "data": {
    "draft_id": 1,
    "events": [...],
    "todos": [...]
  }
}
```

---

## 4. 用户画像

### 4.1 获取兴趣列表

**接口名称**：获取用户兴趣标签

**功能描述**：获取用户的所有兴趣标签

**请求方法**：GET

**URL地址**：`/profile/interests`

**认证**：需要Bearer Token

**查询参数**：

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| category | string | 否 | 分类过滤（research/project/skill） |

**请求示例**：
```bash
curl -X GET "http://localhost:5522/profile/interests?category=research" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

**响应格式**：

**成功响应** (200 OK)：
```json
{
  "user_id": "user123",
  "interests": [
    {
      "id": 1,
      "user_id": "user123",
      "category": "research",
      "tag": "Machine Learning",
      "keywords": ["deep learning", "neural network", "AI"],
      "weight": 0.9,
      "created_at": "2026-05-13T10:00:00",
      "updated_at": "2026-05-13T10:00:00"
    }
  ],
  "total": 1
}
```

---

### 4.2 添加兴趣标签

**接口名称**：添加兴趣标签

**功能描述**：手动添加用户兴趣标签

**请求方法**：POST

**URL地址**：`/profile/interests`

**认证**：需要Bearer Token

**请求参数**：

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| category | string | 是 | 分类（research/project/skill） |
| tag | string | 是 | 标签名称 |
| keywords | array | 是 | 关键词列表 |
| weight | number | 否 | 权重（0-1），默认1.0 |

**请求示例**：
```json
{
  "category": "skill",
  "tag": "Python",
  "keywords": ["python", "programming", "coding"],
  "weight": 0.8
}
```

**响应格式**：

**成功响应** (201 Created)：
```json
{
  "status": "created",
  "interest": {
    "id": 2,
    "user_id": "user123",
    "category": "skill",
    "tag": "Python",
    "keywords": ["python", "programming", "coding"],
    "weight": 0.8,
    "created_at": "2026-05-13T11:00:00",
    "updated_at": "2026-05-13T11:00:00"
  }
}
```

---

### 4.3 获取画像摘要

**接口名称**：获取用户画像摘要

**功能描述**：获取用户画像的统计摘要

**请求方法**：GET

**URL地址**：`/profile/summary`

**认证**：需要Bearer Token

**响应格式**：

**成功响应** (200 OK)：
```json
{
  "user_id": "user123",
  "total_interests": 5,
  "summary": {
    "research": ["Machine Learning", "Computer Vision"],
    "project": ["Web Development"],
    "skill": ["Python", "PyTorch"]
  }
}
```

---

## 5. 推荐系统

### 5.1 获取推荐列表

**接口名称**：获取推荐内容

**功能描述**：获取为用户生成的推荐内容列表

**请求方法**：GET

**URL地址**：`/recommendations/feed`

**认证**：需要Bearer Token

**查询参数**：

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| unread_only | boolean | 否 | 仅未读内容，默认false |
| limit | integer | 否 | 每页数量，默认20 |
| offset | integer | 否 | 偏移量，默认0 |

**请求示例**：
```bash
curl -X GET "http://localhost:5522/recommendations/feed?unread_only=true&limit=10" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

**响应格式**：

**成功响应** (200 OK)：
```json
{
  "total": 50,
  "limit": 10,
  "offset": 0,
  "items": [
    {
      "id": 1,
      "user_id": "user123",
      "content_id": 100,
      "recommendation_score": 0.85,
      "read": 0,
      "saved": 0,
      "source": "arxiv",
      "title": "Deep Learning for Computer Vision",
      "description": "A comprehensive survey...",
      "url": "https://arxiv.org/abs/2301.12345",
      "author": "John Doe",
      "published_date": "2026-05-10",
      "content_type": "paper",
      "tags": ["cs.CV", "cs.LG"]
    }
  ]
}
```

---

### 5.2 标记已读

**接口名称**：标记推荐为已读

**功能描述**：将推荐内容标记为已读

**请求方法**：POST

**URL地址**：`/recommendations/{content_id}/read`

**认证**：需要Bearer Token

**路径参数**：

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| content_id | integer | 是 | 内容ID |

**响应格式**：

**成功响应** (200 OK)：
```json
{
  "status": "marked_read"
}
```

---

### 5.3 收藏内容

**接口名称**：收藏推荐内容

**功能描述**：收藏推荐的内容

**请求方法**：POST

**URL地址**：`/recommendations/{content_id}/save`

**认证**：需要Bearer Token

**路径参数**：

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| content_id | integer | 是 | 内容ID |

**响应格式**：

**成功响应** (200 OK)：
```json
{
  "status": "saved"
}
```

---

### 5.4 获取推荐统计

**接口名称**：获取推荐统计

**功能描述**：获取用户的推荐统计信息

**请求方法**：GET

**URL地址**：`/recommendations/stats/summary`

**认证**：需要Bearer Token

**响应格式**：

**成功响应** (200 OK)：
```json
{
  "total_recommendations": 100,
  "unread": 75,
  "saved": 10,
  "by_source": {
    "arxiv": {
      "total": 50,
      "unread": 40
    },
    "github": {
      "total": 50,
      "unread": 35
    }
  }
}
```

---

## 6. arXiv日报

### 6.1 获取偏好设置

**接口名称**：获取日报偏好

**功能描述**：获取用户的日报偏好设置

**请求方法**：GET

**URL地址**：`/arxiv/preference`

**认证**：需要Bearer Token

**响应格式**：

**成功响应** (200 OK)：
```json
{
  "user_id": "user123",
  "push_time": "09:00",
  "paper_count": 5,
  "categories": ["cs.AI", "cs.LG"],
  "is_enabled": true
}
```

---

### 6.2 更新偏好设置

**接口名称**：更新日报偏好

**功能描述**：更新用户的日报偏好设置

**请求方法**：POST

**URL地址**：`/arxiv/preference`

**认证**：需要Bearer Token

**请求参数**：

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| push_time | string | 否 | 推送时间（HH:MM），默认09:00 |
| paper_count | integer | 否 | 论文数量，默认5 |
| categories | array | 否 | 领域分类，默认["cs.AI", "cs.LG"] |
| is_enabled | boolean | 否 | 是否启用，默认true |

**请求示例**：
```json
{
  "push_time": "08:00",
  "paper_count": 10,
  "categories": ["cs.AI", "cs.CV", "cs.LG"],
  "is_enabled": true
}
```

**响应格式**：

**成功响应** (200 OK)：
```json
{
  "status": "updated",
  "preference": {
    "user_id": "user123",
    "push_time": "08:00",
    "paper_count": 10,
    "categories": ["cs.AI", "cs.CV", "cs.LG"],
    "is_enabled": true
  }
}
```

---

### 6.3 生成日报

**接口名称**：生成日报

**功能描述**：手动触发生成日报

**请求方法**：POST

**URL地址**：`/arxiv/report/generate`

**认证**：需要Bearer Token

**查询参数**：

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| report_date | string | 否 | 日期（YYYY-MM-DD），默认今天 |

**响应格式**：

**成功响应** (200 OK)：
```json
{
  "status": "success",
  "report": {
    "id": 1,
    "user_id": "user123",
    "report_date": "2026-05-13",
    "summary": "# arXiv 学术日报\n\n## 今日推荐论文\n...",
    "paper_ids": [1, 2, 3, 4, 5],
    "html_content": "<h1>arXiv 学术日报</h1>...",
    "download_count": 0
  },
  "paper_count": 5
}
```

**跳过响应** (200 OK)：
```json
{
  "status": "skipped",
  "message": "没有可用的推荐内容"
}
```

---

### 6.4 获取今日日报

**接口名称**：获取今日日报

**功能描述**：获取今天的日报内容

**请求方法**：GET

**URL地址**：`/arxiv/report/today`

**认证**：需要Bearer Token

**响应格式**：

**成功响应** (200 OK)：
```json
{
  "report": {
    "id": 1,
    "user_id": "user123",
    "report_date": "2026-05-13",
    "summary": "# arXiv 学术日报\n...",
    "paper_ids": [1, 2, 3, 4, 5],
    "html_content": "<h1>arXiv 学术日报</h1>...",
    "download_count": 0
  }
}
```

**错误响应** (404 Not Found)：
```json
{
  "detail": "今日日报尚未生成"
}
```

---

### 6.5 获取日报列表

**接口名称**：获取日报列表

**功能描述**：获取用户的历史日报列表

**请求方法**：GET

**URL地址**：`/arxiv/reports`

**认证**：需要Bearer Token

**查询参数**：

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| limit | integer | 否 | 数量限制，默认30 |

**响应格式**：

**成功响应** (200 OK)：
```json
{
  "total": 10,
  "reports": [
    {
      "id": 1,
      "user_id": "user123",
      "report_date": "2026-05-13",
      "summary": "# arXiv 学术日报\n...",
      "download_count": 5
    }
  ]
}
```

---

## 通用错误码

| 状态码 | 说明 |
|--------|------|
| 200 | 请求成功 |
| 201 | 创建成功 |
| 204 | 删除成功（无返回内容） |
| 400 | 请求参数错误 |
| 401 | 未授权（未登录或token无效） |
| 403 | 禁止访问（权限不足） |
| 404 | 资源不存在 |
| 500 | 服务器内部错误 |
| 503 | 服务不可用（如Ollama未启动） |
| 504 | 服务超时（如AI推理超时） |

---

## 认证说明

### 获取Token
1. 先调用 `/auth/register` 注册账号
2. 调用 `/auth/login` 登录获取token
3. 在后续请求中添加Authorization头

### 使用Token
```bash
curl -X GET "http://localhost:5522/items/" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

---

## 调用示例

### 完整工作流示例

```bash
# 1. 注册
curl -X POST "http://localhost:5522/auth/register" \
  -H "Content-Type: application/json" \
  -d '{"username":"test","password":"pass123"}'

# 2. 登录
TOKEN=$(curl -X POST "http://localhost:5522/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"username":"test","password":"pass123"}' \
  | jq -r '.access_token')

# 3. 开始AI规划
curl -X POST "http://localhost:5522/chat/start" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"user_request":"我想学习Python"}'

# 4. 获取推荐
curl -X GET "http://localhost:5522/recommendations/feed" \
  -H "Authorization: Bearer $TOKEN"

# 5. 添加兴趣标签
curl -X POST "http://localhost:5522/profile/interests" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"category":"skill","tag":"Python","keywords":["python","coding"]}'
```

---

**文档版本**：v1.0  
**最后更新**：2026-05-13  
**API版本**：v1.0
