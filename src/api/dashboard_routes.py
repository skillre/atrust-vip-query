# ============================================================
# 仪表盘 & 系统管理 API
# ============================================================

import asyncio
from typing import Optional

import yaml
from fastapi import APIRouter, Query
from loguru import logger

from src.storage.database import get_database
from src.storage.models import (
    ApiResponse, DashboardStats, RecentSearches, SearchLogItem,
    ImportHistoryResponse, ImportLog, SystemConfig, SystemStatusFull,
    DatabaseStats, SyslogStats
)
from src.collector.syslog_collector import get_syslog_receiver

router = APIRouter()


@router.get("/dashboard/stats")
async def get_dashboard_stats() -> ApiResponse:
    """获取仪表盘统计数据"""
    db = get_database()
    stats = await asyncio.to_thread(db.get_dashboard_stats)
    return ApiResponse(code=0, message="success", data=DashboardStats(**stats).model_dump())


@router.get("/search/recent")
async def get_recent_searches(
    limit: int = Query(10, ge=1, le=50)
) -> ApiResponse:
    """获取最近查询记录"""
    db = get_database()
    searches = await asyncio.to_thread(db.get_recent_searches, limit)
    items = [SearchLogItem(**s) for s in searches]
    return ApiResponse(code=0, message="success", data=RecentSearches(searches=items).model_dump())


@router.get("/import/history")
async def get_import_history(
    limit: int = Query(20, ge=1, le=100)
) -> ApiResponse:
    """获取导入历史"""
    db = get_database()
    logs = await asyncio.to_thread(db.get_import_history, limit)
    items = [ImportLog(**log) for log in logs]
    return ApiResponse(
        code=0, message="success",
        data=ImportHistoryResponse(total=len(items), logs=items).model_dump()
    )


@router.get("/system/status-full")
async def get_system_status_full() -> ApiResponse:
    """获取系统状态全量数据"""
    db = get_database()
    syslog = get_syslog_receiver()

    db_health = await asyncio.to_thread(db.health_check)
    db_stats_dict = await asyncio.to_thread(db.get_database_stats)

    syslog_stats = SyslogStats()
    if syslog and hasattr(syslog, 'is_running') and syslog.is_running:
        stats = syslog.get_stats() if hasattr(syslog, 'get_stats') else {}
        syslog_stats = SyslogStats(
            running=True,
            listen_address=f"{getattr(syslog, 'host', '0.0.0.0')}:{getattr(syslog, 'port', 514)}",
            **stats
        )

    status_data = SystemStatusFull(
        status="healthy" if db_health.get("status") == "connected" else "degraded",
        version="1.0.0",
        database_status=db_health.get("status", "unknown"),
        atrust_api_status="disabled",
        syslog_status="running" if syslog_stats.running else "stopped",
        db_stats=DatabaseStats(**db_stats_dict),
        syslog_stats=syslog_stats
    )

    return ApiResponse(code=0, message="success", data=status_data.model_dump())


@router.get("/system/config")
async def get_system_config() -> ApiResponse:
    """读取系统配置"""
    try:
        config_path = "./config.yaml"
        with open(config_path, "r", encoding="utf-8") as f:
            raw = yaml.safe_load(f) or {}

        config = SystemConfig(
            mode=raw.get("mode", "import"),
            atrust_host=raw.get("atrust", {}).get("host", ""),
            atrust_api_id=raw.get("atrust", {}).get("api_id", ""),
            atrust_api_key="••••••••" if raw.get("atrust", {}).get("api_key") else "",
            atrust_timeout=raw.get("atrust", {}).get("timeout", 10),
            syslog_enabled=raw.get("syslog", {}).get("enabled", True),
            syslog_host=raw.get("syslog", {}).get("host", "0.0.0.0"),
            syslog_port=raw.get("syslog", {}).get("port", 514),
            syslog_protocol=raw.get("syslog", {}).get("protocol", "tcp"),
            syslog_workers=raw.get("syslog", {}).get("parse_workers", 4),
            syslog_batch_size=raw.get("syslog", {}).get("batch_size", 5000),
            syslog_flush_interval=raw.get("syslog", {}).get("flush_interval", 5.0),
            db_path=raw.get("database", {}).get("path", "./data/vip_data.db"),
            db_retention_days=raw.get("database", {}).get("retention_days", 90),
            db_batch_size=raw.get("database", {}).get("batch_size", 5000),
            db_flush_interval=raw.get("database", {}).get("flush_interval", 5.0),
            api_host=raw.get("api", {}).get("host", "0.0.0.0"),
            api_port=raw.get("api", {}).get("port", 8000),
            api_debug=raw.get("api", {}).get("debug", False),
            log_level=raw.get("logging", {}).get("level", "INFO"),
            log_file=raw.get("logging", {}).get("file", "./logs/app.log"),
            log_max_size=raw.get("logging", {}).get("max_size", 10),
            log_backup_count=raw.get("logging", {}).get("backup_count", 5),
        )

        return ApiResponse(code=0, message="success", data=config.model_dump())

    except Exception as e:
        logger.error(f"读取配置失败: {e}")
        return ApiResponse(code=5000, message="读取配置失败", data=None)


