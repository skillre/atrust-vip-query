# ============================================================
# FastAPI 路由模块
# 提供 RESTful API 接口
# 所有同步数据库操作通过 asyncio.to_thread 包装，不阻塞事件循环
# ============================================================

import asyncio
import csv
import io
import threading
import uuid
import time
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Query, UploadFile, File
from fastapi.responses import StreamingResponse
from loguru import logger

from src.storage.database import get_database
from src.collector.api_collector import get_api_collector
from src.collector.syslog_collector import get_syslog_receiver
from src.collector.file_importer import get_file_importer

# 上传文件大小限制（50MB）
MAX_UPLOAD_SIZE = 50 * 1024 * 1024
from src.storage.models import ApiResponse, HealthData, VipInfo, BatchQueryRequest


router = APIRouter()


# ------------------------------------------------------------------
# 导入进度任务注册表（进程内，用于前端轮询真实进度）
# ------------------------------------------------------------------
_import_tasks: dict[str, dict] = {}
_import_tasks_lock = threading.Lock()
# 已完成任务保留时长（秒），超时清理避免内存泄漏
_IMPORT_TASK_TTL = 300


def _new_import_task(filename: str, file_size: int) -> str:
    """创建一个导入任务，返回 task_id。"""
    task_id = uuid.uuid4().hex
    now = time.time()
    with _import_tasks_lock:
        # 顺手清理过期的已完成任务
        expired = [
            tid for tid, t in _import_tasks.items()
            if t.get("done") and now - t.get("finished_at", now) > _IMPORT_TASK_TTL
        ]
        for tid in expired:
            _import_tasks.pop(tid, None)
        _import_tasks[task_id] = {
            "filename": filename,
            "file_size": file_size,
            "phase": "pending",
            "processed": 0,
            "total": 0,
            "percent": 0,
            "done": False,
            "success": False,
            "message": "",
            "result": None,
            "created_at": now,
        }
    return task_id


def _update_import_task(task_id: str, **fields) -> None:
    with _import_tasks_lock:
        task = _import_tasks.get(task_id)
        if task is not None:
            task.update(fields)


# ------------------------------------------------------------------
# 查询接口
# ------------------------------------------------------------------

@router.get("/vip/query")
async def query_user_vip(
    name: str = Query(..., description="用户名或显示名"),
    source: str = Query("realtime", description="数据来源: realtime(默认)、database、all"),
    fuzzy: bool = Query(False, description="是否对用户名/显示名做模糊匹配（仅数据库）")
) -> ApiResponse:
    """
    查询用户虚拟IP
    
    查询逻辑（按 source 参数）：
    - realtime (默认): 先查 aTrust API，失败/无结果时查数据库
    - database: 只查本地数据库
    - all: 同时查询 API 和数据库，合并结果

    fuzzy=True 时走数据库模糊匹配，可能命中多个用户，
    结果以 {"matches": [...], "total": N} 形式返回。
    """
    from src.collector.api_collector import AtrustApiError
    
    db = get_database()
    collector = get_api_collector()
    api_result = None
    db_result = None
    api_error = None

    # ---- 模糊模式：直接走数据库多结果查询 ----
    if fuzzy:
        matches = await asyncio.to_thread(db.query_vips_multi, [name], True)
        db.log_search(name, "user", len(matches))
        if not matches:
            return ApiResponse(code=2001, message="未找到匹配用户", data={"matches": [], "total": 0})
        return ApiResponse(
            code=0,
            message=f"success (database, fuzzy) 命中 {len(matches)} 个用户",
            data={"matches": [m.model_dump() for m in matches], "total": len(matches)}
        )
    
    # ---- 1. 尝试从 aTrust API 实时查询 ----
    if source in ("realtime", "all"):
        def _query_from_api():
            # 先尝试按显示名查询
            users = collector.client.query_user_by_display_name(name)
            if users:
                return users, "displayName"
            # 再尝试按用户名查询
            users = collector.client.query_user_by_name(name)
            if users:
                return users, "name"
            return [], None
        
        try:
            online_users, match_type = await asyncio.to_thread(_query_from_api)
            
            if online_users:
                # 取第一个匹配的用户
                user = online_users[0]
                vips = user.get("vips", [])
                
                from src.storage.models import VipQueryResult
                api_result = VipQueryResult(
                    user_name=user.get("name", ""),
                    display_name=user.get("displayName"),
                    is_online=True,
                    online_vips=[
                        VipInfo(ip=v.get("ip", ""), real_ip=user.get("remoteIp"))
                        for v in vips
                    ] if vips else []
                )
        except AtrustApiError as e:
            api_error = str(e)
            logger.warning(f"aTrust API 查询失败: {e}")
        except Exception as e:
            api_error = str(e)
            logger.warning(f"aTrust API 查询异常: {e}")
    
    # ---- 2. 如果 API 查询成功，直接返回 ----
    if api_result and api_result.online_vips:
        db.log_search(name, "user", len(api_result.online_vips))
        return ApiResponse(code=0, message="success (realtime)", data=api_result.model_dump())
    
    # ---- 3. 查询本地数据库 ----
    if source in ("realtime", "database", "all"):
        db_result = await asyncio.to_thread(db.query_user_vip, name)
    
    # ---- 4. 合并结果 ----
    if api_result:
        # API 有结果（用户在线，但可能没虚拟IP），合并数据库历史
        if db_result:
            api_result.history_vip = db_result.history_vip
        db.log_search(name, "user", len(api_result.online_vips) if api_result.online_vips else 0)
        return ApiResponse(code=0, message="success (realtime)", data=api_result.model_dump())
    
    if db_result:
        # 数据库有结果，但用户不在线
        db_result.is_online = False
        db.log_search(name, "user", 1)
        return ApiResponse(code=0, message="success (database)", data=db_result.model_dump())
    
    # ---- 5. 都没有结果 ----
    if api_error:
        # API 出错，数据库也没有，返回 API 错误提示
        return ApiResponse(code=5001, message=f"API 查询失败且数据库无记录: {api_error}", data=None)
    
    return ApiResponse(code=2001, message="用户不存在", data=None)


