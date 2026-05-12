# 用户隔离机制详解

## 🎯 核心概念

这个项目通过**会话 + 用户ID**的方式实现用户隔离。每个用户有唯一的 `user_id`，所有数据操作都必须绑定这个 ID。

---

## 🔄 完整的用户隔离流程

### 第1步：用户注册 → 生成用户ID

```
用户提交: username + password
    ↓
auth_service.register()
    ├─ 生成唯一的 UUID 作为 user_id
    ├─ 密码加密成 bcrypt hash
    ├─ 存入 data/db/users.json
    └─ 返回: "注册成功"

data/db/users.json 中的数据:
{
  "id": "550e8400-e29b-41d4-a716-446655440000",  ← user_id
  "username": "john_doe",
  "password_hash": "$2b$12$...",
  "status": "active"
}
```

代码位置：`auth/auth_service.py`
```python
def register(self, username: str, password: str) -> bool:
    user = UserRecord(
        id=str(uuid.uuid4()),  ← 生成唯一 ID
        username=username,
        password_hash=PasswordService.hash_password(password),
        status="active",
    )
    self.users.save(user)
    return True
```

---

### 第2步：用户登录 → 创建会话

```
用户提交: username + password
    ↓
auth_service.login()
    ├─ 查找用户: self.users.get_by_username(username)
    ├─ 验证密码: PasswordService.verify(password, hash)
    ├─ 创建会话，存储 user_id
    └─ 返回: session_id (作为 Bearer Token)

data/db/sessions.json 中的数据:
{
  "session_id": "a1b2c3d4-e5f6...",  ← 登录后的 token
  "user_id": "550e8400-e29b-41d4-a716-446655440000",  ← 重要：关键到用户
  "username": "john_doe",
  "issued_at": "2025-01-25T10:30:00+00:00",
  "expires_at": "2025-02-24T10:30:00+00:00"  ← 30天过期
}
```

代码位置：`auth/auth_service.py`
```python
def login(self, username: str, password: str) -> SessionPrincipal | None:
    user = self.users.get_by_username(username)
    if not user or not PasswordService.verify(password, user.password_hash):
        return None
    
    now = datetime.now(UTC)
    session = SessionPrincipal(
        session_id=str(uuid.uuid4()),
        user_id=user.id,  ← 将 user_id 存入会话！
        username=user.username,
        issued_at=now,
        expires_at=now + timedelta(days=30),
    )
    self.sessions.create(session)
    return session
```

---

### 第3步：后续请求 → 验证会话并提取 user_id

```
客户端请求 + Header: Authorization: Bearer a1b2c3d4-e5f6...
    ↓
FastAPI 中间件: get_current_session()
    ├─ 从 Header 提取 token
    ├─ 查找 session_id 对应的会话
    ├─ 检查是否过期
    └─ 返回: SessionPrincipal 对象（包含 user_id）

SessionPrincipal 对象:
{
  session_id: "a1b2c3d4-e5f6...",
  user_id: "550e8400-e29b-41d4-a716-446655440000",  ← 用来隔离数据
  username: "john_doe",
  issued_at: datetime(...),
  expires_at: datetime(...)
}
```

代码位置：`auth/deps.py`
```python
def get_current_session(
    creds: HTTPAuthorizationCredentials = Depends(bearer),
) -> SessionPrincipal:
    if creds is None or creds.scheme.lower() != "bearer":
        raise HTTPException(status_code=401, detail="需要登录")
    
    session = _session_store.get(creds.credentials.strip())
    if session is None:
        raise HTTPException(status_code=401, detail="会话已过期")
    
    return session  # ← 返回包含 user_id 的对象
```

---

### 第4步：数据操作 → 使用 user_id 过滤

```
任何 API 端点都必须:
1. 通过 Depends(get_current_session) 获取 session
2. 从 session 提取 user_id
3. 传给数据库函数，进行 WHERE user_id = ? 过滤

例：获取当前用户的所有日程
```

代码位置：`routes/items_router.py`
```python
@router.get("")
def get_all(session: SessionPrincipal = Depends(get_current_session)):
    return {
        "events": db.get_events(session.user_id),  ← 传入 user_id
        "todos":  db.get_todos(session.user_id)    ← 传入 user_id
    }
```

