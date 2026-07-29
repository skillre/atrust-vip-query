# ============================================================
# aTrust API 采集模块
# 调用 aTrust OpenAPI 获取在线用户和虚拟IP信息
# ============================================================

import time
from datetime import datetime
from typing import Optional, List, Dict, Any

import requests
from loguru import logger

from src.config import get_config
from src.storage.models import UserInfo, VipRecord
from src.storage.database import get_database


class AtrustClient:
    """aTrust API 客户端"""
    
    def __init__(self):
        config = get_config()
        self.base_url = config.atrust.host.rstrip("/")
        self.api_id = config.atrust.api_id
        self.api_key = config.atrust.api_key
        self.timeout = config.atrust.timeout
        self.session = requests.Session()
        
        # 配置请求头
        self.session.headers.update({
            "Content-Type": "application/json",
            "Accept": "application/json"
        })
    
    def _sign_request(self, timestamp: str) -> str:
        """
        生成API签名
        
        Args:
            timestamp: 时间戳
        
        Returns:
            签名字符串
        """
        import hmac
        import hashlib
        import base64
        
        message = f"{self.api_id}\n{timestamp}"
        signature = hmac.new(
            self.api_key.encode("utf-8"),
            message.encode("utf-8"),
            hashlib.sha256
        ).digest()
        
        return base64.b64encode(signature).decode("utf-8")
    
    def _make_request(
        self, 
        method: str, 
        path: str, 
        params: Optional[Dict] = None
    ) -> Optional[Dict[str, Any]]:
        """
        发送API请求
        
        Args:
            method: HTTP方法
            path: API路径
            params: 请求参数
        
        Returns:
            响应数据
        """
        url = f"{self.base_url}{path}"
        timestamp = str(int(time.time() * 1000))
        signature = self._sign_request(timestamp)
        
        headers = {
            "X-API-ID": self.api_id,
            "X-Timestamp": timestamp,
            "X-Signature": signature
        }
        
        try:
            response = self.session.request(
                method=method,
                url=url,
                headers=headers,
                params=params,
                timeout=self.timeout,
                verify=False  # aTrust通常使用自签名证书
            )
            
            response.raise_for_status()
            data = response.json()
            
            if data.get("code") == 0 or data.get("success"):
                return data.get("data", data)
            else:
                logger.warning(f"API返回错误: {data}")
                return None
                
        except requests.exceptions.Timeout:
            logger.error(f"API请求超时: {url}")
            return None
        except requests.exceptions.ConnectionError:
            logger.error(f"API连接失败: {url}")
            return None
        except Exception as e:
            logger.error(f"API请求异常: {e}")
            return None
    
    def get_online_users(self) -> Optional[List[Dict[str, Any]]]:
        """
        获取在线用户列表
        
        Returns:
            在线用户列表
        """
        # aTrust OpenAPI: 获取用户在线状态
        # 具体路径需要根据实际API文档调整
        data = self._make_request("GET", "/api/v1/user/status")
        
        if data and isinstance(data, list):
            return data
        elif data and "list" in data:
            return data["list"]
        
        return None
    
    def get_user_vip(self, user_name: str) -> Optional[Dict[str, Any]]:
        """
        查询指定用户的虚拟IP
        
        Args:
            user_name: 用户名
        
        Returns:
            用户虚拟IP信息
        """
        data = self._make_request(
            "GET", 
            "/api/v1/user/vip",
            params={"userName": user_name}
        )
        return data


class ApiCollector:
    """API 数据采集器"""
    
    def __init__(self):
        self.client = AtrustClient()
        self.db = get_database()
    
    def collect_online_users(self) -> int:
        """
        采集在线用户数据
        
        Returns:
            采集的用户数量
        """
        logger.info("开始采集在线用户数据...")
        
        users = self.client.get_online_users()
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
                
                # 解析虚拟IP信息
                virtual_ip = user_data.get("virtualIp")
                if virtual_ip:
                    record = VipRecord(
                        user_name=user.user_name,
                        virtual_ip=virtual_ip,
                        real_ip=user_data.get("realIp"),
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
            状态: "available" 或 "unavailable"
        """
        try:
            data = self.client._make_request("GET", "/api/v1/system/health")
            if data:
                return "available"
            return "unavailable"
        except Exception:
            return "unavailable"


# 全局采集器实例
_collector: Optional[ApiCollector] = None


def get_api_collector() -> ApiCollector:
    """获取全局API采集器实例"""
    global _collector
    if _collector is None:
        _collector = ApiCollector()
    return _collector