@router.post("/vip/query/batch")
async def query_vips_batch(req: BatchQueryRequest) -> ApiResponse:
    """
    批量查询用户虚拟IP（仅本地数据库）

    传入多个用户名/显示名，一次性返回每个的最新虚拟IP。
    fuzzy=True 时每个关键词做模糊匹配（可能展开更多结果，自动按用户去重）。
    """
    names = [n for n in (req.names or []) if n and n.strip()]
    if not names:
        return ApiResponse(code=4000, message="请提供至少一个查询名称", data={"matches": [], "total": 0})

    # 限制单次批量规模，避免滥用
    if len(names) > 500:
        return ApiResponse(code=4001, message="单次批量查询不能超过 500 个", data=None)

    db = get_database()
    matches = await asyncio.to_thread(db.query_vips_multi, names, req.fuzzy)
    db.log_search(f"批量查询 {len(names)} 个", "user", len(matches))

    return ApiResponse(
        code=0,
        message=f"success 命中 {len(matches)} 个用户",
        data={"matches": [m.model_dump() for m in matches], "total": len(matches)}
    )


@router.get("/vip/online")
async def query_online_user_vip(
    name: str = Query(..., description="用户名或显示名")
) -> ApiResponse:
    """
    实时查询在线用户虚拟IP

    直接调用 aTrust API 查询在线用户，无需依赖本地数据库。
    """
    from src.collector.api_collector import AtrustApiError
    
    collector = get_api_collector()
    
    def _query_online():
        # 先尝试按显示名查询
        users = collector.client.query_user_by_display_name(name)
        if users:
            return users, "displayName"
        
        # 再尝试按用户名查询
        users = collector.client.query_user_by_name(name)
        if users:
            return users, "name"
        
        return [], None
    
    try:
        users, match_type = await asyncio.to_thread(_query_online)
        
        if not users:
            return ApiResponse(code=2001, message=f"未找到在线用户: {name}", data=None)
        
        # 构造返回数据
        result_list = []
        for user in users:
            vips = user.get("vips", [])
            vip_list = [v.get("ip", "") for v in vips] if vips else []
            
            result_list.append({
                "name": user.get("name", ""),
                "displayName": user.get("displayName", ""),
                "remoteIp": user.get("remoteIp", ""),
                "os": user.get("os", ""),
                "lastLoginTime": user.get("lastLoginTime", ""),
                "isOnline": True,
                "vips": vip_list,
                "matchType": match_type
            })
        
        # 记录查询日志
        db = get_database()
        db.log_search(name, "user", len(result_list))
        
        return ApiResponse(
            code=0,
            message="success",
            data={"users": result_list, "total": len(result_list)}
        )
        
    except AtrustApiError as e:
        logger.error(f"aTrust API 查询失败: {e}")
        return ApiResponse(code=5001, message=f"API 查询失败: {str(e)}", data=None)
    except Exception as e:
        logger.error(f"查询异常: {e}")
        return ApiResponse(code=5000, message=f"查询异常: {str(e)}", data=None)


@router.get("/vip/reverse")
async def reverse_query_vip(
    ip: str = Query(..., description="虚拟IP地址"),
    limit: int = Query(10, description="返回条数")
) -> ApiResponse:
    """
    按虚拟IP反查用户

    根据虚拟IP地址反查关联的用户信息。
    """
    db = get_database()

    result = await asyncio.to_thread(db.reverse_query_vip, ip, limit)
    if not result or not result.records:
        return ApiResponse(code=2002, message="虚拟IP不存在", data=None)

    # 记录查询日志
    db.log_search(ip, "ip", len(result.records) if result else 0)

    return ApiResponse(
        code=0,
        message="success",
        data=result.model_dump()
    )