代码位置：`data/calendar_db.py`
```python
def get_events(user_id: str) -> list[dict]:
    with _conn() as c:
        rows = c.execute(
            "SELECT * FROM events WHERE user_id=? ORDER BY ...",
            (user_id,),  ← SQL 中必须过滤 user_id！
        ).fetchall()
        return [dict(r) for r in rows]
```

---

## 📊 数据隔离的三层设计

### Layer 1️⃣：会话层 (认证)
- 文件：`auth/deps.py`
- 职责：验证请求，获取 `user_id`
- 防护：无效或过期的 token 会被拒绝

```python
# ✅ 正确：有效 token
curl -H "Authorization: Bearer valid_session_id" http://localhost:5522/items

# ❌ 错误：无效 token
curl -H "Authorization: Bearer invalid_token" http://localhost:5522/items
→ 401 Unauthorized
```

### Layer 2️⃣：路由层 (端点)
- 文件：`routes/items_router.py`
- 职责：接收 `session` 对象，提取 `user_id` 传给服务层
- 防护：忘记传 `user_id` 会导致查询为空

```python
# ✅ 正确：传入 user_id
db.get_events(session.user_id)

# ❌ 错误：没有过滤 user_id（会返回所有用户的数据！）
db.get_events()  # 这样会很危险
```

### Layer 3️⃣：数据库层 (查询)
- 文件：`data/calendar_db.py`
- 职责：所有 SQL 查询都必须包含 `WHERE user_id = ?`
- 防护：数据库级别的强制隔离

```sql
-- ✅ 正确：SQL 中有 WHERE user_id
SELECT * FROM events WHERE user_id = ? AND id = ?

-- ❌ 错误：没有 WHERE user_id（如果被调用，会泄露其他用户数据！）
SELECT * FROM events WHERE id = ?
```

---

## 🔐 安全性保障

### 保障 1：Token 验证
```python
# auth/deps.py - get_current_session()
# 如果 token 无效，直接拒绝，不会进入路由处理器
if session is None:
    raise HTTPException(status_code=401)
```

### 保障 2：Token 有有效期
```python
# auth/stores/session_store.py - get()
expires = datetime.fromisoformat(d["expires_at"])
if expires <= datetime.now(timezone.utc):
    return None  # 过期的 token 被当成无效处理
```

### 保障 3：SQL 参数化查询
```python
# data/calendar_db.py - 所有查询都用 ? 占位符
c.execute(
    "SELECT * FROM events WHERE user_id=? AND id=?",
    (user_id, event_id),  # 参数化，防止 SQL 注入
)
```

### 保障 4：URL 路径参数验证
```python
# routes/items_router.py - 删除日程
@router.delete("/events/{event_id}")
def delete_event(event_id: int, session: SessionPrincipal = Depends(get_current_session)):
    # delete_event() 内部会检查 user_id，确保用户只能删除自己的日程
    if not db.delete_event(event_id, session.user_id):
        raise HTTPException(404, "Not found")
```

---

## 💡 如何在新功能中正确使用用户隔离

### ✅ 正确做法 1：所有查询都要传 user_id

```python
# services/my_new_feature.py
from data import calendar_db

def analyze_user_schedule(user_id: str) -> dict:
    """分析某个用户的日程"""
    # ✅ 正确：显式传入 user_id
    events = calendar_db.get_events(user_id)
    todos = calendar_db.get_todos(user_id)
    
    return {
        "total_events": len(events),
        "completed_todos": sum(1 for t in todos if t["is_done"])
    }
```

```python
# routes/my_new_feature_router.py
@router.post("/analyze")
def analyze(session: SessionPrincipal = Depends(get_current_session)):
    # ✅ 正确：从 session 获取 user_id，传给服务
    result = analyze_user_schedule(session.user_id)
    return result
```

---

### ✅ 正确做法 2：新增数据库表也要包含 user_id

