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
