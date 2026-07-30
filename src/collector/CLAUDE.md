# Data Ingestion Layer

## Responsibility

从三种外部数据源采集虚拟IP和用户信息，统一转换为 `UserInfo` / `VipRecord` 模型并持久化到 SQLite。

## Dependencies

- **requests**: HTTP 客户端（aTrust API）
- **loguru**: 结构化日志

## Consumers

- **src/api/routes.py**: 在线查询、文件导入、健康检查

## Module Structure

```
src/collector/
├── api_collector.py      # CHANNEL: HTTP API 轮询（aTrust OpenAPI）
├── file_importer.py      # CHANNEL: 批量文件导入（CSV/Excel）
├── syslog_collector.py   # CHANNEL: 实时 UDP Syslog 接收
└── __init__.py
```

## Singleton Factory

```python
_collector: Optional[ApiCollector] = None

def get_api_collector() -> ApiCollector:
    global _collector
    if _collector is None:
        _collector = ApiCollector()
    return _collector
```

## Pipeline Collector（获取 → 解析 → 持久化）

```python
def collect_online_users(self) -> int:
    users = self.client.get_online_users()
    if not users:
        return 0
    count = 0
    for user_data in users:
        try:
            user = UserInfo(user_name=user_data.get("name", ""), ...)
            if not user.user_name:
                continue
            self.db.upsert_user(user)           # 先 upsert 用户
            vip = user_data.get("virtualIp")
            if vip:
                record = VipRecord(user_name=user.user_name,
                    virtual_ip=vip, event_type="online_query",
                    timestamp=datetime.now())
                self.db.insert_vip_record(record)
            count += 1
        except Exception as e:
            logger.error(f"处理失败: {e}")
            continue                            # 单条失败不中断
    return count
```

约定：`event_type` 标记来源（`"online_query"`, `"csv_import"`, `"syslog_access"`）；先 upsert 用户再 insert VIP 记录。

## Static Parser + I/O Receiver 分离

Syslog 模块将纯解析（`SyslogParser`，全 `@staticmethod`）与网络 I/O（`SyslogReceiver`，持有 socket/thread/db）分离。Parser 无状态可独立测试，Receiver 组合 Parser 并负责持久化。

## Background Thread Lifecycle

`SyslogReceiver` 使用 `daemon=True` 守护线程运行 UDP 监听。`start()` 幂等，`stop()` 设置 `_running=False` 后关闭 socket 并 `join(timeout=5)`。`health_check() -> str` 返回 `"listening"` 或 `"stopped"`。

## File Import 编码回退

CSV 导入按顺序尝试 `utf-8 → gbk → gb2312 → utf-8-sig`，全部失败返回错误。Excel 通过 pandas 处理，缺少 openpyxl 时返回提示。

## Architectural Boundaries

- **NO queries back**: 只写入，不读取（除健康检查）
- **NO cross-collector communication**: 三条通道完全独立
- **NO error propagation**: 异常内部消化，返回计数/状态

<important if="you are adding a new data ingestion source">
## Adding a New Collector
1. 创建 `src/collector/<name>_collector.py`
2. 导入 `get_config`, `UserInfo`, `VipRecord`, `get_database`, `logger`
3. 解析器用 `@staticmethod`，返回 `Optional[UserInfo]` / `Optional[VipRecord]`
4. 采集器 `__init__` 调用 `get_config()` 和 `get_database()`
5. 主方法遵循 fetch → transform → persist，每条记录独立 try/except
6. 先 `upsert_user()` 再 `insert_vip_record()`
7. 添加 `health_check() -> str` + 模块底部单例工厂
8. 在 `routes.py` 的 `health_check()` 中注册
</important>