@router.get("/vip/history")
async def query_vip_history(
    name: str = Query(..., description="用户名或显示名"),
    days: int = Query(30, description="查询天数"),
    page: int = Query(1, description="页码"),
    page_size: int = Query(20, description="每页条数")
) -> ApiResponse:
    """
    查询历史记录

    查询指定用户的历史虚拟IP记录。
    """
    db = get_database()

    result = await asyncio.to_thread(db.query_user_history, name, days, page, page_size)
    if not result:
        return ApiResponse(code=2001, message="用户不存在", data=None)

    return ApiResponse(
        code=0,
        message="success",
        data=result.model_dump()
    )


@router.get("/user/list")
async def get_user_list(
    search: Optional[str] = Query(None, description="搜索关键词"),
    page: int = Query(1, description="页码"),
    page_size: int = Query(20, description="每页条数")
) -> ApiResponse:
    """
    获取用户列表

    获取所有用户列表，支持搜索和分页。
    """
    db = get_database()

    result = await asyncio.to_thread(db.get_user_list, search, page, page_size)

    return ApiResponse(
        code=0,
        message="success",
        data=result.model_dump()
    )


# ------------------------------------------------------------------
# 文件导入接口
# ------------------------------------------------------------------

@router.post("/import/upload")
async def upload_log_file(
    file: UploadFile = File(..., description="日志文件（CSV/Excel）")
) -> ApiResponse:
    """
    上传并导入日志文件（异步任务）

    支持 CSV 和 Excel 格式的 aTrust 访问日志文件。
    立即返回 task_id，导入在后台线程执行；
    前端通过 GET /import/progress/{task_id} 轮询真实进度。
    """
    allowed_extensions = {".csv", ".xlsx", ".xls"}
    filename = file.filename or "unknown.csv"

    if not any(filename.lower().endswith(ext) for ext in allowed_extensions):
        return ApiResponse(
            code=4001,
            message=f"不支持的文件格式，请上传 CSV 或 Excel 文件",
            data=None
        )

    try:
        content = await file.read()
    except Exception as e:
        logger.error(f"读取上传文件失败: {e}")
        return ApiResponse(code=5000, message="读取上传文件失败", data=None)

    if len(content) > MAX_UPLOAD_SIZE:
        return ApiResponse(
            code=4006,
            message=f"文件过大，最大支持 {MAX_UPLOAD_SIZE // (1024*1024)}MB",
            data=None
        )

    if not content:
        return ApiResponse(code=4002, message="文件为空", data=None)

    task_id = _new_import_task(filename, len(content))

    def _run_import():
        """后台线程：执行导入并回写进度。"""
        def _cb(processed: int, total: int, phase: str):
            if total > 0:
                percent = processed * 100 // total
            else:
                percent = 0
            # 封顶 99%，真正完成时才置 100
            if percent > 99:
                percent = 99
            _update_import_task(
                task_id,
                phase=phase,
                processed=processed,
                total=total,
                percent=percent,
            )

        _update_import_task(task_id, phase="parsing", percent=0)
        try:
            importer = get_file_importer()
            result = importer.import_file(content, filename, progress_cb=_cb)

            if result.get("success"):
                db = get_database()
                db.log_import(
                    filename=filename,
                    file_size=len(content),
                    record_count=result.get("total_rows", 0),
                    success_count=result.get("imported", 0),
                    fail_count=result.get("errors", 0),
                    status="success" if result.get("errors", 0) == 0 else "partial",
                )
                _update_import_task(
                    task_id,
                    phase="done",
                    processed=result.get("total_rows", 0),
                    total=result.get("total_rows", 0),
                    percent=100,
                    done=True,
                    success=True,
                    message=result.get("message", "导入完成"),
                    result=result,
                    finished_at=time.time(),
                )
            else:
                _update_import_task(
                    task_id,
                    phase="error",
                    done=True,
                    success=False,
                    message=result.get("message", "导入失败"),
                    result=result,
                    finished_at=time.time(),
                )
        except Exception as e:
            logger.error(f"文件导入失败: {e}")
            _update_import_task(
                task_id,
                phase="error",
                done=True,
                success=False,
                message="文件导入失败，请检查文件格式后重试",
                finished_at=time.time(),
            )

    # 后台线程执行，不阻塞事件循环；立即返回 task_id
    threading.Thread(target=_run_import, daemon=True).start()

    return ApiResponse(
        code=0,
        message="导入任务已创建",
        data={"task_id": task_id, "filename": filename, "file_size": len(content)},
    )