```python
# data/calendar_db.py - 新增表时
def init_db() -> None:
    with _conn() as c:
        c.executescript("""
            CREATE TABLE IF NOT EXISTS tags (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id     TEXT    NOT NULL,  ← 必须有 user_id！
                name        TEXT    NOT NULL,
                color       TEXT
            );
            CREATE INDEX IF NOT EXISTS idx_tags_user ON tags(user_id);  ← 索引
        """)

def create_tag(user_id: str, data: dict) -> dict:
    """创建标签（只属于某个用户）"""
    now = _now()
    with _conn() as c:
        cur = c.execute(
            "INSERT INTO tags(user_id, name, color, created_at) VALUES(?,?,?,?)",
            (user_id, data["name"], data.get("color"), now),  ← 传入 user_id
        )
        return dict(c.execute("SELECT * FROM tags WHERE id=?", (cur.lastrowid,)).fetchone())

def get_tags(user_id: str) -> list[dict]:
    """获取某个用户的标签"""
    with _conn() as c:
        rows = c.execute(
            "SELECT * FROM tags WHERE user_id=?",  ← WHERE 条件必须有 user_id
            (user_id,)
        ).fetchall()
        return [dict(r) for r in rows]
```

---

### ✅ 正确做法 3：删除/更新操作也要验证 user_id

```python
# data/calendar_db.py - 防止用户删除别人的数据
def delete_tag(tag_id: int, user_id: str) -> bool:
    """删除标签（必须验证所有权）"""
    with _conn() as c:
        # ✅ 正确：既检查 id，也检查 user_id
        return c.execute(
            "DELETE FROM tags WHERE id=? AND user_id=?",
            (tag_id, user_id),  ← 这里很关键！
        ).rowcount > 0
```

**为什么需要两个条件？**
- `id=?` → 找到特定的标签
- `user_id=?` → 确保这个标签属于当前用户
- 如果只有 `id=?`，用户 A 可能删除用户 B 的标签！

---

### ❌ 错误做法（千万不要这样）

```python
# ❌ 错误 1：忘记传 user_id
@router.post("/analyze")
def analyze(session: SessionPrincipal = Depends(get_current_session)):
    result = analyze_user_schedule()  # 没有传 user_id！
    return result
    # 结果：获取的是全部用户的数据，产生隐私泄露

# ❌ 错误 2：直接用 URL 参数作为 user_id（信任客户端）
@router.get("/schedule/{user_id}")
def get_schedule(user_id: str):  # 不要这样！
    return get_events(user_id)  # 用户可以改 URL 查看别人的数据
    # 正确做法：只使用 session.user_id

# ❌ 错误 3：数据库查询没有 WHERE user_id
def get_tags(user_id: str) -> list[dict]:
    with _conn() as c:
        rows = c.execute("SELECT * FROM tags").fetchall()  # 没有 WHERE！
        return [dict(r) for r in rows]
    # 结果：返回所有用户的标签

# ❌ 错误 4：删除操作没有验证所有权
def delete_tag(tag_id: int, user_id: str) -> bool:
    with _conn() as c:
        return c.execute("DELETE FROM tags WHERE id=?", (tag_id,)).rowcount > 0
        # 任何用户都可以删除任何标签！
```

---

## 📝 新功能开发 Checklist

当你要添加新功能时，检查这个清单：

### 数据库层
- [ ] 新表是否包含 `user_id` 字段？
- [ ] 新表是否有 `CREATE INDEX ON user_id`？
- [ ] 所有 SELECT 查询是否都有 `WHERE user_id = ?`？
- [ ] 所有 DELETE/UPDATE 操作是否都验证 `user_id`？

### 服务层
- [ ] 函数签名是否都有 `user_id: str` 参数？
- [ ] 是否将 `user_id` 传给了数据库函数？
- [ ] 是否处理了"数据不存在"或"无权访问"的情况？

### 路由层
- [ ] 端点是否使用 `Depends(get_current_session)`？
- [ ] 是否从 `session` 提取了 `user_id`？
- [ ] 是否将 `user_id` 传给服务函数？

### 示例：添加"标签"功能的完整检查

