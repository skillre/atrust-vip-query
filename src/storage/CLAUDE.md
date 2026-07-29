# Persistence Layer

## Responsibility

SQLite 数据库操作 + Pydantic 数据模型。是整个系统的数据契约层——所有模块依赖这里的模型和 DB 接口。

## Dependencies

- **pydantic**: 数据模型验证（BaseModel）
- **sqlite3**: 标准库 SQLite（无 ORM）

## Consumers

- **src/collector/**: 三个采集器调用 upsert/insert 写入
- **src/api/routes.py**: 调用查询方法，使用模型作为响应类型

## Module Structure

```
src/storage/
├── models.py      # 13 个 Pydantic BaseModel（数据契约）
└── database.py    # Database 类（CRUD + 健康检查）
```

## Connection-per-Operation

所有 DB 方法统一骨架：打开连接 → try 执行 → except 返回 None/空响应 → finally 关闭。

```python
def query_user_vip(self, name: str) -> Optional[VipQueryResult]:
    conn = self._get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT ...", (name,))
        row = cursor.fetchone()
        if not row:
            return None
        return VipQueryResult(user_name=row["user_name"], ...)
    except Exception as e:
        logger.error(f"查询失败: {e}")
        return None
    finally:
        conn.close()
```

使用 `conn.row_factory = sqlite3.Row` 启用 `row["column"]` 字典式访问。

## Upsert（INSERT OR UPDATE）

```python
cursor.execute("""
    INSERT INTO users (user_name, display_name, ...)
    VALUES (?, ?, ...)
    ON CONFLICT(user_name) DO UPDATE SET
        display_name = COALESCE(excluded.display_name, users.display_name),
        updated_at = CURRENT_TIMESTAMP
""", (...))
```

`COALESCE` 保留已有数据——新值为 NULL 时不覆盖。

## Offset-Based Pagination

```python
offset = (page - 1) * page_size          # 1-indexed → 0-indexed
cursor.execute("SELECT ... ORDER BY timestamp DESC LIMIT ? OFFSET ?",
               params + [page_size, offset])
return HistoryResponse(total=total, page=page, page_size=page_size, records=records)
```

每次查询两个 SQL：一个 COUNT，一个 LIMIT/OFFSET。

## Schema Initialization

`_init_db()` 每次启动执行，`CREATE TABLE IF NOT EXISTS` 保证幂等。索引命名：`idx_{table}_{column}`。

## Model Hierarchy

```
PaginatedResponse (base) → UserListResponse, HistoryResponse
ApiResponse              ← 所有 API 响应的统一信封
VipQueryResult           ← 用户→VIP 查询
VipReverseResult         ← VIP→用户 反查
```

## Architectural Boundaries

- **NO ORM**: 直接 sqlite3，模型是 Pydantic
- **NO migration system**: Schema 变更需手动 ALTER
- **NO connection pooling**: 单写者模型，每次独立连接
- **NO exceptions to callers**: 错误返回 None 或空响应

<important if="you are adding a new database table">
## Adding a New Table
1. 在 `_init_db()` 中添加 `CREATE TABLE IF NOT EXISTS`
2. 为查询列添加索引 `idx_{table}_{column}`
3. 在 `models.py` 定义 Pydantic 模型
4. 在 `Database` 类实现 CRUD（connection-per-operation 模式）
</important>

<important if="you are adding a new query method">
## Adding a New Query
1. 在 `Database` 类添加方法，try/finally 关闭连接
2. 分页用 COUNT + LIMIT/OFFSET
3. 返回 `Optional[Model]`（单条）或 `*Response`（分页）
4. 失败返回 None 或空响应对象
</important>
