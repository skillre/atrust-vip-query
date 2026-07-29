# ============================================================
# Syslog 接收模块
# 监听 UDP 514 端口，接收并解析 aTrust 日志
# ============================================================

import json
import socket
import threading
from datetime import datetime
from typing import Optional, Dict, Any

from loguru import logger

from src.config import get_config
from src.storage.models import UserInfo, VipRecord
from src.storage.database import get_database


class SyslogParser:
    """aTrust Syslog 日志解析器"""
    
    @staticmethod
    def parse(raw_data: str) -> Optional[Dict[str, Any]]:
        """
        解析 Syslog 原始数据
        
        aTrust 的 Syslog 格式通常是 JSON 格式的结构化日志
        
        Args:
            raw_data: 原始日志数据
        
        Returns:
            解析后的数据字典
        """
        try:
            # 尝试解析 JSON
            # aTrust 日志格式示例:
            # <13>1 2024-01-01T00:00:00Z hostname app - - - {"actor": {...}, "src": {...}, "event": {...}}
            
            # 找到 JSON 部分（可能在 syslog 头部之后）
            json_start = raw_data.find("{")
            json_end = raw_data.rfind("}") + 1
            
            if json_start >= 0 and json_end > json_start:
                json_str = raw_data[json_start:json_end]
                data = json.loads(json_str)
                return data
            
            # 如果整个就是 JSON
            data = json.loads(raw_data)
            return data
            
        except json.JSONDecodeError as e:
            logger.debug(f"JSON解析失败: {e}")
            return None
        except Exception as e:
            logger.error(f"日志解析异常: {e}")
            return None
    
    @staticmethod
    def extract_user_info(data: Dict[str, Any]) -> Optional[UserInfo]:
        """
        从日志中提取用户信息
        
        Args:
            data: 解析后的日志数据
        
        Returns:
            用户信息
        """
        actor = data.get("actor", {})
        
        user_name = actor.get("name")
        if not user_name:
            return None
        
        return UserInfo(
            user_name=user_name,
            display_name=actor.get("displayName"),
            phone=actor.get("phoneNumber"),
            email=actor.get("email"),
            directory_name=actor.get("directoryName"),
            group_path=actor.get("groupPath")
        )
    
    @staticmethod
    def extract_vip_record(
        data: Dict[str, Any], 
        user_name: str
    ) -> Optional[VipRecord]:
        """
        从日志中提取虚拟IP记录
        
        Args:
            data: 解析后的日志数据
            user_name: 用户名
        
        Returns:
            虚拟IP记录
        """
        src = data.get("src", {})
        event = data.get("event", {})
        
        virtual_ip = src.get("virtualIp")
        if not virtual_ip:
            return None
        
        # 解析时间戳
        timestamp_ms = event.get("timestamp")
        if timestamp_ms:
            try:
                timestamp = datetime.fromtimestamp(timestamp_ms / 1000)
            except (TypeError, ValueError):
                timestamp = datetime.now()
        else:
            timestamp = datetime.now()
        
        # 确定事件类型
        sub_type = event.get("subType", "")
        event_type = "syslog_access"
        
        if "vip.apply" in sub_type or "assign" in sub_type:
            event_type = "syslog_vip_apply"
        elif "vip.revoke" in sub_type or "release" in sub_type:
            event_type = "syslog_vip_revoke"
        
        return VipRecord(
            user_name=user_name,
            virtual_ip=virtual_ip,
            real_ip=src.get("ip"),
            event_type=event_type,
            timestamp=timestamp
        )


class SyslogReceiver:
    """Syslog UDP 接收器"""
    
    def __init__(self):
        config = get_config()
        self.host = config.syslog.host
        self.port = config.syslog.port
        self.protocol = config.syslog.protocol
        self.enabled = config.syslog.enabled
        
        self.parser = SyslogParser()
        self.db = get_database()
        
        self._socket: Optional[socket.socket] = None
        self._running = False
        self._thread: Optional[threading.Thread] = None
    
    def start(self) -> bool:
        """
        启动 Syslog 接收器
        
        Returns:
            是否成功启动
        """
        if not self.enabled:
            logger.info("Syslog 接收器已禁用")
            return False
        
        if self._running:
            logger.warning("Syslog 接收器已在运行")
            return True
        
        try:
            # 创建 UDP socket
            self._socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self._socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self._socket.bind((self.host, self.port))
            
            self._running = True
            
            # 在新线程中运行
            self._thread = threading.Thread(target=self._receive_loop, daemon=True)
            self._thread.start()
            
            logger.info(f"Syslog 接收器已启动: {self.host}:{self.port} ({self.protocol.upper()})")
            return True
            
        except PermissionError:
            logger.error(f"无法绑定端口 {self.port}: 权限不足（需要 root 或 sudo）")
            return False
        except OSError as e:
            logger.error(f"无法绑定端口 {self.port}: {e}")
            return False
        except Exception as e:
            logger.error(f"Syslog 接收器启动失败: {e}")
            return False
    
    def stop(self) -> None:
        """停止 Syslog 接收器"""
        self._running = False
        
        if self._socket:
            try:
                self._socket.close()
            except Exception:
                pass
            self._socket = None
        
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=5)
        
        logger.info("Syslog 接收器已停止")
    
    def _receive_loop(self) -> None:
        """接收数据的主循环"""
        buffer_size = 4096
        
        while self._running:
            try:
                data, addr = self._socket.recvfrom(buffer_size)
                raw_data = data.decode("utf-8", errors="ignore")
                
                # 解析日志
                parsed = self.parser.parse(raw_data)
                if parsed:
                    self._process_log(parsed, addr)
                    
            except socket.timeout:
                continue
            except OSError:
                # socket 已关闭
                break
            except Exception as e:
                logger.error(f"接收数据异常: {e}")
    
    def _process_log(self, data: Dict[str, Any], addr: tuple) -> None:
        """
        处理解析后的日志
        
        Args:
            data: 解析后的日志数据
            addr: 发送方地址
        """
        try:
            # 提取用户信息
            user_info = self.parser.extract_user_info(data)
            if user_info:
                self.db.upsert_user(user_info)
                
                # 提取虚拟IP记录
                vip_record = self.parser.extract_vip_record(data, user_info.user_name)
                if vip_record:
                    self.db.insert_vip_record(vip_record)
                    logger.debug(
                        f"记录虚拟IP: {user_info.user_name} -> {vip_record.virtual_ip}"
                    )
            
        except Exception as e:
            logger.error(f"处理日志失败: {e}")
    
    @property
    def is_running(self) -> bool:
        """是否正在运行"""
        return self._running
    
    def health_check(self) -> str:
        """
        检查 Syslog 接收器状态
        
        Returns:
            状态: "listening" 或 "stopped"
        """
        return "listening" if self._running else "stopped"


# 全局接收器实例
_receiver: Optional[SyslogReceiver] = None


def get_syslog_receiver() -> SyslogReceiver:
    """获取全局 Syslog 接收器实例"""
    global _receiver
    if _receiver is None:
        _receiver = SyslogReceiver()
    return _receiver