```python
# 1️⃣ 数据库层 (data/calendar_db.py)
def init_db():
    c.executescript("""
        CREATE TABLE IF NOT EXISTS tags (
            id       INTEGER PRIMARY KEY,
            user_id  TEXT NOT NULL,           ✅ 有 user_id
            name     TEXT NOT NULL
        );
        CREATE INDEX idx_tags_user ON tags(user_id);  ✅ 有索引
    """)

def get_tags(user_id: str) -> list[dict]:
    rows = c.execute(
        "SELECT * FROM tags WHERE user_id=?",  ✅ 有 WHERE user_id
        (user_id,)
    ).fetchall()
    return [dict(r) for r in rows]

def delete_tag(tag_id: int, user_id: str) -> bool:
    return c.execute(
        "DELETE FROM tags WHERE id=? AND user_id=?",  ✅ 验证所有权
        (tag_id, user_id)
    ).rowcount > 0

# 2️⃣ 服务层 (services/tag_service.py)
async def get_tags(user_id: str) -> list[dict]:  ✅ 有 user_id 参数
    return calendar_db.get_tags(user_id)         ✅ 传给 DB

async def delete_tag(tag_id: int, user_id: str) -> bool:
    return calendar_db.delete_tag(tag_id, user_id)  ✅ 传两个参数

# 3️⃣ 路由层 (routes/tag_router.py)
@router.get("/tags")
def get_tags(session: SessionPrincipal = Depends(get_current_session)):  ✅ 有认证
    return tag_service.get_tags(session.user_id)  ✅ 传 user_id

@router.delete("/tags/{tag_id}")
def delete_tag(
    tag_id: int,
    session: SessionPrincipal = Depends(get_current_session)
):
    if not tag_service.delete_tag(tag_id, session.user_id):  ✅ 验证所有权
        raise HTTPException(404)
```

---

## 🔍 验证用户隔离是否正确

### 测试场景 1：用户 A 不能看到用户 B 的数据

```bash
# 1. 用户 A 登录
curl -X POST http://localhost:5522/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "alice", "password": "pass123"}'
→ {"session_id": "token_a", ...}

# 2. 用户 A 获取日程
curl http://localhost:5522/items \
  -H "Authorization: Bearer token_a"
→ {"events": [A的日程], "todos": [A的待办]}

# 3. 用户 B 登录
curl -X POST http://localhost:5522/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "bob", "password": "pass456"}'
→ {"session_id": "token_b", ...}

# 4. 用户 B 获取日程（应该看不到 A 的数据）
curl http://localhost:5522/items \
  -H "Authorization: Bearer token_b"
→ {"events": [B的日程], "todos": [B的待办]}
```

### 测试场景 2：过期 token 无法使用

```bash
# 用一个过期的 token 请求
curl http://localhost:5522/items \
  -H "Authorization: Bearer expired_token"
→ 401 Unauthorized "会话已过期"
```

### 测试场景 3：用户不能删除别人的日程

```bash
# 用户 A 创建日程，得到 event_id=1
# 用户 A 的 token 可以删除
curl -X DELETE http://localhost:5522/items/events/1 \
  -H "Authorization: Bearer token_a"
→ 204 No Content (删除成功)

# 但如果用户 B 尝试删除（使用 DB 中相同的 event_id），会失败
curl -X DELETE http://localhost:5522/items/events/1 \
  -H "Authorization: Bearer token_b"
→ 404 Not Found (因为查询时加了 AND user_id = ?)
```

---

## 总结

| 方面 | 实现细节 |
|------|--------|
| **用户ID** | UUID，在注册时生成，存储在 `users.json` |
| **会话** | 登录时创建，包含 `user_id`，30天过期，存储在 `sessions.json` |
| **认证** | 通过 `Bearer Token` + `get_current_session()` 验证 |
| **数据隔离** | 所有表都有 `user_id` 字段，所有查询都有 `WHERE user_id = ?` |
| **防护** | 3层防护：会话验证 → 路由过滤 → 数据库过滤 |

## 如果我要加新功能，需要管吗？

### 答案：**需要！但很简单。**

按照这个模板：

```python
# 1. 新表加 user_id 字段 ✅
# 2. 所有查询加 WHERE user_id = ? ✅
# 3. 删除/更新加两个条件：id AND user_id ✅
# 4. 路由层从 session 提取 user_id 传给服务 ✅
```

只要遵循这 4 点，用户隔离自动就正确了！🎉
