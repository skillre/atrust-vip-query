# aTrust 用户虚拟IP查询系统

轻量级 MVP，用于查询深信服 aTrust 零信任系统分配给用户的虚拟IP地址。支持两种运行模式：**导入模式**（上传日志文件）和**实时模式**（直连 aTrust 设备）。

## Architecture

```
app.py (入口，编排所有服务)
  ├── src/collector/  → 数据采集（Syslog / API / 文件导入）
  ├── src/storage/    → 持久化（SQLite + Pydantic 模型）
  ├── src/api/        → REST 接口（FastAPI）
  └── src/web/        → Web 界面（Streamlit）
```

数据流：`外部数据源 → collector → storage → api/web`

## Commands

| Command | What it does |
| --- | --- |
| `python app.py` | 启动所有服务（FastAPI + Streamlit） |
| `pip install -r requirements.txt` | 安装依赖 |
| `python scripts/clean_db.py` | 清理数据库中的脏数据（引号/tab残留） |

## Business Context

运维人员需要快速查询用户的虚拟IP用于问题排查和安全审计。aTrust 设备可能无法从云端直接访问，因此系统支持通过上传导出的日志文件来离线使用。

<important if="you are adding a new data ingestion source">
- 创建 `src/collector/<name>_collector.py`
- 实现解析器（`@staticmethod` 方法返回 `UserInfo` / `VipRecord`）
- 实现采集器类，遵循 fetch → parse → persist 管线
- 在模块底部添加单例工厂 `_x` + `get_x()`
- 在 `src/api/routes.py` 的 `health_check()` 中注册健康检查
- 详见 src/collector/CLAUDE.md
</important>

<important if="you are adding a new API endpoint">
- 在 `src/api/routes.py` 添加路由函数
- 返回统一 `ApiResponse` 信封（code/message/data）
- 业务错误码用 `2xxx`，输入错误 `4xxx`，服务器错误 `5000`
- 详见 src/api/CLAUDE.md
</important>

<important if="you are adding a new database table or query">
- 在 `src/storage/database.py` 的 `_init_db()` 中添加 `CREATE TABLE IF NOT EXISTS`
- 索引命名：`idx_{table}_{column}`
- 查询方法遵循连接-操作-关闭模式（try/finally）
- 详见 src/storage/CLAUDE.md
</important>
