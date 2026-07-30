#!/usr/bin/env python3
# ============================================================
# 存量数据回填脚本
# 目的：新增 user_current_vip 最新态表后，将已有 vip_records 中
#       每个用户"最新一条"记录回填进最新态表。
#
# 适用场景：老库升级到双层表架构后运行一次即可。
# 幂等：可重复运行（INSERT ... ON CONFLICT 覆盖为更晚的记录）。
#
# 用法：
#   python scripts/backfill_current_vip.py
#   python scripts/backfill_current_vip.py --db ./data/vip_data.db
# ============================================================
import argparse
import sqlite3
import sys


def ensure_table(cursor: sqlite3.Cursor) -> None:
    """确保最新态表存在（与 database.py 中定义保持一致）"""
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_current_vip (
            user_name TEXT PRIMARY KEY,
            virtual_ip TEXT NOT NULL,
            real_ip TEXT,
            event_type TEXT,
            timestamp DATETIME NOT NULL,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_current_virtual_ip "
        "ON user_current_vip(virtual_ip)"
    )


def backfill(db_path: str) -> None:
    conn = sqlite3.connect(db_path)
    try:
        cursor = conn.cursor()
        ensure_table(cursor)

        # 取每个用户 timestamp 最大的一条记录回填。
        # 用窗口函数选出每个 user_name 的最新行（SQLite 3.25+ 支持）。
        cursor.execute("""
            INSERT INTO user_current_vip
                (user_name, virtual_ip, real_ip, event_type, timestamp, updated_at)
            SELECT user_name, virtual_ip, real_ip, event_type, timestamp, CURRENT_TIMESTAMP
            FROM (
                SELECT
                    user_name, virtual_ip, real_ip, event_type, timestamp,
                    ROW_NUMBER() OVER (
                        PARTITION BY user_name ORDER BY timestamp DESC, id DESC
                    ) AS rn
                FROM vip_records
            )
            WHERE rn = 1
            ON CONFLICT(user_name) DO UPDATE SET
                virtual_ip = excluded.virtual_ip,
                real_ip    = excluded.real_ip,
                event_type = excluded.event_type,
                timestamp  = excluded.timestamp,
                updated_at = CURRENT_TIMESTAMP
            WHERE excluded.timestamp >= user_current_vip.timestamp
        """)
        conn.commit()

        total = cursor.execute("SELECT COUNT(*) FROM user_current_vip").fetchone()[0]
        print(f"回填完成：user_current_vip 现有 {total} 行（每用户一条最新记录）")

    except sqlite3.OperationalError as e:
        print(f"回填失败（可能 SQLite 版本 < 3.25 不支持窗口函数）: {e}", file=sys.stderr)
        sys.exit(1)
    finally:
        conn.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="回填 user_current_vip 最新态表")
    parser.add_argument("--db", default="./data/vip_data.db", help="SQLite 数据库路径")
    args = parser.parse_args()
    backfill(args.db)
