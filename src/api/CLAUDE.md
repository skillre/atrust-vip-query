# REST API Layer

## Responsibility

FastAPI 薄控制器——定义路由、参数校验、响应包装。不含业务逻辑，所有操作委托给 storage 和 collector。

## Dependencies

- **fastapi**: Web 框架（APIRouter, Query, UploadFile, File）

## Consumers

- **app.py**: 通过 `app.include_router(api_router)` 注册

## Module Structure

```
src/api/
└── routes.py    # 7 个端点，单一文件
```

## Unified Response Envelope

所有端点返回 `ApiResponse`（code/message/data），错误码通过 body 返回：

| 范围 | 含义 |
| --- | --- |
| `0` | 成功 |
| `2xxx` | 业务错误（用户不存在等） |
| `4xxx` | 输入错误（格式不对、文件为空） |
| `5000` | 服务器错误 |

```python
return ApiResponse(code=0, message="success", data=result.model_dump())
return ApiResponse(code=2001, message="用户不存在", data=None)
```

## FastAPI Query 参数

```python
@router.get("/vip/history")
async def query_vip_history(
    name: str = Query(..., description="用户名或显示名"),   # 必填
    days: int = Query(30, description="查询天数"),          # 可选
    page: int = Query(1), page_size: int = Query(20)
) -> ApiResponse:
    db = get_database()
    result = db.query_user_history(name, days, page, page_size)
    if not result:
        return ApiResponse(code=2001, message="用户不存在", data=None)
    return ApiResponse(code=0, message="success", data=result.model_dump())
```

## File Upload Pattern

```python
@router.post("/import/upload")
async def upload_log_file(file: UploadFile = File(...)) -> ApiResponse:
    allowed = {".csv", ".xlsx", ".xls"}
    if not any(file.filename.lower().endswith(ext) for ext in allowed):
        return ApiResponse(code=4001, message="不支持的文件格式", data=None)
    content = await file.read()
    if not content:
        return ApiResponse(code=4002, message="文件为空", data=None)
    importer = get_file_importer()
    result = importer.import_file(content, file.filename)
    return ApiResponse(code=0 if result["success"] else 4003,
                       message=result["message"], data=result)
```

## API 端点清单

| 端点 | 方法 | 说明 |
| --- | --- | --- |
| `/api/v1/import/upload` | POST | 上传并导入日志文件 |
| `/api/v1/import/preview` | POST | 预览日志文件 |
| `/api/v1/vip/query` | GET | 查询用户虚拟IP |
| `/api/v1/vip/reverse` | GET | 按虚拟IP反查用户 |
| `/api/v1/vip/history` | GET | 查询历史记录 |
| `/api/v1/user/list` | GET | 获取用户列表 |
| `/api/v1/system/health` | GET | 健康检查 |

## Architectural Boundaries

- **NO business logic**: 只做路由和响应包装
- **NO auth**: 所有端点公开（CORS `allow_origins=["*"]`）
- **NOTE**: async handler 中调用同步阻塞代码，计划后续用 `asyncio.to_thread` 优化

<important if="you are adding a new API endpoint">
## Adding a New Endpoint
1. 在 `models.py` 定义响应模型（分页用 `PaginatedResponse` 子类）
2. 在 `database.py` 实现查询方法（connection-per-operation）
3. 在 `routes.py` 添加路由：`@router.get("/path")`，参数用 `Query()`
4. 返回 `ApiResponse(code=0, data=result.model_dump())`
5. 错误码：业务 `2xxx`，输入 `4xxx`，服务器 `5000`
</important>
