# 开发约束（持久化）

> ⚠️ 本文件记录了项目的开发约束，切换会话时请务必阅读此文件。

## 核心约束

### 1. 本地环境限制

- **本地只写代码**，不运行任何服务
- **不安装任何依赖**（不执行 `pip install`）
- 本地目录仅作为代码编辑工作区

### 2. 运行环境

- 所有代码运行、调试、测试都在**腾讯云免费试用云主机**上进行
- 功能测试统一使用 **docker / docker-compose 方式先上线验证**（构建镜像 → compose 启动 → 功能验证 → 按需更新）
- **不再使用 Replit、Fly.io 等互联网平台进行测试**
- 云主机信息见下方"云环境方案"章节

### 3. 项目技术栈

- Python 3.10+
- FastAPI (后端 API)
- React (Web UI)
- SQLite (数据库)
- Syslog UDP 514 (日志接收)

### 4. 部署要求（docker 优先）

- **项目最终都必须能通过 docker / docker-compose 部署**，这是硬性要求，任何改动不得破坏容器化部署能力
- 变更依赖、端口、路径、环境变量、启动流程、config.yaml、数据库 schema 等时，**必须评估并同步更新** `Dockerfile` / `docker-compose.yml` / `docker-entrypoint.sh` / `.dockerignore` / `DEPLOYMENT.md`
- 每次 bug 修复或文件修改完成后，**必须同步 git commit + push 到 GitHub**（origin: skillre/atrust-vip-query）

## 云环境方案（当前：腾讯云 + Docker）

### 当前方案（唯一）

| 项目 | 说明 |
| ------ | ---------- |
| 云主机 | 腾讯云免费试用云主机（轻量应用服务器 / CVM） |
| 部署方式 | docker / docker-compose 一键部署（项目根目录 `docker-compose.yml`） |
| 测试流程 | 本地写代码 → push GitHub → 云主机 `git pull` → `docker compose up -d --build` → 功能验证 |
| UDP 514 | 支持（云主机防火墙/安全组需放行 514 与 8000 端口） |

- **为什么不用 Replit / Fly.io**：测试已迁移到腾讯云免费试用云主机，docker 方式上线更贴近生产环境
- `.replit`、`fly.toml` 等文件保留，仅作为历史参考，**不再使用**

### 历史方案（已弃用，仅供参考）

| 方案 | 免费额度 | 适合场景 | UDP 514 支持 | 备注 |
| ------ | ---------- | ---------- | -------------- | ------ |
| **Replit** | 免费 tier，500MB 内存 | 在线 IDE + 运行 | ✅ | 已弃用 |
| **Fly.io** | Free tier (3 shared VM) | 容器化部署 | ✅ | 已弃用 |
| Render / Google Cloud Run / Railway | - | - | ⚠️ | 已排除 |

### 注意事项

- React 前端通过 `npm run build` 构建后由后端静态托管（Docker 镜像内已包含构建流程）
- Render 免费 tier 不支持 UDP 端口监听（已排除）
- 云主机防火墙/安全组必须放行 `8000`（Web）与 `514`（Syslog UDP/TCP）

## 开发工作流

```
本地（只写代码）          GitHub          腾讯云主机（运行）
┌─────────────┐  push   ┌──────┐  pull   ┌──────────────────────┐
│ 编写代码/文档 │ ─────→ │ 仓库  │ ─────→ │ git pull              │
│ 修改 bug     │        └──────┘        │ docker compose up -d  │
└─────────────┘                         │ 功能测试 / 验证        │
                                        └──────────────────────┘
```

## 已创建的配置文件

| 文件 | 用途 |
| ------ | ------ |
| `Dockerfile` | Docker 镜像构建配置（当前主用） |
| `docker-compose.yml` | 腾讯云主机 docker-compose 一键部署（当前主用） |
| `docker-entrypoint.sh` | 容器启动入口（首次补齐 config.yaml） |
| `.dockerignore` | Docker 构建上下文排除规则 |
| `.replit` | Replit 配置（历史遗留，不再使用） |
| `fly.toml` | Fly.io 应用配置（历史遗留，不再使用） |
| `.gitignore` | Git 忽略规则 |

## 数据库 Schema 变更记录（无迁移系统，需手动执行）

> ⚠️ 本项目**无自动迁移系统**。schema 变更后，对已有的生产库需手动执行 DDL / 回填。
> 新库（首次启动）无需处理，`database.py` 的 `_init_db` 会自动建表。

### 2025 容量优化：新增最新态表 + 启用定时清理

**背景**：`vip_records` 是 append-only 流水表，10w 用户规模下日增百万~千万条，而查询主路径只需“每人最新一条”。改为**双层表**：

- `user_current_vip`（新增）：一人一行的最新态表，查询主路径只查它，容量恒定 = 用户数，永不清理。
- `vip_records`（保留）：降级为有限历史表，供反查/历史/导出；保留窗口 90→**14 天**，由后台线程每 6 小时清理。

**对已有生产库的升级步骤**（在云环境执行）：

```bash
# 1. 拉取新代码后，启动一次应用会自动建 `user_current_vip` 表（_init_db）
#    但存量记录不会自动进新表 —— 需回填：
python scripts/backfill_current_vip.py --db ./data/vip_data.db

# 2. （可选）回填后可手动触发一次旧数据清理，立即释放超过 14 天的历史：
#    （应用启动后也会自动清，此步仅用于立即生效）
sqlite3 ./data/vip_data.db "DELETE FROM vip_records WHERE timestamp < datetime('now','-14 days'); VACUUM;"
```

> 回填脚本幂等，可重复运行；依赖 SQLite 3.25+ 窗口函数。

## 更新记录

- 2025-01: 初始创建，记录开发约束
- 2025-01: 创建 Replit、Fly.io 配置文件
- 2025-01: 添加部署说明要求（用户无平台经验）
- 2025: Docker 统一打包（docker-compose 一键部署 + 持久化数据卷）
- 2025: 数据库容量优化（新增 user_current_vip 最新态表、保留 14 天、启用定时清理、支持模糊/批量查询）
- 2025-08: 测试环境迁移至腾讯云免费试用云主机（docker-compose 上线验证），弃用 Replit / Fly.io；新增 docker 部署文件同步与 GitHub 同步约定
