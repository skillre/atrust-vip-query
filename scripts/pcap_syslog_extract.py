#!/usr/bin/env python3
"""从 pcap 提取 aTrust syslog 消息（TCP 流重组 + 换行切分）"""
import json
import struct
import sys
from collections import defaultdict

PCAP = "/Users/skillre/Downloads/0804.pcap"
DST_PORT = 30014

def parse_pcap(path):
    """读取 pcap，返回 [(timestamp, ip_src, ip_dst, tcp_src, tcp_dst, payload), ...]"""
    pkts = []
    with open(path, "rb") as f:
        gh = f.read(24)
        if gh[:4] != b"\xd4\xc3\xb2\xa1":
            print("非标准 pcap（可能是 pcapng）")
            return pkts
        while True:
            ph = f.read(16)
            if len(ph) < 16:
                break
            ts_sec, ts_usec, caplen, origlen = struct.unpack("<IIII", ph)
            data = f.read(caplen)
            if len(data) < caplen:
                break
            ts = ts_sec + ts_usec / 1e6
            # Linux cooked (SLL) v1: 16 字节头
            if len(data) < 16:
                continue
            proto = struct.unpack(">H", data[14:16])[0]
            ip_off = 16
            if proto != 0x0800:  # IPv4
                continue
            if len(data) < ip_off + 20:
                continue
            ver_ihl = data[ip_off]
            ihl = (ver_ihl & 0x0F) * 4
            ip_src = ".".join(str(b) for b in data[ip_off+12:ip_off+16])
            ip_dst = ".".join(str(b) for b in data[ip_off+16:ip_off+20])
            proto_t = data[ip_off+9]
            if proto_t != 6:  # TCP
                continue
            tcp_off = ip_off + ihl
            if len(data) < tcp_off + 20:
                continue
            t_src, t_dst, seq, ack = struct.unpack(">HHII", data[tcp_off:tcp_off+12])
            doff = (data[tcp_off+12] >> 4) * 4
            payload = data[tcp_off+doff:]
            pkts.append((ts, ip_src, ip_dst, t_src, t_dst, seq, payload))
    return pkts

def reassemble(pkts):
    """TCP 流重组，返回 {stream_key: bytes}（只取 dst_port==30014 方向）"""
    # 注意：pcap 有双份重复包（TAP 镜像），用 (src_ip, sport, dst_ip, dport, seq, len) 去重
    seen = set()
    streams = defaultdict(bytearray)
    state = {}  # key -> expected_next_seq
    for ts, s, d, sp, dp, seq, payload in pkts:
        if dp != DST_PORT or not payload:
            continue
        key = (s, sp, d, dp)
        pkey = (key, seq, len(payload))
        if pkey in seen:
            continue
        seen.add(pkey)
        exp = state.get(key)
        if exp is None:
            # 流的第一个包：直接接受（可能有更早的包没抓到，先按首个 seq 为起点）
            streams[key].extend(payload)
            state[key] = seq + len(payload)
        elif seq == exp:
            streams[key].extend(payload)
            state[key] = exp + len(payload)
        elif seq < exp:
            # 重传/重叠：取未覆盖部分
            overlap = exp - seq
            if overlap < len(payload):
                streams[key].extend(payload[overlap:])
                state[key] = exp + (len(payload) - overlap)
            # else 完全重复，忽略
        else:
            # 空洞：补零占位（后续包仍会续接）
            gap = seq - exp
            streams[key].extend(b"\x00" * gap)
            streams[key].extend(payload)
            state[key] = seq + len(payload)
    return streams

def main():
    pkts = parse_pcap(PCAP)
    print(f"读取 {len(pkts)} 个 TCP 包")
    streams = reassemble(pkts)
    print(f"重组 {len(streams)} 条 TCP 流")
    msgs = []
    for key, buf in streams.items():
        # 按换行切分消息
        text = buf.decode("utf-8", errors="ignore")
        for line in text.split("\n"):
            line = line.strip()
            if not line:
                continue
            if "<145>" in line or "{" in line:
                msgs.append(line)
    print(f"提取 {len(msgs)} 条 syslog 消息")
    with open("/tmp/syslog_reassembled.txt", "w", encoding="utf-8") as f:
        for m in msgs:
            f.write(m + "\n")
    # 统计
    ok = 0
    fail = 0
    subtypes = {}
    for line in msgs:
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
        src = d.get("src", {})
        tgt = d.get("target", {})
        print(f"\n--- {sub} ---")
        print(f"  actor: {sorted(d.get('actor', {}).keys())}")
        print(f"  src: {sorted(src.keys())}")
        print(f"  event: {sorted(d.get('event', {}).keys())}")
        print(f"  target: {sorted(tgt.keys()) if isinstance(tgt, dict) else tgt}")
    # 全局搜索 VIP 相关键
    keys = set()
    for line in msgs:
        try:
            s = line.find("{")
            e = line.rfind("}")
            data = json.loads(line[s:e+1])
            def walk(o, path=""):
                if isinstance(o, dict):
                    for k, v in o.items():
                        kl = k.lower()
                        if any(x in kl for x in ("vip", "virtual", "ip_pool", "ippool", "pool")):
                            keys.add((path + "." + k, type(v).__name__, str(v)[:80]))
                        walk(v, path + "." + k)
                elif isinstance(o, list):
                    for i, v in enumerate(o):
                        walk(v, path + f"[{i}]")
            walk(data)
        except Exception:
            pass
    print("\n=== 含 vip/virtual/pool 的字段 ===")
    for k in sorted(keys):
        print(k)

if __name__ == "__main__":
    main()