@router.get("/import/progress/{task_id}")
async def get_import_progress(task_id: str) -> ApiResponse:
    """
    查询导入任务进度

    前端轮询此接口驱动进度弹窗。
    返回：phase / processed / total / percent / done / success / message / result
    """
    with _import_tasks_lock:
        task = _import_tasks.get(task_id)
        snapshot = dict(task) if task is not None else None

    if snapshot is None:
        return ApiResponse(code=4040, message="任务不存在或已过期", data=None)

    return ApiResponse(
        code=0,
        message="success",
        data={
            "task_id": task_id,
            "filename": snapshot.get("filename"),
            "file_size": snapshot.get("file_size"),
            "phase": snapshot.get("phase"),
            "processed": snapshot.get("processed", 0),
            "total": snapshot.get("total", 0),
            "percent": snapshot.get("percent", 0),
            "done": snapshot.get("done", False),
            "success": snapshot.get("success", False),
            "message": snapshot.get("message", ""),
            "result": snapshot.get("result"),
        },
    )


@router.post("/import/preview")
async def preview_log_file(
    file: UploadFile = File(..., description="日志文件（CSV/Excel）")
) -> ApiResponse:
    """
    预览日志文件

    解析文件前几行，显示数据结构，不导入数据库。
    """
    try:
        content = await file.read()

        # 文件大小检查
        if len(content) > MAX_UPLOAD_SIZE:
            return ApiResponse(
                code=4006,
                message=f"文件过大，最大支持 {MAX_UPLOAD_SIZE // (1024*1024)}MB",
                data=None
            )

        if not content:
            return ApiResponse(code=4002, message="文件为空", data=None)

        # 尝试解码
        text_content = None
        for encoding in ["utf-8", "gbk", "gb2312", "utf-8-sig"]:
            try:
                text_content = content.decode(encoding)
                break
            except UnicodeDecodeError:
                continue

        if text_content is None:
            return ApiResponse(code=4004, message="无法识别文件编码", data=None)

        importer = get_file_importer()
        result = await asyncio.to_thread(importer.get_import_preview, text_content)

        return ApiResponse(
            code=0 if result["success"] else 4005,
            message="预览成功" if result["success"] else result.get("message", "预览失败"),
            data=result
        )

    except Exception as e:
        logger.error(f"文件预览失败: {e}")
        return ApiResponse(code=5000, message="文件预览失败，请检查文件格式", data=None)


# ------------------------------------------------------------------
# 数据导出接口
# ------------------------------------------------------------------

@router.get("/export/csv")
async def export_csv(
    name: Optional[str] = Query(None, description="用户名或显示名筛选"),
    days: int = Query(30, description="导出天数"),
    event_type: Optional[str] = Query(None, description="事件类型筛选")
) -> StreamingResponse:
    """
    导出数据为 CSV 文件

    支持按用户名、时间范围、事件类型筛选。
    """
    db = get_database()

    # 在后台线程获取数据
    data = await asyncio.to_thread(db.get_export_data, name, days, event_type)

    if not data:
        return StreamingResponse(
            io.BytesIO(b""),
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=export.csv"}
        )

    # 生成 CSV
    output = io.StringIO()
    if data:
        writer = csv.DictWriter(output, fieldnames=data[0].keys())
        writer.writeheader()
        writer.writerows(data)

    csv_bytes = output.getvalue().encode("utf-8-sig")  # BOM for Excel compatibility

    filename = f"vip_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"

    return StreamingResponse(
        io.BytesIO(csv_bytes),
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"'
        }
    )


# ------------------------------------------------------------------
# 系统接口
# ------------------------------------------------------------------

@router.get("/system/health")
async def health_check() -> ApiResponse:
    """
    健康检查

    检查系统运行状态。
    """
    db = get_database()
    syslog = get_syslog_receiver()

    # 在后台线程执行同步检查
    db_status = await asyncio.to_thread(db.health_check)
    syslog_status = await asyncio.to_thread(syslog.health_check)

    health_data = HealthData(
        status="healthy" if db_status["status"] == "connected" else "degraded",
        version="1.0.0",
        database=db_status["status"],
        atrust_api="disabled",
        syslog=syslog_status if isinstance(syslog_status, str) else syslog_status.get("status", "unknown")
    )

    return ApiResponse(
        code=0,
        message="success",
        data=health_data.model_dump()
    )


@router.get("/system/stats")
async def get_system_stats() -> ApiResponse:
    """
    获取系统性能统计

    包含数据库统计和 Syslog 处理器性能指标。
    """
    db = get_database()
    syslog = get_syslog_receiver()

    db_status = await asyncio.to_thread(db.health_check)

    stats = {
        "database": db_status,
        "syslog": syslog.get_stats() if syslog.is_running else None,
    }

    return ApiResponse(
        code=0,
        message="success",
        data=stats
    )
