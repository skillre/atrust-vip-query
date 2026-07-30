# ============================================================
# FastAPI 路由模块
# 提供 RESTful API 接口
# 所有同步数据库操作通过 asyncio.to_thread 包装，不阻塞事件循环
# ============================================================

import asyncio
import csv
import io
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
from src.storage.models import ApiResponse, HealthData, VipInfo


router = APIRouter()


# ------------------------------------------------------------------
# 查询接口
# ------------------------------------------------------------------

@router.get("/vip/query")
async def query_user_vip(
    name: str = Query(..., description="用户名或显示名"),
    source: str = Query("all", description="数据来源: online, history, all")
) -> ApiResponse:
    """
    查询用户虚拟IP

    根据用户名或显示名查询虚拟IP，优先查询在线用户，再查询历史记录。
    """
    db = get_database()

    result = await asyncio.to_thread(db.query_user_vip, name)
    if not result:
        return ApiResponse(code=2001, message="用户不存在", data=None)

    # 如果需要查询在线状态，调用 aTrust API
    if source in ("online", "all"):
        collector = get_api_collector()

        def _get_online():
            return collector.client.get_online_users()

        online_users = await asyncio.to_thread(_get_online)

        if online_users:
            for user in online_users:
                if user.get("name") == result.user_name:
                    result.is_online = True
                    vip = user.get("virtualIp")
                    if vip:
                        result.online_vips = [
                            VipInfo(
                                ip=vip,
                                real_ip=user.get("realIp")
                            )
                        ]
                    break

    # 记录查询日志
    db.log_search(name, "user", 1 if result else 0)

    return ApiResponse(
        code=0,
        message="success",
        data=result.model_dump()
    )


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
    上传并导入日志文件

    支持 CSV 和 Excel 格式的 aTrust 访问日志文件。
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
        # 文件大小检查
        content = await file.read()
        if len(content) > MAX_UPLOAD_SIZE:
            return ApiResponse(
                code=4006,
                message=f"文件过大，最大支持 {MAX_UPLOAD_SIZE // (1024*1024)}MB",
                data=None
            )

        if not content:
            return ApiResponse(
                code=4002,
                message="文件为空",
                data=None
            )

        importer = get_file_importer()

        # 文件导入在后台线程执行，不阻塞事件循环
        result = await asyncio.to_thread(importer.import_file, content, filename)

        if result["success"]:
            # 记录导入日志
            db = get_database()
            db.log_import(
                filename=filename,
                file_size=len(content),
                record_count=result.get("total", 0),
                success_count=result.get("success", 0),
                fail_count=result.get("failed", 0),
                status="success" if result.get("failed", 0) == 0 else "partial"
            )
            return ApiResponse(
                code=0,
                message=result["message"],
                data=result
            )
        else:
            return ApiResponse(
                code=4003,
                message=result["message"],
                data=result
            )

    except Exception as e:
        logger.error(f"文件导入失败: {e}")
        return ApiResponse(
            code=5000,
            message="文件导入失败，请检查文件格式后重试",
            data=None
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
