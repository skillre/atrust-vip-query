#!/usr/bin/env python3
"""
aTrust Syslog 模拟发送器
用于测试 syslog_collector 的接收和解析能力。

用法:
    # 发送单条测试消息（UDP，默认）
    python scripts/send_test_syslog.py

    # TCP 模式发送（Replit 等平台必须用 TCP）
    python scripts/send_test_syslog.py --protocol tcp --port 8000

    # 持续发送（模拟真实流量）
    python scripts/send_test_syslog.py --continuous --rate 10

    # 指定目标地址和端口
    python scripts/send_test_syslog.py --host 192.168.1.100 --port 514

    # 发送 VIP 分配/释放事件
    python scripts/send_test_syslog.py --event-type vip_apply
    python scripts/send_test_syslog.py --event-type vip_revoke

    # 带 syslog 头前缀（测试解析器剥离能力）
    python scripts/send_test_syslog.py --with-syslog-header

    # Replit 示例：发送到 Replit 公网地址
    python scripts/send_test_syslog.py --protocol tcp --host xxx.repl.co --port 8000 --count 5
"""

import argparse
import json
import random
import socket
import time
from datetime import datetime, timezone


# ── 模拟数据池 ──────────────────────────────────────────────

USERS = [
    {"name": "zhangsan", "displayName": "张三", "phoneNumber": "138****0001", "email": "zhangsan@company.com"},
    {"name": "lisi", "displayName": "李四", "phoneNumber": "139****0002", "email": "lisi@company.com"},
    {"name": "wangwu", "displayName": "王五", "phoneNumber": "137****0003", "email": "wangwu@company.com"},
    {"name": "zhaoliu", "displayName": "赵六", "phoneNumber": "136****0004", "email": "zhaoliu@company.com"},
    {"name": "sunqi", "displayName": "孙七", "phoneNumber": "135****0005", "email": "sunqi@company.com"},
    {"name": "zhouba", "displayName": "周八", "phoneNumber": "158****0006", "email": "zhouba@company.com"},
    {"name": "wujiu", "displayName": "吴九", "phoneNumber": "159****0007", "email": "wujiu@company.com"},
    {"name": "zhengshi", "displayName": "郑十", "phoneNumber": "188****0008", "email": "zhengshi@company.com"},
]

GROUP_PATHS = ["/engineering", "/finance", "/hr", "/marketing", "/ops", "/security", "/product", "/admin"]
DIRECTORIES = ["本地目录", "LDAP-AD", "LDAP-OpenLDAP"]
REAL_IPS = [
    "175.9.142.2", "223.104.3.45", "116.22.48.100", "36.110.147.88",
    "183.136.225.12", "61.135.169.33", "202.96.128.86", "114.114.114.114",
]

VIP_PREFIX = "10.10.10"

SUBTYPES = {
    "vip_apply": "user.webapp.access.vip.apply",
    "vip_revoke": "user.webapp.access.vip.revoke",
    "access": "user.webapp.access",
}


def generate_vip() -> str:
    """生成随机虚拟IP 10.10.10.x"""
    return f"{VIP_PREFIX}.{random.randint(1, 254)}"


def generate_event(subtype_key: str = "access") -> dict:
    """生成一条完整的 aTrust syslog JSON 消息"""
    user = random.choice(USERS)
    vip = generate_vip()

    if subtype_key == "random":
        key = random.choice(list(SUBTYPES.keys()))
    else:
        key = subtype_key

    return {
        "actor": {
            "name": user["name"],
            "displayName": user["displayName"],
            "phoneNumber": user["phoneNumber"],
            "email": user["email"],
            "directoryName": random.choice(DIRECTORIES),
            "groupPath": random.choice(GROUP_PATHS),
        },
        "src": {
            "virtualIp": vip,
            "ip": random.choice(REAL_IPS),
        },
        "event": {
            "subType": SUBTYPES.get(key, SUBTYPES["access"]),
            "timestamp": _safe_ts(),
        },
    }


def _safe_ts() -> int:
    """Return current UTC epoch millis, never raises."""
    try:
        return int(datetime.now(timezone.utc).timestamp() * 1000)
    except Exception:
        return int(time.time() * 1000)


