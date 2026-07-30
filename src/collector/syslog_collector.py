# ============================================================
# Syslog 接收模块（生产级）
# 监听 UDP 514 端口，接收并解析 aTrust 日志
#
# 架构：收包线程 → 解析队列 → 解析线程池 → 写入队列 → 批量写入线程
# 适用于每天 6000w+ 条日志的高吞吐场景
# ============================================================

import json
import queue
import socket
import threading
import time
from datetime import datetime
from typing import Optional, Dict, Any, List, Tuple

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
        """从日志中提取用户信息"""
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
        """从日志中提取虚拟IP记录"""
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
    """
    Syslog UDP 接收器（生产级）

    线程模型：
    ┌─────────────┐    ┌──────────────────┐    ┌─────────────┐
    │  收包线程    │───▶│  解析线程池 (N)   │───▶│  批量写入线程│
    │  (1个)      │    │  从 parse_queue   │    │  定时/定量   │
    │  recvfrom() │    │  取数据并解析     │    │  刷盘到 SQLite│
    └─────────────┘    └──────────────────┘    └─────────────┘
    """

    def __init__(self):
        config = get_config()
        self.host = config.syslog.host
        self.port = config.syslog.port
        self.protocol = config.syslog.protocol
        self.enabled = config.syslog.enabled
        self.buffer_size = config.syslog.buffer_size
        self.parse_workers = config.syslog.parse_workers
        self.batch_size = config.syslog.batch_size
        self.flush_interval = config.syslog.flush_interval

        self.parser = SyslogParser()
        self.db = get_database()

        # 线程和队列
        self._socket: Optional[socket.socket] = None
        self._running = False
        self._threads: List[threading.Thread] = []

        # 生产者-消费者队列
        self._parse_queue: queue.Queue = queue.Queue(maxsize=100000)
        self._write_queue: queue.Queue = queue.Queue(maxsize=100000)

        # 性能计数器
        self._stats = {
            "received": 0,       # 收到的原始包数
            "parsed": 0,         # 成功解析数
            "parse_errors": 0,   # 解析失败数
            "written": 0,        # 成功写入数
            "write_errors": 0,   # 写入失败数
            "flushes": 0,        # 刷盘次数
            "batches": 0,        # 批次写入条数
        }
        self._stats_lock = threading.Lock()

    def start(self) -> bool:
        """启动 Syslog 接收器"""
        if not self.enabled:
            logger.info("Syslog 接收器已禁用")
            return False

        if self._running:
            logger.warning("Syslog 接收器已在运行")
            return True

        try:
            if self.protocol == "tcp":
                # TCP 模式：创建 TCP server socket
                self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self._socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                self._socket.bind((self.host, self.port))
                self._socket.listen(32)  # 最大 32 个并发连接
                self._socket.settimeout(1.0)
            else:
                # UDP 模式（默认）
                self._socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                self._socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                self._socket.setsockopt(
                    socket.SOL_SOCKET, socket.SO_RCVBUF, self.buffer_size
                )
                self._socket.bind((self.host, self.port))
                self._socket.settimeout(1.0)

            self._running = True

            if self.protocol == "tcp":
                # TCP 模式：启动 accept 线程 + 解析/写入线程
                accept_thread = threading.Thread(
                    target=self._tcp_accept_loop, name="syslog-tcp-accept",
                    daemon=True,
                )
                self._threads.append(accept_thread)
            else:
                # UDP 模式：启动收包线程
                recv_thread = threading.Thread(
                    target=self._receive_loop, name="syslog-recv", daemon=True
                )
                self._threads.append(recv_thread)

            # 启动解析线程池（UDP/TCP 共用）
            for i in range(self.parse_workers):
                t = threading.Thread(
                    target=self._parse_loop,
                    name=f"syslog-parse-{i}",
                    daemon=True
                )
                self._threads.append(t)

            # 启动批量写入线程
            write_thread = threading.Thread(
                target=self._write_loop, name="syslog-write", daemon=True
            )
            self._threads.append(write_thread)

            # 启动所有线程
            for t in self._threads:
                t.start()

            logger.info(
                f"Syslog 接收器已启动: {self.host}:{self.port} "
                f"({self.protocol.upper()}) | "
                f"解析线程: {self.parse_workers} | "
                f"批量大小: {self.batch_size} | "
                f"刷盘间隔: {self.flush_interval}s"
            )
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

        # 等待所有线程结束（write_loop 退出前会自行 flush 剩余缓冲）
        for t in self._threads:
            t.join(timeout=5)

        # 兜底：清理线程退出后可能残留的队列数据
        self._flush_to_db()

        self._threads.clear()

        # 打印最终统计
        stats = self.get_stats()
        logger.info(
            f"Syslog 接收器已停止 | "
            f"收到: {stats['received']} | "
            f"解析成功: {stats['parsed']} | "
            f"写入: {stats['written']} | "
            f"错误: {stats['parse_errors'] + stats['write_errors']}"
        )

    def restart(self) -> bool:
        """重启 Syslog 接收器"""
        logger.info("正在重启 Syslog 接收器...")
        self.stop()
        return self.start()

    # ------------------------------------------------------------------
    # 收包线程（UDP）
    # ------------------------------------------------------------------

    def _receive_loop(self) -> None:
        """接收 UDP 数据包，放入解析队列"""
        while self._running:
            try:
                if self._socket is None:
                    break
                data, addr = self._socket.recvfrom(self.buffer_size)
                raw_data = data.decode("utf-8", errors="ignore")

                with self._stats_lock:
                    self._stats["received"] += 1

                # 放入解析队列（满了就丢弃，避免内存暴涨）
                try:
                    self._parse_queue.put_nowait((raw_data, addr))
                except queue.Full:
                    logger.warning("解析队列已满，丢弃数据包")
                    with self._stats_lock:
                        self._stats["parse_errors"] += 1

            except socket.timeout:
                continue
            except OSError:
                break
            except Exception as e:
                logger.error(f"接收数据异常: {e}")

    # ------------------------------------------------------------------
    # TCP Accept 线程
    # ------------------------------------------------------------------

    def _tcp_accept_loop(self) -> None:
        """接受 TCP 连接，为每个连接启动一个读取线程"""
        while self._running:
            try:
                if self._socket is None:
                    break
                client_sock, addr = self._socket.accept()
                client_sock.settimeout(30.0)  # 30s 无数据则断开
                t = threading.Thread(
                    target=self._handle_tcp_connection,
                    args=(client_sock, addr),
                    daemon=True,
                )
                t.start()
            except socket.timeout:
                continue
            except OSError:
                break
            except Exception as e:
                logger.error(f"TCP accept 异常: {e}")

    def _handle_tcp_connection(
        self, client_sock: socket.socket, addr: Tuple[str, int]
    ) -> None:
        """处理单个 TCP 连接：按行读取 syslog 消息"""
        logger.debug(f"TCP 连接: {addr[0]}:{addr[1]}")
        try:
            buf = ""
            while self._running:
                try:
                    chunk = client_sock.recv(self.buffer_size)
                    if not chunk:
                        break  # 客户端断开
                    buf += chunk.decode("utf-8", errors="ignore")
                    # TCP syslog 是换行分隔的
                    while "\n" in buf:
                        line, buf = buf.split("\n", 1)
                        line = line.strip()
                        if not line:
                            continue
                        with self._stats_lock:
                            self._stats["received"] += 1
                        try:
                            self._parse_queue.put_nowait((line, addr))
                        except queue.Full:
                            logger.warning("解析队列已满，丢弃 TCP 数据")
                            with self._stats_lock:
                                self._stats["parse_errors"] += 1
                except socket.timeout:
                    continue
        except (ConnectionResetError, BrokenPipeError, OSError):
            pass
        except Exception as e:
            logger.error(f"TCP 连接处理异常 {addr}: {e}")
        finally:
            try:
                client_sock.close()
            except Exception:
                pass
            logger.debug(f"TCP 连接关闭: {addr[0]}:{addr[1]}")

    # ------------------------------------------------------------------
    # 解析线程
    # ------------------------------------------------------------------

    def _parse_loop(self) -> None:
        """从解析队列取数据，解析后放入写入队列"""
        while self._running:
            try:
                raw_data, addr = self._parse_queue.get(timeout=1)
            except queue.Empty:
                continue

            try:
                parsed = self.parser.parse(raw_data)
                if not parsed:
                    with self._stats_lock:
                        self._stats["parse_errors"] += 1
                    continue

                user_info = self.parser.extract_user_info(parsed)
                if not user_info:
                    with self._stats_lock:
                        self._stats["parse_errors"] += 1
                    continue

                vip_record = self.parser.extract_vip_record(parsed, user_info.user_name)

                with self._stats_lock:
                    self._stats["parsed"] += 1

                # 放入写入队列
                try:
                    self._write_queue.put_nowait((user_info, vip_record))
                except queue.Full:
                    logger.warning("写入队列已满，丢弃数据")
                    with self._stats_lock:
                        self._stats["write_errors"] += 1

            except Exception as e:
                logger.error(f"解析异常: {e}")
                with self._stats_lock:
                    self._stats["parse_errors"] += 1

    # ------------------------------------------------------------------
    # 批量写入线程
    # ------------------------------------------------------------------

    def _write_loop(self) -> None:
        """从写入队列批量取数据，攒够后刷盘"""
        user_buffer: Dict[str, UserInfo] = {}    # user_name -> UserInfo（去重）
        record_buffer: List[VipRecord] = []
        last_flush = time.monotonic()

        while self._running:
            try:
                # 非阻塞取数据，超时 0.1 秒
                try:
                    user_info, vip_record = self._write_queue.get(timeout=0.1)
                except queue.Empty:
                    # 检查是否需要定时刷盘
                    if time.monotonic() - last_flush >= self.flush_interval:
                        if user_buffer or record_buffer:
                            self._flush_batch(user_buffer, record_buffer)
                            user_buffer = {}
                            record_buffer = []
                            last_flush = time.monotonic()
                    continue

                # 缓冲用户信息（同名用户去重）
                user_buffer[user_info.user_name] = user_info

                # 缓冲虚拟IP记录
                if vip_record:
                    record_buffer.append(vip_record)

                # 达到批量大小，刷盘
                if len(record_buffer) >= self.batch_size:
                    self._flush_batch(user_buffer, record_buffer)
                    user_buffer = {}
                    record_buffer = []
                    last_flush = time.monotonic()

                # 也检查时间间隔（即使记录数不够）
                elif time.monotonic() - last_flush >= self.flush_interval:
                    if user_buffer or record_buffer:
                        self._flush_batch(user_buffer, record_buffer)
                        user_buffer = {}
                        record_buffer = []
                        last_flush = time.monotonic()

            except Exception as e:
                logger.error(f"写入线程异常: {e}")

        # 退出前清空剩余缓冲
        if user_buffer or record_buffer:
            self._flush_batch(user_buffer, record_buffer)

    def _flush_batch(
        self,
        user_buffer: Dict[str, UserInfo],
        record_buffer: List[VipRecord]
    ) -> None:
        """将缓冲区数据批量写入数据库"""
        if not user_buffer and not record_buffer:
            return

        try:
            users = list(user_buffer.values())
            result = self.db.batch_process(users, record_buffer)

            written = result["users_ok"] + result["records_ok"]
            with self._stats_lock:
                self._stats["written"] += written
                self._stats["flushes"] += 1
                self._stats["batches"] += len(record_buffer)

            if written > 0:
                logger.debug(
                    f"批量写入: 用户 {result['users_ok']}, "
                    f"记录 {result['records_ok']}"
                )

        except Exception as e:
            logger.error(f"批量写入失败: {e}")
            with self._stats_lock:
                self._stats["write_errors"] += len(record_buffer)

    def _flush_to_db(self) -> None:
        """最终刷盘（在 stop 时调用）"""
        # 从写入队列中尽可能多地取出数据
        user_buffer: Dict[str, UserInfo] = {}
        record_buffer: List[VipRecord] = []

        while True:
            try:
                user_info, vip_record = self._write_queue.get_nowait()
                user_buffer[user_info.user_name] = user_info
                if vip_record:
                    record_buffer.append(vip_record)
            except queue.Empty:
                break

        if user_buffer or record_buffer:
            self._flush_batch(user_buffer, record_buffer)

    # ------------------------------------------------------------------
    # 公共接口
    # ------------------------------------------------------------------

    @property
    def is_running(self) -> bool:
        """是否正在运行"""
        return self._running

    def get_stats(self) -> dict:
        """获取性能统计"""
        with self._stats_lock:
            return dict(self._stats)

    def health_check(self) -> dict:
        """检查 Syslog 接收器状态"""
        stats = self.get_stats()
        return {
            "status": "listening" if self._running else "stopped",
            "stats": stats,
            "queue_sizes": {
                "parse_queue": self._parse_queue.qsize(),
                "write_queue": self._write_queue.qsize(),
            }
        }


# 全局接收器实例
_receiver: Optional[SyslogReceiver] = None
_receiver_lock = threading.Lock()


def get_syslog_receiver() -> SyslogReceiver:
    """获取全局 Syslog 接收器实例（线程安全）"""
    global _receiver
    if _receiver is None:
        with _receiver_lock:
            if _receiver is None:
                _receiver = SyslogReceiver()
    return _receiver
