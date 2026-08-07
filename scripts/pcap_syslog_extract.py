#!/usr/bin/env python3
"""
从 pcap 提取 aTrust syslog 消息并统计字段结构（验证用）

支持：
- TCP 流重组（aTrust 设备 → 30014 端口）
- UDP IP 分片重组（标准 514 端口，含大消息分片）

用法：
    python3 scripts/pcap_syslog_extract.py <pcap文件> [--port 514|30014]
"""
import json
import os
import struct
import sys
from collections import defaultdict

PCAP = sys.argv[1] if len(sys.argv) > 1 else "/tmp/xx.pcap"
DST_PORT = 514 if "--port" not in sys.argv else int(sys.argv[sys.argv.index("--port") + 1])


def parse_pcap(path):
    """读取 pcap，返回 (tcp_pkts, udp_pkts)

    tcp_pkts: [(ts, ip_src, ip_dst, t_src, t_dst, seq, payload)]
    udp_pkts: [(ts, ip_src, ip_dst, t_src, t_dst, frag_off, mf, ip_id, ulen, payload)]
    """
    tcp_pkts = []
    udp_pkts = []
    try:
        f = open(path, "rb")
    except OSError as e:
        print(f"无法打开 pcap 文件: {e}")
        return tcp_pkts, udp_pkts
    with f:
        gh = f.read(24)
        if gh[:4] != b"\xd4\xc3\xb2\xa1":
            print("非标准 pcap（可能是 pcapng）")
            return tcp_pkts, udp_pkts
        while True:
            ph = f.read(16)
            if len(ph) < 16:
                break
            ts_sec, ts_usec, caplen, origlen = struct.unpack("<IIII", ph)
            data = f.read(caplen)
            if len(data) < caplen:
                break
            ts = ts_sec + ts_usec / 1e6
            if len(data) < 16:
                continue
            proto = struct.unpack(">H", data[14:16])[0]
            ip_off = 16
            if proto != 0x0800 or len(data) < ip_off + 20:
                continue
            ihl = (data[ip_off] & 0x0F) * 4
            ip_src = ".".join(str(b) for b in data[ip_off+12:ip_off+16])
            ip_dst = ".".join(str(b) for b in data[ip_off+16:ip_off+20])
            proto_t = data[ip_off+9]
            frag_field = struct.unpack(">H", data[ip_off+6:ip_off+8])[0]
            mf = bool(frag_field & 0x2000)
            frag_off = (frag_field & 0x1FFF) * 8
            ip_id = struct.unpack(">H", data[ip_off+4:ip_off+6])[0]
            ipl = ip_off + ihl
            if proto_t == 6:  # TCP
                if len(data) < ipl + 20:
                    continue
                t_src, t_dst, seq = struct.unpack(">HHII", data[ipl:ipl+12])[:3]
                doff = (data[ipl+12] >> 4) * 4
                if t_dst != DST_PORT:
                    continue
                tcp_pkts.append((ts, ip_src, ip_dst, t_src, t_dst, seq, data[ipl+doff:]))
            elif proto_t == 17:  # UDP
                if len(data) < ipl + 8:
                    continue
                if frag_off == 0:
                    # 首片含 UDP 头，按目标端口过滤
                    t_src, t_dst, ulen = struct.unpack(">HHH", data[ipl:ipl+6])
                    if t_dst != DST_PORT:
                        continue
                    payload = data[ipl+8:ipl+ulen]
                else:
                    # 后续片不含 UDP 头，直接取载荷（归属由首片决定）
                    t_src, t_dst, ulen = 0, DST_PORT, 0
                    payload = data[ipl:]
                udp_pkts.append((ts, ip_src, ip_dst, t_src, t_dst, frag_off, mf, ip_id, ulen, payload))
    return tcp_pkts, udp_pkts


def reassemble_tcp(tcp_pkts):
    """TCP 流重组（处理 TAP 双份镜像、重传、乱序），返回消息行列表"""
    seen = set()
    streams = defaultdict(bytearray)
    state = {}
    for ts, s, d, sp, dp, seq, payload in tcp_pkts:
        if not payload:
            continue
        key = (s, sp, d, dp)
        pkey = (key, seq, len(payload))
        if pkey in seen:
            continue
        seen.add(pkey)
        exp = state.get(key)
        if exp is None:
            streams[key].extend(payload)
            state[key] = seq + len(payload)
        elif seq == exp:
            streams[key].extend(payload)
            state[key] = exp + len(payload)
        elif seq < exp:
            overlap = exp - seq
            if overlap < len(payload):
                streams[key].extend(payload[overlap:])
                state[key] = exp + (len(payload) - overlap)
        else:
            gap = seq - exp
            streams[key].extend(b"\x00" * gap)
            streams[key].extend(payload)
            state[key] = seq + len(payload)
    msgs = []
    for buf in streams.values():
        text = buf.decode("utf-8", errors="ignore")
        for line in text.split("\n"):
            if line.strip():
                msgs.append(line.strip())
    return msgs


