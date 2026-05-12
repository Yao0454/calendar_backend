# 用户隔离 - 快速参考

## 🎬 一句话总结

**每个用户有唯一的 user_id，所有数据操作都必须带上 user_id 进行过滤。**

---

## 🔄 4步流程

```
1️⃣ 注册 
   用户提交 username + password
   → 系统生成唯一 UUID 作为 user_id
   → 保存到 data/db/users.json

2️⃣ 登录
   用户提交 username + password  
   → 系统验证，创建会话
   → 会话包含 user_id（这很关键！）
   → 返回 session_id 作为 token

3️⃣ 请求时
   客户端: Authorization: Bearer {session_id}
   → 服务器验证 session_id 有效
   → 从会话中提取 user_id

4️⃣ 数据库查询
   使用 user_id 过滤：WHERE user_id = ?
   → 确保只返回该用户的数据
```

---

## 🛡️ 三层防护

```
Layer 1: 认证层 (auth/deps.py)
├─ 验证 token 是否有效
├─ 验证 token 是否过期
└─ 返回包含 user_id 的 SessionPrincipal

    ↓

Layer 2: 路由层 (routes/*.py)
├─ 从 session 提取 user_id
├─ 传给服务层或数据库函数
└─ 确保不会漏掉 user_id

    ↓

Layer 3: 数据库层 (data/calendar_db.py)
├─ SQL 中必须有 WHERE user_id = ?
├─ DELETE/UPDATE 也要验证 user_id
└─ 数据库级别强制隔离
```

---

## 📝 新功能的 4点检查清单

### ✅ 1. 新表要有 user_id

```python
CREATE TABLE my_table (
    id       INTEGER PRIMARY KEY,
    user_id  TEXT NOT NULL,     ← 必须有！
    ...
);
CREATE INDEX idx_my_user ON my_table(user_id);  ← 性能优化
```

### ✅ 2. SELECT 要有 WHERE user_id

```python
def get_my_data(user_id: str):
    c.execute(
        "SELECT * FROM my_table WHERE user_id=?",  ← user_id 过滤
        (user_id,)
    )
```

### ✅ 3. DELETE/UPDATE 要验证所有权

```python
def delete_my_data(item_id: int, user_id: str):
    return c.execute(
        "DELETE FROM my_table WHERE id=? AND user_id=?",  ← 两个条件！
        (item_id, user_id)
    ).rowcount > 0
```

### ✅ 4. 路由层要传 user_id

```python
@router.delete("/my-data/{item_id}")
def delete(
    item_id: int,
    session: SessionPrincipal = Depends(get_current_session)  ← 认证
):
    if not my_service.delete(item_id, session.user_id):  ← 传 user_id
        raise HTTPException(404)
```

---

## ❌ 常见错误

| 错误 | 后果 | 如何避免 |
|------|------|--------|
| 忘记传 user_id | 数据隐私泄露 | 所有函数都要有 user_id 参数 |
| 查询没有 WHERE user_id | 返回所有用户数据 | 养成习惯，SQL 中总是加 WHERE user_id = ? |
| 删除只检查 id | 用户可删除别人数据 | DELETE 必须同时检查 id AND user_id |
| 从 URL 读 user_id | 用户可伪造身份 | 只从 session 获取 user_id |

---

## 🧪 测试

### 测试 1：两个用户的数据不混淆

```bash
# 用户 A 登录，获取数据
curl -H "Authorization: Bearer token_a" http://api/items
→ 只返回 A 的日程

# 用户 B 登录，获取数据
curl -H "Authorization: Bearer token_b" http://api/items
→ 只返回 B 的日程（不包含 A 的）
```

### 测试 2：过期 token 被拒绝

```bash
curl -H "Authorization: Bearer expired_token" http://api/items
→ 401 Unauthorized
```

### 测试 3：用户不能删除别人的数据

```bash
# 用户 B 尝试删除用户 A 创建的日程（id=1）
curl -X DELETE -H "Authorization: Bearer token_b" http://api/items/events/1
→ 404 Not Found (因为 WHERE user_id=token_b AND id=1 找不到)
```

---

## 💡 核心要点速记

| 要素 | 位置 | 说明 |
|------|------|------|
| **用户 ID** | users.json | 唯一标识，UUID 格式 |
| **会话** | sessions.json | 包含 user_id，30 天过期 |
| **认证** | auth/deps.py | get_current_session() |
| **提取 user_id** | routes/*.py | session.user_id |
| **数据过滤** | data/calendar_db.py | WHERE user_id = ? |

---

## 🎯 如果你要加功能

### 简单功能（不需要新表）
→ 在现有的 events/todos 表操作
→ 只需要确保路由层传了 user_id

### 新增功能（需要新表）
→ 新表加 user_id 字段和索引
→ 所有操作都按照 4 点检查清单做
→ 完成！用户隔离自动生效

---

## 📚 详细文档

- 完整讲解：`USER_ISOLATION.md`（512 行）
- 所有接口：`API_DOCUMENTATION.md`
- 项目结构：`PROJECT_STRUCTURE.md`
- 大模型原则：`API_DOCUMENTATION.md` 第 5 部分

---

## ✨ 最后一句话

只要你记住这个模板，加功能时就不会搞错用户隔离：

```python
# 1. 新表加 user_id
# 2. 查询加 WHERE user_id = ?
# 3. 删除/更新加 AND user_id = ?
# 4. 路由层传 session.user_id
```

完成！🎉
