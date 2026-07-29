# ============================================================
# FastAPI 路由模块
# 提供 RESTful API 接口
# ============================================================

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Query, UploadFile, File
from loguru import logger

from src.storage.database import get_database
from src.collector.api_collector import get_api_collector
from src.collector.syslog_collector import get_syslog_receiver
from src.collector.file_importer import get_file_importer
from src.storage.models import ApiResponse, HealthData, VipInfo


router = APIRouter(prefix="/api/v1")


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
    
    result = db.query_user_vip(name)
    if not result:
        return ApiResponse(code=2001, message="用户不存在", data=None)
    
    # 如果需要查询在线状态，调用 aTrust API
    if source in ("online", "all"):
        collector = get_api_collector()
        online_users = collector.client.get_online_users()
        
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
    
    result = db.reverse_query_vip(ip, limit)
    if not result or not result.records:
        return ApiResponse(code=2002, message="虚拟IP不存在", data=None)
    
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
    
    result = db.query_user_history(name, days, page, page_size)
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
    
    result = db.get_user_list(search, page, page_size)
    
    return ApiResponse(
        code=0,
        message="success",
        data=result.model_dump()
    )


@router.post("/import/upload")
async def upload_log_file(
    file: UploadFile = File(..., description="日志文件（CSV/Excel）")
) -> ApiResponse:
    """
    上传并导入日志文件
    
    支持 CSV 和 Excel 格式的 aTrust 访问日志文件。
    """
    # 检查文件格式
    allowed_extensions = {".csv", ".xlsx", ".xls"}
    filename = file.filename or "unknown.csv"
    
    if not any(filename.lower().endswith(ext) for ext in allowed_extensions):
        return ApiResponse(
            code=4001,
            message=f"不支持的文件格式，请上传 CSV 或 Excel 文件",
            data=None
        )
    
    try:
        # 读取文件内容
        content = await file.read()
        
        if not content:
            return ApiResponse(
                code=4002,
                message="文件为空",
                data=None
            )
        
        # 导入文件
        importer = get_file_importer()
        result = importer.import_file(content, filename)
        
        if result["success"]:
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
            message=f"文件导入失败: {str(e)}",
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
        result = importer.get_import_preview(text_content)
        
        return ApiResponse(
            code=0 if result["success"] else 4005,
            message="预览成功" if result["success"] else result.get("message", "预览失败"),
            data=result
        )
    
    except Exception as e:
        return ApiResponse(code=5000, message=f"预览失败: {str(e)}", data=None)


@router.get("/system/health")
async def health_check() -> ApiResponse:
    """
    健康检查
    
    检查系统运行状态。
    """
    db = get_database()
    syslog = get_syslog_receiver()
    
    # 数据库状态
    db_status = db.health_check()
    
    # Syslog 状态
    syslog_status = syslog.health_check()
    
    health_data = HealthData(
        status="healthy" if db_status["status"] == "connected" else "degraded",
        version="1.0.0",
        database=db_status["status"],
        atrust_api="disabled",
        syslog=syslog_status
    )
    
    return ApiResponse(
        code=0,
        message="success",
        data=health_data.model_dump()
    )
