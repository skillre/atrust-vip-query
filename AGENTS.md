# AGENTS.md

> 面向 AI 编码助手的项目指南。人类协作者也可阅读。
> 本文件是总入口，各子目录另有更详细的 `CLAUDE.md`，改动对应模块前请一并阅读。

## 项目概览

aTrust 用户虚拟IP查询系统 —— 轻量级 MVP，用于查询深信服 aTrust 零信任系统分配给用户的虚拟IP地址。

两种运行模式（`config.yaml` 中 `mode` 字段，默认 `import`）：

- **导入模式**：上传导出的日志文件（CSV/Excel）离线查询
- **实时模式**：直连 aTrust 设备（Syslog 接收 / OpenAPI 轮询）

设计目标是让运维人员快速查用户虚拟IP，用于问题排查和安全审计。aTrust 设备可能无法从云端直连，因此必须支持离线文件导入。

## 技术栈

| 层 | 技术 |
| --- | --- |
| 后端 | Python 3.10+ / FastAPI / uvicorn |
| 数据 | SQLite（标准库 sqlite3，无 ORM）+ Pydantic 2 模型 |
| 采集 | Syslog（标准端口 514，协议 UDP/TCP 由前端配置）/ requests（aTrust OpenAPI）/ pandas+openpyxl（文件导入） |
| 前端 | React 19 / Vite / react-router-dom |
| 日志 | loguru |

## 目录结构

```
app.py               # 入口，编排所有服务（FastAPI + Syslog）
src/
├── collector/       # 数据采集：syslog_collector / api_collector / file_importer
├── storage/         # 持久化：database.py (CRUD) + models.py (Pydantic 数据契约)
├── api/             # REST 接口：routes.py（查询/导入/导出）+ dashboard_routes.py（仪表盘/系统配置）
├── config.py        # 配置加载（config.yaml）
└── utils/
frontend/src/        # React SPA（查询/反查/历史/导入/导出等面板）
scripts/             # 运维脚本（clean_db.py 等）
config.yaml          # 运行配置（参考 config.yaml.example）
static/              # React 构建产物部署目录（由 dist/ 拷入，见部署说明；已 gitignore）
```

数据流：`外部数据源 → collector → storage → api → frontend`

- API 路由在 `app.py` 统一挂载到 `/api/v1` 前缀（`routes.py` 与 `dashboard_routes.py` 两个 router）。
- 后端提供静态文件服务：若存在 `static/index.html` 则托管前端 SPA，否则仅暴露 `/docs`。

## 常用命令

| 命令 | 作用 |
| --- | --- |
| `pip install -r requirements.txt` | 安装 Python 依赖 |
| `python app.py` | 启动 FastAPI + Syslog 服务（端口 8000） |
| `cd frontend && npm install` | 安装前端依赖 |
| `cd frontend && npm run dev` | 启动 React 开发服务器（端口 3000，`/api` 代理到 8000） |
| `cd frontend && npm run build` | 构建生产产物到 `frontend/dist/`（部署时需拷贝到根目录 `static/` 供后端托管） |
| `cd frontend && npm run lint` | oxlint 前端检查 |
| `python scripts/clean_db.py` | 清理数据库脏数据（引号/tab 残留） |

## 开发约束（重要，详见 DEV_CONSTRAINTS.md）

- **本地只写代码，不运行服务、不装依赖**。所有运行/调试/测试在免费云环境（Replit 开发、Fly.io 部署）中进行。
- 修改数据库 schema 需手动 `ALTER`：项目**无迁移系统**。
- Schema、模型、API、UI 需保持数据契约一致（models.py 是唯一契约来源）。

- **storage 是数据契约层**：所有模块依赖 `models.py` 的 Pydantic 模型与 `database.py` 的接口。
- **connection-per-operation**：每个 DB 方法独立开关连接，`try/except/finally`，失败返回 `None` 或空响应对象，**不向调用方抛异常**。
- **API 薄控制器**：路由只做校验/响应包装，业务委托给 storage 和 collector，统一返回 `ApiResponse`（code/message/data 信封）。查询/导入/导出类端点放 `routes.py`，仪表盘与系统配置类端点放 `dashboard_routes.py`。
- **前端不直接访问数据库**：只通过 `fetch()` 调 `/api/v1`。
- 无 ORM、无连接池、无迁移系统 —— 保持轻量，改动时不要引入这些。

## 新增端到端功能的顺序

1. **Storage**：`database.py` 加表/查询方法，`models.py` 定义模型（详见 `src/storage/CLAUDE.md`）
2. **API**：`routes.py` 加路由，返回 `ApiResponse`（详见 `src/api/CLAUDE.md`）
3. **Collector**（若涉及新数据源）：新建采集器，统一转换为 `UserInfo`/`VipRecord`（详见 `src/collector/CLAUDE.md`）
4. **React UI**：新增面板（详见 `frontend/src/CLAUDE.md`）

> 注：各子目录 `CLAUDE.md` 中的部分数字（端点数量、模型数量、Syslog 端口/协议）可能滞后于代码，以 `src/` 下实际代码和 `config.yaml` 为准。

## 分层文档索引

| 路径 | 内容 |
| --- | --- |
| `src/storage/CLAUDE.md` | 数据模型、DB 模式、upsert/分页写法 |
| `src/api/CLAUDE.md` | 路由与统一响应信封 |
| `src/collector/CLAUDE.md` | 三种采集通道的实现约定 |
| `frontend/src/CLAUDE.md` | React 组件结构与样式约定 |
| `DEV_CONSTRAINTS.md` | 本地/云环境分工、部署方案对比 |
| `DEPLOYMENT.md` | 详细部署步骤（Replit / Fly.io） |
| `README.md` | 面向使用者的总说明 |
