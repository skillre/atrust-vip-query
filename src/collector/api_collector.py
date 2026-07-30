# ============================================================
# aTrust API 采集模块
# 调用 aTrust OpenAPI 获取在线用户和虚拟IP信息
# ============================================================
#
# 签名算法说明 (已验证可用):
# 1. 签名串 = 请求路径 + ? + query参数(按key排序) + & + body参数
# 2. 签名密钥 = appId={id}&appSecret={key}&timestamp={ts}&nonce={nonce}
# 3. 签名 = HMAC-SHA256(签名密钥, 签名串)
# 4. 请求头: x-ca-key, x-ca-sign, x-ca-timestamp, x-ca-nonce
#
# 测试设备: 10.5.40.161:4433
# 验证时间: 2026-07-30
# ============================================================

import hashlib
import hmac
import time
import uuid
from datetime import datetime
from typing import Optional, List, Dict, Any, Tuple

import requests
import urllib3
from loguru import logger

from src.config import get_config
from src.storage.models import UserInfo, VipRecord
from src.storage.database import get_database

# 禁用 SSL 警告（aTrust 使用自签名证书）
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class AtrustClient:
    """
    aTrust API 客户端
    
    实现 HMAC-SHA256 签名认证，支持在线用户查询和虚拟IP获取。
    
    使用示例:
        client = AtrustClient()
        users = client.get_online_users()
        vip_users = client.query_user_by_display_name("张三")
    """
    
    # API 路径常量
    PATH_GET_CONFIG = "/api/v1/admin/getConfig"
    PATH_ONLINE_USERS = "/api/v1/monitor/getUserStatus"
    PATH_QUERY_DEVICES = "/api/v1/device/queryAll"
    
    # 默认配置
    DEFAULT_TIMEOUT = 30
    MAX_RETRY = 3
    RETRY_DELAY = 1  # 秒
    
    def __init__(self):
        """初始化 aTrust API 客户端"""
        config = get_config()
        
        self.base_url = config.atrust.host.rstrip("/")
        self.api_id = config.atrust.api_id
        self.api_key = config.atrust.api_key
        self.timeout = getattr(config.atrust, 'timeout', self.DEFAULT_TIMEOUT)
        
        # 创建请求会话
        self.session = requests.Session()
        self.session.verify = False  # aTrust 使用自签名证书
        
        # 禁用代理（aTrust 通常在内网，不需要代理）
        self.session.trust_env = False  # 不使用环境变量中的代理设置
        
        # 验证配置
        if not self.base_url:
            raise ValueError("aTrust 主机地址未配置")
        if not self.api_id:
            raise ValueError("aTrust API ID 未配置")
        if not self.api_key:
            raise ValueError("aTrust API Key 未配置")
        
        logger.debug(f"aTrust 客户端初始化完成: {self.base_url}")
    
    def _generate_nonce(self) -> str:
        """生成随机数 nonce (UUID v4)"""
        return str(uuid.uuid4())
    
    def _generate_timestamp(self) -> int:
        """生成当前时间戳（秒级，10位）"""
        return int(time.time())
    
    def _calculate_sign(
        self, 
        method: str, 
        path: str, 
        query_params: Optional[Dict[str, str]] = None, 
        body: str = ""
    ) -> Tuple[str, int, str, str]:
        """
        计算 HMAC-SHA256 签名
        
        Args:
            method: HTTP 方法 (GET, POST)
            path: API 路径 (如 /api/v1/monitor/getUserStatus)
            query_params: URL 查询参数
            body: 请求体 (JSON 字符串)
        
        Returns:
            Tuple[sign, timestamp, nonce, sign_str]
        
        Raises:
            ValueError: 参数验证失败
        """
        if not path:
            raise ValueError("请求路径不能为空")
        
        # 1. 生成时间戳和 nonce
        timestamp = self._generate_timestamp()
        nonce = self._generate_nonce()
        
        # 2. 构造签名串
        # 签名串 = 请求路径 + ? + query参数(按key ASCII排序) + & + body参数
        sign_str = path
        
        if query_params:
            # 按 key 的 ASCII 排序
            sorted_params = sorted(query_params.items())
            query_string = '&'.join([f"{k}={v}" for k, v in sorted_params])
            sign_str += '?' + query_string
        
        if body:
            sign_str += ('&' if query_params else '?') + body
        
        # 3. 构造签名密钥
        # 格式: appId={id}&appSecret={key}&timestamp={ts}&nonce={nonce}
        key_str = f"appId={self.api_id}&appSecret={self.api_key}&timestamp={timestamp}&nonce={nonce}"
        
        # 4. 计算 HMAC-SHA256 签名
        sign = hmac.new(
            key_str.encode('utf-8'),
            sign_str.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        
        logger.debug(f"签名计算完成: path={path}, timestamp={timestamp}")
        return sign, timestamp, nonce, sign_str
    
    def _build_url(self, path: str, query_params: Optional[Dict[str, str]] = None) -> str:
        """
        构造完整 URL
        
        Args:
            path: API 路径
            query_params: 查询参数
        
        Returns:
            完整的 URL
        """
        url = f"{self.base_url}{path}"
        
        if query_params:
            sorted_params = sorted(query_params.items())
            query_string = '&'.join([f"{k}={v}" for k, v in sorted_params])
            url += '?' + query_string
        
        return url
    
    def _make_request(
        self, 
        method: str, 
        path: str, 
        query_params: Optional[Dict[str, str]] = None,
        data: Optional[Dict] = None,
        retry_count: int = 0
    ) -> Dict[str, Any]:
        """
        发送 API 请求（带重试机制）
        
        Args:
            method: HTTP 方法
            path: API 路径
            query_params: URL 查询参数
            data: 请求体数据
            retry_count: 当前重试次数
        
        Returns:
            API 响应数据
        
        Raises:
            AtrustApiError: API 调用失败
        """
        # 准备请求体
        body_str = ""
        if data:
            import json
            body_str = json.dumps(data, separators=(',', ':'))
        
        # 计算签名
        sign, timestamp, nonce, sign_str = self._calculate_sign(
            method.upper(), path, query_params, body_str
        )
        
        # 构造 URL
        url = self._build_url(path, query_params)
        
        # 构造请求头
        headers = {
            'Content-Type': 'application/json; charset=utf-8',
            'x-ca-key': self.api_id,
            'x-ca-sign': sign,
            'x-ca-timestamp': str(timestamp),
            'x-ca-nonce': nonce
        }
        
        logger.debug(f"发送请求: {method} {url}")
        
        try:
            # 发送请求
            response = self.session.request(
                method=method.upper(),
                url=url,
                headers=headers,
                data=body_str if body_str else None,
                timeout=self.timeout
            )
            
            # 检查 HTTP 状态码
            response.raise_for_status()
            
            # 解析响应
            result = response.json()
            
            # 检查业务状态码
            code = result.get("code", -1)
            if code != 0:
                msg = result.get("msg", "未知错误")
                trace_id = result.get("traceId", "")
                error_msg = f"API 业务错误: code={code}, msg={msg}, traceId={trace_id}"
                logger.warning(error_msg)
                raise AtrustApiError(error_msg, code=code, trace_id=trace_id)
            
            logger.debug(f"请求成功: {path}")
            return result
            
        except AtrustApiError:
            raise
            
        except requests.exceptions.SSLError as e:
            # SSL 错误需要单独处理（ConnectionError 的子类）
            error_msg = f"SSL 证书错误: {url} - {str(e)}"
            logger.error(error_msg)
            raise AtrustApiError(error_msg)
            
        except requests.exceptions.Timeout as e:
            error_msg = f"API 请求超时: {url}"
            logger.error(error_msg)
            if retry_count < self.MAX_RETRY:
                logger.info(f"尝试重试 ({retry_count + 1}/{self.MAX_RETRY})...")
                time.sleep(self.RETRY_DELAY)
                return self._make_request(method, path, query_params, data, retry_count + 1)
            raise AtrustApiError(error_msg) from e
            
        except requests.exceptions.ConnectionError as e:
            error_msg = f"API 连接失败: {url} - {str(e)}"
            logger.error(error_msg)
            if retry_count < self.MAX_RETRY:
                logger.info(f"尝试重试 ({retry_count + 1}/{self.MAX_RETRY})...")
                time.sleep(self.RETRY_DELAY)
                return self._make_request(method, path, query_params, data, retry_count + 1)
            raise AtrustApiError(error_msg) from e
            
        except ValueError as e:
            # JSON 解析错误
            error_msg = f"响应解析失败: {url} - {str(e)}"
            logger.error(error_msg)
            raise AtrustApiError(error_msg) from e
            
        except requests.exceptions.RequestException as e:
            # 其他请求异常
            error_msg = f"API 请求异常: {url} - {str(e)}"
            logger.error(error_msg)
            raise AtrustApiError(error_msg) from e
    
    def get_config(self) -> Dict[str, Any]:
        """
        获取控制台配置（不需要签名）
        
        Returns:
            配置信息
        
        Raises:
            AtrustApiError: 请求失败
        """
        url = f"{self.base_url}{self.PATH_GET_CONFIG}"
        
        try:
            response = self.session.get(url, timeout=self.timeout)
            response.raise_for_status()
            result = response.json()
            
            if result.get("code") != 0:
                raise AtrustApiError(f"获取配置失败: {result.get('msg')}")
            
            return result.get("data", {})
            
        except requests.exceptions.RequestException as e:
            raise AtrustApiError(f"获取配置请求失败: {str(e)}")
    
    def get_online_users(
        self,
        search_value: Optional[str] = None,
        filter_by: str = "displayName",
        page_size: int = 100,
        page_index: int = 1
    ) -> Dict[str, Any]:
        """
        获取在线用户列表
        
        Args:
            search_value: 搜索值
            filter_by: 过滤条件 (name/displayName/vip/remoteIp/os/all)
            page_size: 每页数量 (最大 1000)
            page_index: 页码 (从 1 开始)
        
        Returns:
            包含用户列表的字典:
            {
                "count": int,           # 当前页数量
                "amount": int,          # 总会话数
                "onlineUser": int,      # 去重后用户数
                "data": List[Dict]      # 用户列表
            }
        """
        params = {
            'pageSize': str(min(page_size, 1000)),
            'pageIndex': str(max(1, page_index))
        }
        
        if search_value:
            params['filter'] = filter_by
            params['searchValue'] = search_value
        
        result = self._make_request("GET", self.PATH_ONLINE_USERS, query_params=params)
        return result.get("data", {})
    
    def query_user_by_display_name(self, display_name: str) -> List[Dict[str, Any]]:
        """
        通过显示名查询在线用户
        
        Args:
            display_name: 用户显示名
        
        Returns:
            匹配的用户列表
        """
        if not display_name:
            return []
        
        result = self.get_online_users(
            search_value=display_name,
            filter_by="displayName"
        )
        
        users = result.get("data", [])
        
        # 精确匹配过滤（API 是模糊搜索）
        matched_users = []
        for user in users:
            user_display = user.get("displayName", "")
            if (display_name.lower() in user_display.lower() or 
                user_display.lower() in display_name.lower()):
                matched_users.append(user)
        
        return matched_users
    
    def query_user_by_name(self, username: str) -> List[Dict[str, Any]]:
        """
        通过用户名查询在线用户
        
        Args:
            username: 用户名
        
        Returns:
            匹配的用户列表
        """
        if not username:
            return []
        
        result = self.get_online_users(
            search_value=username,
            filter_by="name"
        )
        
        users = result.get("data", [])
        
        # 精确匹配过滤
        matched_users = []
        for user in users:
            user_name = user.get("name", "")
            if (username.lower() in user_name.lower() or 
                user_name.lower() in username.lower()):
                matched_users.append(user)
        
        return matched_users
    
    def get_user_vip(self, user_name: str) -> List[str]:
        """
        查询指定用户的所有虚拟IP
        
        Args:
            user_name: 用户名
        
        Returns:
            虚拟IP列表
        """
        users = self.query_user_by_name(user_name)
        
        vip_list = []
        for user in users:
            vips = user.get("vips", [])
            for vip in vips:
                ip = vip.get("ip", "")
                if ip and ip not in vip_list:
                    vip_list.append(ip)
        
        return vip_list
    
    def get_all_online_users(self) -> List[Dict[str, Any]]:
        """
        获取所有在线用户（自动分页）
        
        Returns:
            所有在线用户列表
        """
        all_users = []
        page_index = 1
        page_size = 100
        
        while True:
            result = self.get_online_users(page_size=page_size, page_index=page_index)
            users = result.get("data", [])
            
            if not users:
                break
            
            all_users.extend(users)
            
            # 检查是否还有下一页
            if len(users) < page_size:
                break
            
            page_index += 1
        
        return all_users
    
    def query_devices(
        self,
        page_size: int = 20,
        page_index: int = 1
    ) -> Dict[str, Any]:
        """
        查询全量终端信息
        
        Args:
            page_size: 每页数量 (最大 1000)
            page_index: 页码
        
        Returns:
            终端信息字典
        """
        data = {
            "pageSize": min(page_size, 1000),
            "pageIndex": max(1, page_index)
        }
        
        result = self._make_request("POST", self.PATH_QUERY_DEVICES, data=data)
        return result.get("data", {})
    
    def health_check(self) -> str:
        """
        检查 aTrust API 是否可用
        
        Returns:
            "available" 或 "unavailable"
        """
        try:
            self.get_config()
            return "available"
        except Exception as e:
            logger.warning(f"健康检查失败: {e}")
            return "unavailable"
    
    def test_connection(self) -> Tuple[bool, str]:
        """
        测试 aTrust 设备连接
        
        Returns:
            (success, message)
        """
        try:
            # 测试获取配置
            config = self.get_config()
            app_version = config.get("appversion", "未知")
            logger.info(f"连接成功，设备版本: {app_version[:50]}")
            return True, f"连接成功，设备版本: {app_version[:100]}"
            
        except AtrustApiError as e:
            error_msg = f"API 错误: {str(e)}"
            logger.error(error_msg)
            return False, error_msg
            
        except Exception as e:
            error_msg = f"连接失败: {str(e)}"
            logger.error(error_msg)
            return False, error_msg


class AtrustApiError(Exception):
    """aTrust API 调用异常"""
    
    def __init__(self, message: str, code: int = -1, trace_id: str = ""):
        super().__init__(message)
        self.code = code
        self.trace_id = trace_id
    
    def __str__(self):
        if self.trace_id:
            return f"{super().__str__()} (traceId: {self.trace_id})"
        return super().__str__()


class ApiCollector:
    """
    API 数据采集器
    
    负责从 aTrust 设备采集在线用户数据并存储到数据库。
    """
    
    def __init__(self):
        """初始化采集器"""
        self.client = AtrustClient()
        self.db = get_database()
    
    def collect_online_users(self) -> int:
        """
        采集在线用户数据
        
        Returns:
            采集的用户数量
        """
        logger.info("开始采集在线用户数据...")
        
        try:
            users = self.client.get_all_online_users()
        except AtrustApiError as e:
            logger.error(f"获取在线用户失败: {e}")
            return 0
        
        if not users:
            logger.warning("未获取到在线用户数据")
            return 0
        
        count = 0
        for user_data in users:
            try:
                # 解析用户信息
                user = UserInfo(
                    user_name=user_data.get("name", ""),
                    display_name=user_data.get("displayName"),
                    phone=user_data.get("phone"),
                    email=user_data.get("email"),
                    directory_name=user_data.get("userDirectoryName"),
                    group_path=user_data.get("groupPath")
                )
                
                if not user.user_name:
                    continue
                
                # 保存用户信息
                self.db.upsert_user(user)
                
                # 解析虚拟IP信息（vips 是数组格式）
                vips = user_data.get("vips", [])
                for vip_data in vips:
                    virtual_ip = vip_data.get("ip", "")
                    if virtual_ip:
                        record = VipRecord(
                            user_name=user.user_name,
                            virtual_ip=virtual_ip,
                            real_ip=user_data.get("remoteIp"),
                            event_type="online_query",
                            timestamp=datetime.now()
                        )
                        self.db.insert_vip_record(record)
                
                count += 1
                
            except Exception as e:
                logger.error(f"处理用户数据失败: {e}")
                continue
        
        logger.info(f"在线用户采集完成，共 {count} 条")
        return count
    
    def health_check(self) -> str:
        """
        检查 aTrust API 是否可用
        
        Returns:
            "available" 或 "unavailable"
        """
        return self.client.health_check()

    def test_connection(self) -> bool:
        """
        测试 aTrust 设备连接
        
        Returns:
            True 表示连接成功，False 表示连接失败
        """
        try:
            success, message = self.client.test_connection()
            return success
        except Exception:
            return False


# ============================================================
# 全局实例
# ============================================================

_collector: Optional[ApiCollector] = None


def get_api_collector() -> ApiCollector:
    """获取全局 API 采集器实例"""
    global _collector
    if _collector is None:
        _collector = ApiCollector()
    return _collector


def reset_api_collector() -> None:
    """重置全局 API 采集器实例"""
    global _collector
    _collector = None