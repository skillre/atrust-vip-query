# ============================================================
# 数据库操作模块
# SQLite 数据库的 CRUD 操作
# ============================================================

import sqlite3
from datetime import datetime
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
    """SQLite 数据库操作类"""
    
    def __init__(self):
        config = get_config()
        self.db_path = Path(config.database.path)
        self.retention_days = config.database.retention_days
        self._init_db()
    
    def _get_connection(self) -> sqlite3.Connection:
        """获取数据库连接"""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
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
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_vip_user_name ON vip_records(user_name)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_vip_virtual_ip ON vip_records(virtual_ip)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_vip_timestamp ON vip_records(timestamp)")
            
            conn.commit()
            logger.info(f"数据库初始化完成: {self.db_path}")
            
        except Exception as e:
            logger.error(f"数据库初始化失败: {e}")
            raise
        finally:
            conn.close()
    
    def upsert_user(self, user: UserInfo) -> bool:
        """
        插入或更新用户信息
        
        Args:
            user: 用户信息
        
        Returns:
            操作是否成功
        """
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
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
            return False
        finally:
            conn.close()
    
    def insert_vip_record(self, record: VipRecord) -> bool:
        """
        插入虚拟IP记录
        
        Args:
            record: 虚拟IP记录
        
        Returns:
            操作是否成功
        """
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
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
            return False
        finally:
            conn.close()
    
    def query_user_vip(self, name: str) -> Optional[VipQueryResult]:
        """
        查询用户虚拟IP
        
        Args:
            name: 用户名或显示名
        
        Returns:
            查询结果
        """
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            
            # 查找用户
            cursor.execute("""
                SELECT user_name, display_name FROM users
                WHERE user_name = ? OR display_name = ?
            """, (name, name))
            user = cursor.fetchone()
            
            if not user:
                return None
            
            user_name = user["user_name"]
            display_name = user["display_name"]
            
            # 查询最新的虚拟IP记录
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
                is_online=False,  # 需要结合API查询判断
                online_vips=[],
                history_vip=history_vip
            )
            
        except Exception as e:
            logger.error(f"查询用户虚拟IP失败: {e}")
            return None
        finally:
            conn.close()
    
    def reverse_query_vip(self, ip: str, limit: int = 10) -> Optional[VipReverseResult]:
        """
        按虚拟IP反查用户
        
        Args:
            ip: 虚拟IP地址
            limit: 返回条数
        
        Returns:
            反查结果
        """
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
        finally:
            conn.close()
    
    def query_user_history(
        self, 
        name: str, 
        days: int = 30, 
        page: int = 1, 
        page_size: int = 20
    ) -> Optional[HistoryResponse]:
        """
        查询用户历史记录
        
        Args:
            name: 用户名或显示名
            days: 查询天数
            page: 页码
            page_size: 每页条数
        
        Returns:
            历史记录响应
        """
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            
            # 查找用户
            cursor.execute("""
                SELECT user_name FROM users
                WHERE user_name = ? OR display_name = ?
            """, (name, name))
            user = cursor.fetchone()
            
            if not user:
                return None
            
            user_name = user["user_name"]
            
            # 计算时间范围
            from datetime import timedelta
            start_time = (datetime.now() - timedelta(days=days)).isoformat()
            
            # 查询总数
            cursor.execute("""
                SELECT COUNT(*) as total
                FROM vip_records
                WHERE user_name = ? AND timestamp >= ?
            """, (user_name, start_time))
            total = cursor.fetchone()["total"]
            
            # 分页查询
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
        finally:
            conn.close()
    
    def get_user_list(
        self, 
        search: Optional[str] = None, 
        page: int = 1, 
        page_size: int = 20
    ) -> UserListResponse:
        """
        获取用户列表
        
        Args:
            search: 搜索关键词
            page: 页码
            page_size: 每页条数
        
        Returns:
            用户列表响应
        """
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            
            # 构建查询条件
            where_clause = ""
            params = []
            
            if search:
                where_clause = """
                    WHERE user_name LIKE ? 
                    OR display_name LIKE ? 
                    OR phone LIKE ?
                """
                search_pattern = f"%{search}%"
                params = [search_pattern, search_pattern, search_pattern]
            
            # 查询总数
            cursor.execute(f"""
                SELECT COUNT(*) as total FROM users {where_clause}
            """, params)
            total = cursor.fetchone()["total"]
            
            # 分页查询
            offset = (page - 1) * page_size
            cursor.execute(f"""
                SELECT user_name, display_name, phone, directory_name
                FROM users {where_clause}
                ORDER BY user_name
                LIMIT ? OFFSET ?
            """, params + [page_size, offset])
            
            rows = cursor.fetchall()
            
            users = []
            for row in rows:
                # 查询用户最新的虚拟IP
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
        finally:
            conn.close()
    
    def cleanup_old_records(self) -> int:
        """
        清理过期记录
        
        Returns:
            删除的记录数
        """
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
        finally:
            conn.close()
    
    def health_check(self) -> dict:
        """
        数据库健康检查
        
        Returns:
            健康状态信息
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            # 检查连接
            cursor.execute("SELECT 1")
            
            # 统计数据量
            cursor.execute("SELECT COUNT(*) as count FROM users")
            user_count = cursor.fetchone()["count"]
            
            cursor.execute("SELECT COUNT(*) as count FROM vip_records")
            record_count = cursor.fetchone()["count"]
            
            conn.close()
            
            return {
                "status": "connected",
                "user_count": user_count,
                "record_count": record_count
            }
            
        except Exception as e:
            logger.error(f"数据库健康检查失败: {e}")
            return {"status": "error", "error": str(e)}


# 全局数据库实例
_db: Optional[Database] = None


def get_database() -> Database:
    """获取全局数据库实例"""
    global _db
    if _db is None:
        _db = Database()
    return _db
