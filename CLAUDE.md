# aTrust 用户虚拟IP查询系统

轻量级 MVP，用于查询深信服 aTrust 零信任系统分配给用户的虚拟IP地址。支持两种运行模式：**导入模式**（上传日志文件）和**实时模式**（直连 aTrust 设备）。

## Architecture

```
app.py (入口，编排所有服务)
  ├── src/collector/  → 数据采集（Syslog / API / 文件导入）
  ├── src/storage/    → 持久化（SQLite + Pydantic 模型）
  ├── src/api/        → REST 接口（FastAPI）
  ├── src/web/        → Streamlit GUI（独立进程，端口 8501）
  └── frontend/       → React SPA（Vite 构建，端口 3000）

数据流：外部数据源 → collector → storage → api → web/frontend
```

## Commands

| Command | What it does |
| --- | --- |
| `python app.py` | 启动 FastAPI + Syslog 服务（端口 8000） |
| `streamlit run src/web/app.py` | 启动 Streamlit GUI（端口 8501） |
| `cd frontend && npm run dev` | 启动 React 开发服务器（端口 3000） |
| `cd frontend && npm run build` | 构建 React 生产产物到 static/ |
| `pip install -r requirements.txt` | 安装 Python 依赖 |
| `python scripts/clean_db.py` | 清理数据库中的脏数据（引号/tab残留） |

## Business Context

运维人员需要快速查询用户的虚拟IP用于问题排查和安全审计。aTrust 设备可能无法从云端直接访问，因此系统支持通过上传导出的日志文件来离线使用。

<important if="you are adding a new end-to-end feature">
## Adding a New Feature (End-to-End)
1. **Storage**: 在 `database.py` 添加表和查询方法，在 `models.py` 定义模型（详见 src/storage/CLAUDE.md）
2. **API**: 在 `routes.py` 添加路由，返回 `ApiResponse`（详见 src/api/CLAUDE.md）
3. **Collector** (if data source): 创建新的采集器（详见 src/collector/CLAUDE.md）
4. **Streamlit UI**: 添加新标签页（详见 src/web/CLAUDE.md）
5. **React UI**: 添加新面板（详见 frontend/src/CLAUDE.md）
</important>