@router.put("/system/config")
async def update_system_config(config: SystemConfig) -> ApiResponse:
    """更新系统配置"""
    try:
        config_path = "./config.yaml"

        with open(config_path, "r", encoding="utf-8") as f:
            raw = yaml.safe_load(f) or {}

        raw["mode"] = config.mode

        raw.setdefault("atrust", {})
        raw["atrust"]["host"] = config.atrust_host
        raw["atrust"]["api_id"] = config.atrust_api_id
        if config.atrust_api_key != "••••••••":
            raw["atrust"]["api_key"] = config.atrust_api_key
        raw["atrust"]["timeout"] = config.atrust_timeout

        raw.setdefault("syslog", {})
        raw["syslog"]["enabled"] = config.syslog_enabled
        raw["syslog"]["host"] = config.syslog_host
        raw["syslog"]["port"] = config.syslog_port
        raw["syslog"]["protocol"] = config.syslog_protocol
        raw["syslog"]["parse_workers"] = config.syslog_workers
        raw["syslog"]["batch_size"] = config.syslog_batch_size
        raw["syslog"]["flush_interval"] = config.syslog_flush_interval

        raw.setdefault("database", {})
        raw["database"]["path"] = config.db_path
        raw["database"]["retention_days"] = config.db_retention_days
        raw["database"]["batch_size"] = config.db_batch_size
        raw["database"]["flush_interval"] = config.db_flush_interval

        raw.setdefault("api", {})
        raw["api"]["host"] = config.api_host
        raw["api"]["port"] = config.api_port
        raw["api"]["debug"] = config.api_debug

        raw.setdefault("logging", {})
        raw["logging"]["level"] = config.log_level
        raw["logging"]["file"] = config.log_file
        raw["logging"]["max_size"] = config.log_max_size
        raw["logging"]["backup_count"] = config.log_backup_count

        with open(config_path, "w", encoding="utf-8") as f:
            yaml.dump(raw, f, allow_unicode=True, default_flow_style=False)

        return ApiResponse(code=0, message="配置已保存", data=None)

    except Exception as e:
        logger.error(f"保存配置失败: {e}")
        return ApiResponse(code=5000, message="保存配置失败", data=None)


@router.post("/system/config/reset")
async def reset_system_config() -> ApiResponse:
    """恢复默认配置"""
    try:
        default_config = SystemConfig()
        return await update_system_config(default_config)
    except Exception as e:
        logger.error(f"重置配置失败: {e}")
        return ApiResponse(code=5000, message="重置配置失败", data=None)


@router.post("/system/test-atrust")
async def test_atrust_connection() -> ApiResponse:
    """
    测试 aTrust 设备连接
    
    使用当前配置文件中的配置进行测试，而不是启动时的配置。
    """
    import yaml
    from src.collector.api_collector import AtrustClient, AtrustApiError
    
    try:
        # 读取当前配置文件
        config_path = "./config.yaml"
        with open(config_path, "r", encoding="utf-8") as f:
            raw = yaml.safe_load(f) or {}
        
        host = raw.get("atrust", {}).get("host", "")
        api_id = raw.get("atrust", {}).get("api_id", "")
        api_key = raw.get("atrust", {}).get("api_key", "")
        timeout = raw.get("atrust", {}).get("timeout", 30)
        
        # 验证配置
        if not host:
            return ApiResponse(code=3001, message="aTrust 主机地址未配置", data={"connected": False})
        if not api_id:
            return ApiResponse(code=3001, message="aTrust API ID 未配置", data={"connected": False})
        if not api_key:
            return ApiResponse(code=3001, message="aTrust API Key 未配置", data={"connected": False})
        
        # 创建临时客户端进行测试
        def _test():
            import requests
            import urllib3
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
            
            # 构造 URL
            test_url = f"{host}/api/v1/admin/getConfig"
            
            # 创建会话并禁用代理
            session = requests.Session()
            session.verify = False
            session.trust_env = False  # 禁用环境变量代理
            
            try:
                response = session.get(test_url, timeout=timeout)
                response.raise_for_status()
                result = response.json()
                
                if result.get("code") == 0:
                    app_version = result.get("data", {}).get("appversion", "未知")
                    return True, f"连接成功，设备版本: {app_version[:100]}"
                else:
                    return False, f"API 返回错误: {result.get('msg', '未知错误')}"
            except Exception as e:
                return False, f"连接失败: {str(e)}"
            finally:
                session.close()
        
        success, message = await asyncio.to_thread(_test)
        
        if success:
            return ApiResponse(code=0, message=message, data={"connected": True})
        else:
            return ApiResponse(code=3001, message=message, data={"connected": False})
            
    except AtrustApiError as e:
        return ApiResponse(code=3001, message=str(e), data={"connected": False})
    except Exception as e:
        logger.error(f"测试连接异常: {e}")
        return ApiResponse(code=3001, message=f"连接失败: {str(e)}", data={"connected": False})


@router.post("/system/syslog/restart")
async def restart_syslog() -> ApiResponse:
    """重启 Syslog 接收器"""
    syslog = get_syslog_receiver()
    try:
        if syslog and hasattr(syslog, 'restart'):
            await asyncio.to_thread(syslog.restart)
            return ApiResponse(code=0, message="Syslog 已重启", data=None)
        else:
            return ApiResponse(code=3002, message="Syslog 接收器不可用", data=None)
    except Exception as e:
        return ApiResponse(code=3002, message=f"重启失败: {str(e)}", data=None)
