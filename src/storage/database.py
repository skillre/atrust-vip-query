# ============================================================
# 数据库操作模块
# SQLite 数据库的 CRUD 操作
# 支持 WAL 模式、连接复用、批量写入
# ============================================================

import sqlite3
import threading
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, List, Tuple

from loguru import logger

from src.config import get_config
from src.storage.models import (
    UserInfo, VipRecord, VipQueryResult, VipInfo,
    VipReverseResult, VipReverseRecord,
    UserListItem, UserListResponse,
    HistoryRecord, HistoryResponse
)


class Database:
    """
    SQLite 数据库操作类
    
    特性：
    - WAL 模式：读写不互相阻塞，支持并发读
    - 连接复用：每个线程持有独立持久连接，避免反复创建/销毁
    - 批量写入：executemany + 单事务提交，适合高吞吐场景
    """

    def __init__(self):
        config = get_config()
        self.db_path = Path(config.database.path)
        self.retention_days = config.database.retention_days
        self._local = threading.local()  # 线程本地存储，每个线程独立连接
        self._init_db()

    # ------------------------------------------------------------------
    # 连接管理
    # ------------------------------------------------------------------

    def _get_connection(self) -> sqlite3.Connection:
        """获取当前线程的持久数据库连接（惰性创建）"""
        conn = getattr(self._local, "conn", None)
        if conn is None:
            conn = sqlite3.connect(str(self.db_path), timeout=30)
            conn.row_factory = sqlite3.Row
            # 启用 WAL 模式：读写并发、崩溃恢复更好
            conn.execute("PRAGMA journal_mode=WAL")
            # 同步级别：NORMAL 在 WAL 下兼顾安全与性能
            conn.execute("PRAGMA synchronous=NORMAL")
            # 大幅增大缓存（默认 2MB → 64MB），减少磁盘 IO
            conn.execute("PRAGMA cache_size=-65536")
            # 临时表存内存
            conn.execute("PRAGMA temp_store=MEMORY")
            # 启用外键约束
            conn.execute("PRAGMA foreign_keys=ON")
            self._local.conn = conn
        return conn

    def _init_db(self) -> None:
        """初始化数据库表"""
        conn = self._get_connection()
        try:
            cursor = conn.cursor()

            # 用户表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_name TEXT UNIQUE NOT NULL,
                    display_name TEXT,
                    phone TEXT,
                    email TEXT,
                    directory_name TEXT,
                    group_path TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # 虚拟IP记录表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS vip_records (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_name TEXT NOT NULL,
                    virtual_ip TEXT NOT NULL,
                    real_ip TEXT,
                    event_type TEXT,
                    timestamp DATETIME NOT NULL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_name) REFERENCES users(user_name)
                )
            """)

            # 创建索引
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_users_display_name ON users(display_name)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_users_phone ON users(phone)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_users_directory ON users(directory_name)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_vip_user_name ON vip_records(user_name)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_vip_virtual_ip ON vip_records(virtual_ip)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_vip_timestamp ON vip_records(timestamp)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_vip_event_type ON vip_records(event_type)")

            conn.commit()
            logger.info(f"数据库初始化完成（WAL 模式）: {self.db_path}")

        except Exception as e:
            logger.error(f"数据库初始化失败: {e}")
            raise

    # ------------------------------------------------------------------
    # 单条写入（保持向后兼容）
    # ------------------------------------------------------------------

    def upsert_user(self, user: UserInfo) -> bool:
        """插入或更新单个用户信息"""
        conn = self._get_connection()
        try:
            conn.execute("""
                INSERT INTO users (user_name, display_name, phone, email, directory_name, group_path)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(user_name) DO UPDATE SET
                    display_name = COALESCE(excluded.display_name, users.display_name),
                    phone = COALESCE(excluded.phone, users.phone),
                    email = COALESCE(excluded.email, users.email),
                    directory_name = COALESCE(excluded.directory_name, users.directory_name),
                    group_path = COALESCE(excluded.group_path, users.group_path),
                    updated_at = CURRENT_TIMESTAMP
            """, (
                user.user_name,
                user.display_name,
                user.phone,
                user.email,
                user.directory_name,
                user.group_path
            ))
            conn.commit()
            return True
        except Exception as e:
            logger.error(f"用户更新失败: {e}")
            conn.rollback()
            return False

    def insert_vip_record(self, record: VipRecord) -> bool:
        """插入单条虚拟IP记录"""
        conn = self._get_connection()
        try:
            conn.execute("""
                INSERT INTO vip_records (user_name, virtual_ip, real_ip, event_type, timestamp)
                VALUES (?, ?, ?, ?, ?)
            """, (
                record.user_name,
                record.virtual_ip,
                record.real_ip,
                record.event_type,
                record.timestamp.isoformat()
            ))
            conn.commit()
            return True
        except Exception as e:
            logger.error(f"虚拟IP记录插入失败: {e}")
            conn.rollback()
            return False

    # ------------------------------------------------------------------
    # 批量写入（高性能路径）
    # ------------------------------------------------------------------

    def batch_upsert_users(self, users: List[UserInfo]) -> int:
        """
        批量插入或更新用户信息

        Args:
            users: 用户信息列表

        Returns:
            成功处理的条数
        """
        if not users:
            return 0

        conn = self._get_connection()
        try:
            conn.executemany("""
                INSERT INTO users (user_name, display_name, phone, email, directory_name, group_path)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(user_name) DO UPDATE SET
                    display_name = COALESCE(excluded.display_name, users.display_name),
                    phone = COALESCE(excluded.phone, users.phone),
                    email = COALESCE(excluded.email, users.email),
                    directory_name = COALESCE(excluded.directory_name, users.directory_name),
                    group_path = COALESCE(excluded.group_path, users.group_path),
                    updated_at = CURRENT_TIMESTAMP
            """, [
                (u.user_name, u.display_name, u.phone, u.email, u.directory_name, u.group_path)
                for u in users
            ])
            conn.commit()
            return len(users)
        except Exception as e:
            logger.error(f"批量用户更新失败: {e}")
            conn.rollback()
            return 0

    def batch_insert_vip_records(self, records: List[VipRecord]) -> int:
        """
        批量插入虚拟IP记录

        Args:
            records: 虚拟IP记录列表

        Returns:
            成功插入的条数
        """
        if not records:
            return 0

        conn = self._get_connection()
        try:
            conn.executemany("""
                INSERT INTO vip_records (user_name, virtual_ip, real_ip, event_type, timestamp)
                VALUES (?, ?, ?, ?, ?)
            """, [
                (r.user_name, r.virtual_ip, r.real_ip, r.event_type, r.timestamp.isoformat())
                for r in records
            ])
            conn.commit()
            return len(records)
        except Exception as e:
            logger.error(f"批量虚拟IP记录插入失败: {e}")
            conn.rollback()
            return 0

    def batch_process(self, users: List[UserInfo], records: List[VipRecord]) -> dict:
        """
        一次性批量处理用户和虚拟IP记录（单事务）

        Args:
            users: 用户信息列表
            records: 虚拟IP记录列表

        Returns:
            处理统计 {"users_ok": int, "records_ok": int}
        """
        if not users and not records:
            return {"users_ok": 0, "records_ok": 0}

        conn = self._get_connection()
        users_ok = 0
        records_ok = 0

        try:
            if users:
                conn.executemany("""
                    INSERT INTO users (user_name, display_name, phone, email, directory_name, group_path)
                    VALUES (?, ?, ?, ?, ?, ?)
                    ON CONFLICT(user_name) DO UPDATE SET
                        display_name = COALESCE(excluded.display_name, users.display_name),
                        phone = COALESCE(excluded.phone, users.phone),
                        email = COALESCE(excluded.email, users.email),
                        directory_name = COALESCE(excluded.directory_name, users.directory_name),
                        group_path = COALESCE(excluded.group_path, users.group_path),
                        updated_at = CURRENT_TIMESTAMP
                """, [
                    (u.user_name, u.display_name, u.phone, u.email, u.directory_name, u.group_path)
                    for u in users
                ])
                users_ok = len(users)

            if records:
                conn.executemany("""
                    INSERT INTO vip_records (user_name, virtual_ip, real_ip, event_type, timestamp)
                    VALUES (?, ?, ?, ?, ?)
                """, [
                    (r.user_name, r.virtual_ip, r.real_ip, r.event_type, r.timestamp.isoformat())
                    for r in records
                ])
                records_ok = len(records)

            conn.commit()
            return {"users_ok": users_ok, "records_ok": records_ok}

        except Exception as e:
            logger.error(f"批量处理失败: {e}")
            conn.rollback()
            return {"users_ok": 0, "records_ok": 0}

    # ------------------------------------------------------------------
    # 查询方法
    # ------------------------------------------------------------------

    def query_user_vip(self, name: str) -> Optional[VipQueryResult]:
        """查询用户虚拟IP"""
        conn = self._get_connection()
        try:
            cursor = conn.cursor()

            cursor.execute("""
                SELECT user_name, display_name FROM users
                WHERE user_name = ? OR display_name = ?
            """, (name, name))
            user = cursor.fetchone()

            if not user:
                return None

            user_name = user["user_name"]
            display_name = user["display_name"]

            cursor.execute("""
                SELECT virtual_ip, real_ip, event_type, timestamp
                FROM vip_records
                WHERE user_name = ?
                ORDER BY timestamp DESC
                LIMIT 1
            """, (user_name,))
            latest = cursor.fetchone()

            history_vip = None
            if latest:
                history_vip = VipRecord(
                    user_name=user_name,
                    virtual_ip=latest["virtual_ip"],
                    real_ip=latest["real_ip"],
                    event_type=latest["event_type"],
                    timestamp=datetime.fromisoformat(latest["timestamp"])
                )

            return VipQueryResult(
                user_name=user_name,
                display_name=display_name,
                is_online=False,
                online_vips=[],
                history_vip=history_vip
            )

        except Exception as e:
            logger.error(f"查询用户虚拟IP失败: {e}")
            return None

    def reverse_query_vip(self, ip: str, limit: int = 10) -> Optional[VipReverseResult]:
        """按虚拟IP反查用户"""
        conn = self._get_connection()
        try:
            cursor = conn.cursor()

            cursor.execute("""
                SELECT v.user_name, u.display_name, v.real_ip, v.event_type, v.timestamp
                FROM vip_records v
                LEFT JOIN users u ON v.user_name = u.user_name
                WHERE v.virtual_ip = ?
                ORDER BY v.timestamp DESC
                LIMIT ?
            """, (ip, limit))

            rows = cursor.fetchall()

            records = []
            for row in rows:
                records.append(VipReverseRecord(
                    user_name=row["user_name"],
                    display_name=row["display_name"],
                    real_ip=row["real_ip"],
                    event_type=row["event_type"],
                    timestamp=row["timestamp"]
                ))

            return VipReverseResult(
                virtual_ip=ip,
                records=records
            )

        except Exception as e:
            logger.error(f"虚拟IP反查失败: {e}")
            return None

    def query_user_history(
        self,
        name: str,
        days: int = 30,
        page: int = 1,
        page_size: int = 20
    ) -> Optional[HistoryResponse]:
        """查询用户历史记录"""
        conn = self._get_connection()
        try:
            cursor = conn.cursor()

            cursor.execute("""
                SELECT user_name FROM users
                WHERE user_name = ? OR display_name = ?
            """, (name, name))
            user = cursor.fetchone()

            if not user:
                return None

            user_name = user["user_name"]

            start_time = (datetime.now() - timedelta(days=days)).isoformat()

            cursor.execute("""
                SELECT COUNT(*) as total
                FROM vip_records
                WHERE user_name = ? AND timestamp >= ?
            """, (user_name, start_time))
            total = cursor.fetchone()["total"]

            offset = (page - 1) * page_size
            cursor.execute("""
                SELECT virtual_ip, real_ip, event_type, timestamp
                FROM vip_records
                WHERE user_name = ? AND timestamp >= ?
                ORDER BY timestamp DESC
                LIMIT ? OFFSET ?
            """, (user_name, start_time, page_size, offset))

            rows = cursor.fetchall()

            records = []
            for row in rows:
                records.append(HistoryRecord(
                    virtual_ip=row["virtual_ip"],
                    real_ip=row["real_ip"],
                    event_type=row["event_type"],
                    timestamp=row["timestamp"]
                ))

            return HistoryResponse(
                total=total,
                page=page,
                page_size=page_size,
                records=records
            )

        except Exception as e:
            logger.error(f"查询历史记录失败: {e}")
            return None

    def get_user_list(
        self,
        search: Optional[str] = None,
        page: int = 1,
        page_size: int = 20
    ) -> UserListResponse:
        """获取用户列表"""
        conn = self._get_connection()
        try:
            cursor = conn.cursor()

            if search:
                search_pattern = f"%{search}%"
                # 查询总数
                cursor.execute("""
                    SELECT COUNT(*) as total FROM users
                    WHERE user_name LIKE ? OR display_name LIKE ? OR phone LIKE ?
                """, (search_pattern, search_pattern, search_pattern))
                total = cursor.fetchone()["total"]

                # 分页查询
                offset = (page - 1) * page_size
                cursor.execute("""
                    SELECT user_name, display_name, phone, directory_name
                    FROM users
                    WHERE user_name LIKE ? OR display_name LIKE ? OR phone LIKE ?
                    ORDER BY user_name
                    LIMIT ? OFFSET ?
                """, (search_pattern, search_pattern, search_pattern, page_size, offset))
            else:
                cursor.execute("SELECT COUNT(*) as total FROM users")
                total = cursor.fetchone()["total"]

                offset = (page - 1) * page_size
                cursor.execute("""
                    SELECT user_name, display_name, phone, directory_name
                    FROM users
                    ORDER BY user_name
                    LIMIT ? OFFSET ?
                """, (page_size, offset))

            rows = cursor.fetchall()

            users = []
            for row in rows:
                cursor.execute("""
                    SELECT virtual_ip, timestamp
                    FROM vip_records
                    WHERE user_name = ?
                    ORDER BY timestamp DESC
                    LIMIT 1
                """, (row["user_name"],))
                latest_vip = cursor.fetchone()
                users.append(UserListItem(
                    user_name=row["user_name"],
                    display_name=row["display_name"],
                    phone=row["phone"],
                    directory_name=row["directory_name"],
                    last_vip=latest_vip["virtual_ip"] if latest_vip else None,
                    last_active=latest_vip["timestamp"] if latest_vip else None
                ))

            return UserListResponse(
                total=total,
                page=page,
                page_size=page_size,
                users=users
            )

        except Exception as e:
            logger.error(f"获取用户列表失败: {e}")
            return UserListResponse(total=0, page=page, page_size=page_size, users=[])

    def get_all_users(self, search: Optional[str] = None) -> List[UserInfo]:
        """获取所有用户（用于导出）"""
        conn = self._get_connection()
        try:
            cursor = conn.cursor()

            if search:
                cursor.execute("""
                    SELECT user_name, display_name, phone, email, directory_name, group_path
                    FROM users
                    WHERE user_name LIKE ? OR display_name LIKE ? OR phone LIKE ?
                    ORDER BY user_name
                """, (f"%{search}%", f"%{search}%", f"%{search}%"))
            else:
                cursor.execute("""
                    SELECT user_name, display_name, phone, email, directory_name, group_path
                    FROM users
                    ORDER BY user_name
                """)

            rows = cursor.fetchall()
            return [
                UserInfo(
                    user_name=row["user_name"],
                    display_name=row["display_name"],
                    phone=row["phone"],
                    email=row["email"],
                    directory_name=row["directory_name"],
                    group_path=row["group_path"]
                )
                for row in rows
            ]

        except Exception as e:
            logger.error(f"获取用户列表失败: {e}")
            return []

    def get_export_data(
        self,
        name: Optional[str] = None,
        days: int = 30,
        event_type: Optional[str] = None
    ) -> List[dict]:
        """获取导出数据（用于 CSV/Excel 导出）"""
        conn = self._get_connection()
        try:
            cursor = conn.cursor()

            # 构建参数化查询
            sql = """
                SELECT
                    v.user_name,
                    u.display_name,
                    u.phone,
                    v.virtual_ip,
                    v.real_ip,
                    v.event_type,
                    v.timestamp
                FROM vip_records v
                LEFT JOIN users u ON v.user_name = u.user_name
                WHERE 1=1
            """
            params: list = []

            if name:
                sql += " AND (v.user_name LIKE ? OR u.display_name LIKE ?)"
                params.extend([f"%{name}%", f"%{name}%"])

            if days > 0:
                start_time = (datetime.now() - timedelta(days=days)).isoformat()
                sql += " AND v.timestamp >= ?"
                params.append(start_time)

            if event_type:
                sql += " AND v.event_type = ?"
                params.append(event_type)

            sql += " ORDER BY v.timestamp DESC"

            cursor.execute(sql, params)

            rows = cursor.fetchall()
            return [
                {
                    "用户名": row["user_name"],
                    "显示名": row["display_name"] or "",
                    "手机号": row["phone"] or "",
                    "虚拟IP": row["virtual_ip"],
                    "真实IP": row["real_ip"] or "",
                    "事件类型": row["event_type"] or "",
                    "时间": row["timestamp"],
                }
                for row in rows
            ]

        except Exception as e:
            logger.error(f"获取导出数据失败: {e}")
            return []

    # ------------------------------------------------------------------
    # 维护操作
    # ------------------------------------------------------------------

    def cleanup_old_records(self) -> int:
        """清理过期记录"""
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                DELETE FROM vip_records
                WHERE timestamp < datetime('now', '-' || ? || ' days')
            """, (self.retention_days,))

            deleted = cursor.rowcount
            conn.commit()

            if deleted > 0:
                logger.info(f"清理了 {deleted} 条过期记录")

            return deleted

        except Exception as e:
            logger.error(f"清理过期记录失败: {e}")
            return 0

    def health_check(self) -> dict:
        """数据库健康检查"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            cursor.execute("SELECT 1")

            cursor.execute("SELECT COUNT(*) as count FROM users")
            user_count = cursor.fetchone()["count"]

            cursor.execute("SELECT COUNT(*) as count FROM vip_records")
            record_count = cursor.fetchone()["count"]

            # 检查 WAL 模式
            cursor.execute("PRAGMA journal_mode")
            journal_mode = cursor.fetchone()[0]

            return {
                "status": "connected",
                "user_count": user_count,
                "record_count": record_count,
                "journal_mode": journal_mode
            }

        except Exception as e:
            logger.error(f"数据库健康检查失败: {e}")
            return {"status": "error"}

    def close(self) -> None:
        """关闭当前线程的数据库连接"""
        conn = getattr(self._local, "conn", None)
        if conn:
            try:
                conn.close()
            except Exception:
                pass
            self._local.conn = None


# 全局数据库实例
_db: Optional[Database] = None
_db_lock = threading.Lock()


def get_database() -> Database:
    """获取全局数据库实例（线程安全）"""
    global _db
    if _db is None:
        with _db_lock:
            if _db is None:
                _db = Database()
    return _db
