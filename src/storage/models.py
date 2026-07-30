# ============================================================
# 数据模型定义
# Pydantic 模型 + SQLAlchemy ORM 模型
# ============================================================

from datetime import datetime
from typing import Optional, List

from pydantic import BaseModel


# ============================================================
# Pydantic 请求/响应模型
# ============================================================

class UserInfo(BaseModel):
    """用户信息"""
    user_name: str
    display_name: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    directory_name: Optional[str] = None
    group_path: Optional[str] = None


class VipRecord(BaseModel):
    """虚拟IP记录"""
    user_name: str
    virtual_ip: str
    real_ip: Optional[str] = None
    event_type: str
    timestamp: datetime


class VipInfo(BaseModel):
    """虚拟IP信息（查询结果）"""
    ip: str
    real_ip: Optional[str] = None
    last_login_time: Optional[str] = None


class VipQueryResult(BaseModel):
    """虚拟IP查询结果"""
    user_name: str
    display_name: Optional[str] = None
    is_online: bool
    online_vips: List[VipInfo] = []
    history_vip: Optional[VipRecord] = None


class VipReverseRecord(BaseModel):
    """虚拟IP反查记录"""
    user_name: str
    display_name: Optional[str] = None
    real_ip: Optional[str] = None
    event_type: str
    timestamp: str


class VipReverseResult(BaseModel):
    """虚拟IP反查结果"""
    virtual_ip: str
    records: List[VipReverseRecord] = []


class UserListItem(BaseModel):
    """用户列表项"""
    user_name: str
    display_name: Optional[str] = None
    phone: Optional[str] = None
    directory_name: Optional[str] = None
    last_vip: Optional[str] = None
    last_active: Optional[str] = None


class PaginatedResponse(BaseModel):
    """分页响应"""
    total: int
    page: int
    page_size: int


class UserListResponse(PaginatedResponse):
    """用户列表响应"""
    users: List[UserListItem] = []


class HistoryRecord(BaseModel):
    """历史记录项"""
    virtual_ip: str
    real_ip: Optional[str] = None
    event_type: str
    timestamp: str


class HistoryResponse(PaginatedResponse):
    """历史记录响应"""
    records: List[HistoryRecord] = []


class ApiResponse(BaseModel):
    """通用API响应"""
    code: int = 0
    message: str = "success"
    data: Optional[dict] = None


class HealthData(BaseModel):
    """健康检查数据"""
    status: str = "healthy"
    version: str = "1.0.0"
    uptime: str = ""
    database: str = "connected"
    atrust_api: str = "unknown"
    syslog: str = "stopped"


# ============================================================
# 新增模型（Phase 5 扩展）
# ============================================================

class DashboardStats(BaseModel):
    """仪表盘统计数据"""
    online_users: int = 0
    today_queries: int = 0
    vip_pool_size: int = 0
    last_sync: str = ""


class SearchLog(BaseModel):
    """查询日志"""
    query_text: str
    query_type: str  # 'user' | 'ip'
    result_count: int = 0


class SearchLogItem(BaseModel):
    """查询日志列表项"""
    id: int
    query_text: str
    query_type: str
    result_count: int
    created_at: str


class RecentSearches(BaseModel):
    """最近查询结果"""
    searches: List[SearchLogItem] = []


class ImportLog(BaseModel):
    """导入记录"""
    id: int
    filename: str
    file_size: int = 0
    record_count: int = 0
    success_count: int = 0
    fail_count: int = 0
    status: str = "pending"
    error_message: Optional[str] = None
    created_at: str
    completed_at: Optional[str] = None


class ImportHistoryResponse(BaseModel):
    """导入历史响应"""
    total: int
    logs: List[ImportLog] = []


class SystemConfig(BaseModel):
    """系统配置"""
    mode: str = "import"
    atrust_host: str = ""
    atrust_api_id: str = ""
    atrust_api_key: str = ""
    atrust_timeout: int = 10
    syslog_enabled: bool = True
    syslog_host: str = "0.0.0.0"
    syslog_port: int = 514
    syslog_protocol: str = "tcp"
    syslog_workers: int = 4
    syslog_batch_size: int = 5000
    syslog_flush_interval: float = 5.0
    db_path: str = "./data/vip_data.db"
    db_retention_days: int = 90
    db_batch_size: int = 5000
    db_flush_interval: float = 5.0
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_debug: bool = False
    log_level: str = "INFO"
    log_file: str = "./logs/app.log"
    log_max_size: int = 10
    log_backup_count: int = 5


class SyslogStats(BaseModel):
    """Syslog 性能统计"""
    running: bool = False
    listen_address: str = ""
    today_received: int = 0
    parse_success: int = 0
    parse_failed: int = 0
    avg_process_time_ms: float = 0.0
    batch_size: int = 0
    flush_interval: float = 0.0


class DatabaseStats(BaseModel):
    """数据库统计"""
    user_count: int = 0
    record_count: int = 0
    today_imports: int = 0
    db_size_mb: float = 0.0


class SystemStatusFull(BaseModel):
    """系统状态全量数据"""
    status: str = "healthy"
    version: str = "1.0.0"
    uptime: str = ""
    database_status: str = "connected"
    atrust_api_status: str = "disabled"
    syslog_status: str = "stopped"
    db_stats: DatabaseStats = DatabaseStats()
    syslog_stats: SyslogStats = SyslogStats()