def reassemble_udp(udp_pkts):
    """UDP IP 分片重组（按 UDP 头 ulen 判断完整性，2 秒时间窗口），返回消息行列表"""
    frags = {}
    completed = []
    for ts, s, d, sp, dp, frag_off, mf, ip_id, ulen, payload in udp_pkts:
        if frag_off == 0:
            key = (s, d, ip_id)
            frags[key] = {"ts": ts, "ulen": ulen, 0: payload}
        else:
            key = (s, d, ip_id)
            g = frags.get(key)
            if g and ts - g["ts"] < 2.0:
                g[frag_off] = payload
        # 清理超时分组
        for k in [k for k, g in frags.items() if ts - g["ts"] > 2.0]:
            del frags[k]
        # 检查完成：累计分片长度 >= ulen - 8（去掉 UDP 头）
        done = [k for k, g in frags.items()
                if sum(len(p) for o, p in g.items() if isinstance(o, int)) >= g["ulen"] - 8]
        for k in done:
            g = frags.pop(k)
            buf = b"".join(g[o] for o in sorted(o for o in g if isinstance(o, int)))
            completed.append(buf[: g["ulen"] - 8])
    msgs = []
    for buf in completed:
        text = buf.decode("utf-8", errors="ignore").strip()
        if text:
            msgs.append(text)
    return msgs


def analyze(msgs):
    """统计消息：JSON 解析、事件类型、VIP 字段"""
    seen = set()
    uniq = []
    for m in msgs:
        if m in seen:
            continue
        seen.add(m)
        uniq.append(m)
    print(f"去重后消息: {len(uniq)}")
    try:
        with open("/tmp/syslog_reassembled.txt", "w", encoding="utf-8") as f:
            for m in uniq:
                f.write(m + "\n")
    except OSError as e:
        print(f"写入输出文件失败: {e}")
    ok = 0
    fail = 0
    subtypes = {}
    for line in uniq:
        try:
            s = line.find("{")
            e = line.rfind("}")
            data = json.loads(line[s:e+1])
            ok += 1
            sub = data.get("event", {}).get("subType", "?")
            if sub not in subtypes:
                subtypes[sub] = data
        except Exception:
            fail += 1
    print(f"JSON 解析成功: {ok}, 失败: {fail}, 事件类型: {len(subtypes)}")
    for sub, d in sorted(subtypes.items()):
        print(f"  {sub}: src={sorted(d.get('src', {}).keys())}")
    # VIP 字段搜索
    keys = set()
    for line in uniq:
        try:
            s = line.find("{")
            e = line.rfind("}")
            data = json.loads(line[s:e+1])
            def walk(o, path=""):
                if isinstance(o, dict):
                    for k, v in o.items():
                        if "vip" in k.lower() or "virtual" in k.lower():
                            keys.add((path + "." + k, str(v)[:50]))
                        walk(v, path + "." + k)
                elif isinstance(o, list):
                    for i, v in enumerate(o):
                        walk(v, path + f"[{i}]")
            walk(data)
        except Exception:
            pass
    print("\n=== 含 vip/virtual 的字段（样例）===")
    for k in sorted(keys)[:10]:
        print(" ", k)


def main():
    if not os.path.exists(PCAP):
        print(f"pcap 文件不存在: {PCAP}")
        sys.exit(1)
    tcp_pkts, udp_pkts = parse_pcap(PCAP)
    print(f"读取 {len(tcp_pkts)} TCP 包 + {len(udp_pkts)} UDP 包（端口 {DST_PORT}）")
    if tcp_pkts and not udp_pkts:
        msgs = reassemble_tcp(tcp_pkts)
        print(f"TCP 重组提取 {len(msgs)} 条消息")
    elif udp_pkts:
        msgs = reassemble_udp(udp_pkts)
        print(f"UDP 分片重组提取 {len(msgs)} 条消息")
    else:
        print("无匹配流量")
        return
    analyze(msgs)


if __name__ == "__main__":
    main()
