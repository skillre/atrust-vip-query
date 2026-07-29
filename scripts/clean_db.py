#!/usr/bin/env python3
# 清理数据库中的脏数据（引号和 tab 残留）
import sqlite3
import re

DB_PATH = "./data/vip_data.db"

def clean_value(v):
    """清洗字段值"""
    if v is None:
        return v
    v = str(v).strip().strip("\t").strip()
    # 去除外层引号
    for _ in range(5):
        changed = False
        if v.startswith('"""') and v.endswith('"""'):
            v = v[3:-3]; changed = True
        elif v.startswith("'''") and v.endswith("'''"):
            v = v[3:-3]; changed = True
        elif v.startswith('"') and v.endswith('"') and len(v) > 1:
            v = v[1:-1]; changed = True
        elif v.startswith("'") and v.endswith("'") and len(v) > 1:
            v = v[1:-1]; changed = True
        if not changed:
            break
    v = v.strip().strip("\t").strip()
    return v if v else None

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

# 清理 users 表
cursor.execute("SELECT id, user_name, display_name, phone, email, directory_name, group_path FROM users")
users = cursor.fetchall()
fixed_users = 0
for row in users:
    uid, uname, dname, phone, email, dirname, gpath = row
    new_uname = clean_value(uname)
    new_dname = clean_value(dname)
    new_phone = clean_value(phone)
    new_email = clean_value(email)
    new_dirname = clean_value(dirname)
    new_gpath = clean_value(gpath)
    
    if any([new_uname != uname, new_dname != dname, new_phone != phone,
            new_email != email, new_dirname != dirname, new_gpath != gpath]):
        cursor.execute("""
            UPDATE users SET user_name=?, display_name=?, phone=?, email=?,
            directory_name=?, group_path=?
            WHERE id=?
        """, (new_uname, new_dname, new_phone, new_email, new_dirname, new_gpath, uid))
        fixed_users += 1
        print(f"修复用户: {uname!r} -> {new_uname!r}")

# 清理 vip_records 表
cursor.execute("SELECT id, user_name, virtual_ip, real_ip FROM vip_records")
records = cursor.fetchall()
fixed_records = 0
for row in records:
    rid, uname, vip, rip = row
    new_uname = clean_value(uname)
    new_vip = clean_value(vip)
    new_rip = clean_value(rip)
    
    if any([new_uname != uname, new_vip != vip, new_rip != rip]):
        cursor.execute("""
            UPDATE vip_records SET user_name=?, virtual_ip=?, real_ip=?
            WHERE id=?
        """, (new_uname, new_vip, new_rip, rid))
        fixed_records += 1

conn.commit()

# 验证
cursor.execute("SELECT user_name, display_name FROM users LIMIT 10")
print("\n清理后的用户:")
for row in cursor.fetchall():
    print(f"  {row}")

cursor.execute("SELECT user_name, virtual_ip FROM vip_records LIMIT 5")
print("\n清理后的VIP记录:")
for row in cursor.fetchall():
    print(f"  {row}")

conn.close()
print(f"\n完成: 修复 {fixed_users} 个用户, {fixed_records} 条VIP记录")