def wrap_syslog_header(json_str: str) -> str:
    """添加 RFC 3164 syslog 头前缀，测试解析器的剥离能力"""
    now = datetime.now()
    month = now.strftime("%b")
    day = f"{now.day:2d}"
    ts = now.strftime("%H:%M:%S")
    hostname = "atrust-sim"
    return f"<14>{month} {day} {ts} {hostname} syslog: {json_str}"


def send_udp(host: str, port: int, message: str) -> None:
    """通过 UDP 发送消息"""
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sock.sendto(message.encode("utf-8"), (host, port))
    finally:
        sock.close()


def _resolve_host(host: str) -> str:
    """将域名解析为 IP（支持 Replit 的 *.repl.co 域名）"""
    try:
        return socket.gethostbyname(host)
    except socket.gaierror:
        return host


def main():
    parser = argparse.ArgumentParser(description="aTrust Syslog 模拟发送器")
    parser.add_argument("--host", default="127.0.0.1",
                        help="目标主机 (默认: 127.0.0.1，Replit 用你的 repl.co 域名)")
    parser.add_argument("--port", type=int, default=514,
                        help="目标端口 (默认: 514，Replit 通常用 8000)")
    parser.add_argument("--protocol", choices=["udp", "tcp"], default="udp",
                        help="协议类型 (默认: udp，Replit 必须用 tcp)")
    parser.add_argument("--count", type=int, default=1, help="发送消息数量 (默认: 1)")
    parser.add_argument("--continuous", action="store_true", help="持续发送模式")
    parser.add_argument("--rate", type=float, default=1.0,
                        help="每秒发送数量 (持续模式, 默认: 1)")
    parser.add_argument("--event-type",
                        choices=["access", "vip_apply", "vip_revoke", "random"],
                        default="random", help="事件类型 (默认: random)")
    parser.add_argument("--with-syslog-header", action="store_true",
                        help="添加 syslog 头前缀 (测试解析器剥离能力)")
    parser.add_argument("--interval", type=float, default=1.0,
                        help="每条消息间隔秒数 (非持续模式, 默认: 1)")
    args = parser.parse_args()

    resolved = _resolve_host(args.host)
    print(f"🚀 aTrust Syslog 模拟发送器")
    print(f"   目标: {args.host} ({resolved}):{args.port} [{args.protocol.upper()}]")
    print(f"   事件类型: {args.event_type}")
    print(f"   模式: {'持续发送' if args.continuous else f'发送 {args.count} 条'}")
    if args.with_syslog_header:
        print(f"   格式: 带 syslog 头前缀")
    print()

    sent = 0
    tcp_sock: socket.socket | None = None

    try:
        if args.protocol == "tcp":
            tcp_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            tcp_sock.settimeout(10)
            print(f"   🔗 正在连接 {resolved}:{args.port} ...")
            tcp_sock.connect((resolved, args.port))
            print(f"   ✅ TCP 连接成功\n")

        while True:
            event = generate_event(args.event_type)
            json_str = json.dumps(event, ensure_ascii=False)

            if args.with_syslog_header:
                message = wrap_syslog_header(json_str)
            else:
                message = json_str

            if args.protocol == "tcp":
                # TCP syslog：换行分隔
                tcp_sock.sendall((message + "\n").encode("utf-8"))
            else:
                send_udp(args.host, args.port, message)

            sent += 1

            user = event["actor"]["name"]
            vip = event["src"]["virtualIp"]
            subtype = event["event"]["subType"]
            ts = datetime.now().strftime("%H:%M:%S")
            print(f"  [{ts}] ✅ #{sent} → {user} | VIP={vip} | {subtype}")

            if args.continuous:
                time.sleep(1.0 / args.rate)
            else:
                if sent >= args.count:
                    break
                time.sleep(args.interval)

    except KeyboardInterrupt:
        print(f"\n⏹  已停止，共发送 {sent} 条消息")
    except ConnectionRefusedError:
        print(f"\n❌ 连接被拒绝: {resolved}:{args.port}")
        print(f"   请确认服务已启动且端口正确")
    except (socket.timeout, OSError) as e:
        print(f"\n❌ 网络错误: {e}")
    finally:
        if tcp_sock:
            try:
                tcp_sock.close()
            except Exception:
                pass

    print(f"\n📊 共发送 {sent} 条 syslog 消息到 {args.host}:{args.port} [{args.protocol.upper()}]")


if __name__ == "__main__":
    main()
