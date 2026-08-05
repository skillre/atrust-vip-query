# 部署指南

> 本文档提供详细的部署步骤。**当前推荐方案：腾讯云主机 Docker 部署**（所有功能测试均以 docker / docker-compose 方式在云主机上线验证）。Replit / Fly.io 方案保留供参考。

---

## 目录

1. [前置准备](#前置准备)
2. [方案一：腾讯云主机 Docker 部署（当前推荐）](#方案一腾讯云主机-docker-部署当前推荐)
3. [方案二：Replit 部署（历史参考）](#方案二replit-部署历史参考)
4. [方案三：Fly.io 部署（历史参考）](#方案三flyio-部署历史参考)
5. [方案四：导入模式使用说明](#方案四导入模式使用说明)
6. [常见问题](#常见问题)

---

## 前置准备

### 必需账号

| 平台 | 用途 | 注册地址 |
| ------ | ------ | ---------- |
| GitHub | 代码托管（必选） | <https://github.com> |
| 腾讯云 | 免费试用云主机，docker 部署测试（必选） | <https://cloud.tencent.com> |
| Replit | 在线开发运行（历史方案，可选） | <https://replit.com> |
| Fly.io | 容器化部署（历史方案，可选） | <https://fly.io> |

### Git 基础操作

如果你不熟悉 Git，先学习这几个命令：

```bash
# 初始化仓库
git init

# 添加文件到暂存区
git add .

# 提交更改
git commit -m "描述信息"

# 推送到 GitHub
git push origin main
```

---

## 方案一：腾讯云主机 Docker 部署（当前推荐）

> 当前所有功能测试都在腾讯云免费试用云主机上以 docker / docker-compose 方式完成，本方案也是唯一生产部署方式。

### 步骤 1：准备腾讯云主机

> **当前测试/部署主机**：`ubuntu@49.235.170.245`（腾讯云免费试用轻量服务器，Ubuntu）
> 本地 SSH：`ssh ubuntu@49.235.170.245`（本机 id_ed25519 已授权）

1. 打开 <https://cloud.tencent.com> 注册/登录，领取**免费试用云主机**（轻量应用服务器或 CVM，系统建议 Ubuntu 22.04 / Debian 12）
2. 在**防火墙/安全组**中放行以下端口：
   - `8000`（Web 访问）
   - `514` UDP + TCP（Syslog 接收）

### 步骤 2：安装 Docker 与 Compose 插件

SSH 登录云主机后执行：

```bash
# 使用国内镜像加速安装 Docker
curl -fsSL https://get.docker.com | bash -s docker --mirror Aliyun

# 安装 compose 插件（Docker 24+ 自带 docker compose 子命令，若缺失则补装）
sudo apt-get update && sudo apt-get install -y docker-compose-plugin

# 验证
sudo docker --version && sudo docker compose version
```

> 若希望免 sudo 执行 docker 命令，可执行：`sudo usermod -aG docker $USER` 后重新登录。

### 步骤 3：获取代码

```bash
# 从 GitHub 拉取（推荐，保持与仓库同步）
git clone https://github.com/skillre/atrust-vip-query.git
cd atrust-vip-query

# 已有目录时更新
# git pull origin main
```

### 步骤 4：准备配置文件

```bash
# 复制配置模板并按需修改（aTrust API 密钥、运行模式等）
cp config.yaml.example config.yaml
vi config.yaml
```

> 容器启动时 `docker-entrypoint.sh` 也会自动补齐缺失的 config.yaml。

### 步骤 5：一键启动

```bash
docker compose up -d --build
```

首次构建需要几分钟（已配置国内 PyPI 镜像）。启动后检查状态：

```bash
# 查看容器状态
docker compose ps

# 查看日志
docker compose logs -f
```

### 步骤 6：访问与验证

- Web 界面：`http://<云主机IP>:8000`
- API 文档：`http://<云主机IP>:8000/docs`
- 健康检查：`http://<云主机IP>:8000/api/v1/system/health`

### 步骤 7：日常更新（拉取新版本）

```bash
git pull origin main
docker compose up -d --build
```

### 常用命令速查

| 命令 | 说明 |
| ------ | ------ |
| `docker compose up -d --build` | 构建并启动 |
| `docker compose ps` | 查看状态 |
| `docker compose logs -f` | 查看日志 |
| `docker compose down` | 停止（数据保留在命名卷中） |
| `docker compose down -v` | 停止并删除数据卷（慎用） |
| `docker exec -it atrust-vip-query bash` | 进入容器 |

---

## 方案二：Replit 部署（历史参考）

Replit 是一个在线 IDE，可以直接在浏览器中写代码、运行、调试，非常适合开发阶段。

### 步骤 1：注册 Replit 账号

1. 打开 <https://replit.com>
2. 点击 **Sign Up**
3. 选择 **Continue with GitHub**（用 GitHub 账号登录）
4. 授权 Replit 访问你的 GitHub

### 步骤 2：将代码推送到 GitHub

在你的电脑上打开终端（Terminal），进入项目目录：

```bash
cd /Users/skillre/claude/系统开发/虚拟IP查询

# 初始化 Git 仓库
git init

# 添加所有文件
git add .

# 提交
git commit -m "初始版本：aTrust 用户虚拟IP查询系统"

# 在 GitHub 上创建新仓库（命名为 atrust-vip-query），然后：
git remote add origin https://github.com/你的用户名/atrust-vip-query.git
git branch -M main
git push -u origin main
```

### 步骤 3：在 Replit 中导入项目

1. 登录 Replit
2. 点击右上角 **+ Create Repl**
3. 选择 **Import from GitHub**
4. 选择你刚才创建的 `atrust-vip-query` 仓库
5. 点击 **Import**

### 步骤 4：配置 Replit

Replit 会自动检测到 `.replit` 配置文件。如果没有自动识别：

1. 点击左侧的 **Files** 面板
2. 确认 `.replit` 文件存在
3. 点击顶部的 **Run** 按钮

### 步骤 5：运行项目

1. 点击顶部绿色的 **Run** 按钮
2. Replit 会自动安装依赖（首次运行需要 2-3 分钟）
3. 看到以下输出表示成功：

   ```
   FastAPI 服务地址: http://0.0.0.0:8000
   React 前端地址: http://localhost:3000
   ```

### 步骤 6：访问服务

Replit 会自动分配一个公网地址，格式如：

- `https://你的用户名-atrust-vip-query.repl.co`

在浏览器中打开 <http://localhost:3000> 访问 React 前端。

### Replit 使用技巧

| 操作 | 说明 |
| ------ | ------ |
| **Run** | 运行项目 |
| **Stop** | 停止运行 |
| **Shell** | 打开终端，可以执行命令 |
| **Secrets** | 设置环境变量（敏感信息） |

### 步骤 7：同步 GitHub 最新代码

当本地代码更新并推送到 GitHub 后，在 Replit 中同步有两种方式：

#### 方式一：Shell 命令同步（推荐）

1. 点击左侧 **Shell** 面板
2. 执行以下命令：

```bash
git pull origin main
```

1. 首次同步后如果依赖有变更，重新安装：

```bash
pip install -r requirements.txt
```

1. 点击 **Run** 重启服务

#### 方式二：Version Control 面板同步

1. 点击左侧 **Version Control** 面板（Git 图标）
2. 面板会显示本地与远程的差异
3. 点击 **Pull** 按钮拉取最新代码
4. 确认合并（如有冲突需手动解决）
5. 点击 **Run** 重启服务

> 💡 **提示：** 方式一适合熟悉命令行的用户，方式二适合 GUI 操作习惯的用户。两种方式效果相同。

---

## 方案三：Fly.io 部署（历史参考）

Fly.io 支持容器化部署，更灵活，适合正式环境。

### 步骤 1：安装 flyctl 命令行工具

**macOS：**

```bash
curl -L https://fly.io/install.sh | sh
```

**Windows（PowerShell）：**

```powershell
iwr https://fly.io/install.ps1 -useb | iex
```

安装完成后，重启终端。

### 步骤 2：注册并登录 Fly.io

```bash
# 注册账号（会打开浏览器）
fly auth signup

# 或者用已有账号登录
fly auth login
```

### 步骤 3：初始化项目

```bash
cd /Users/skillre/claude/系统开发/虚拟IP查询

# 初始化 Fly.io 配置
fly launch

# 按提示操作：
# - App name: atrust-vip-query
# - Region: 选择离你最近的（推荐 hkg 香港 或 nrt 东京）
# - 是否覆盖 existing Dockerfile: Yes
```

### 步骤 4：创建数据卷（持久化数据库）

```bash
# 创建数据卷
fly volumes create data_volume --region hkg --size 1

# 查看数据卷
fly volumes list
```

### 步骤 5：设置环境变量

```bash
# 设置敏感配置（不要写在代码里）
fly secrets set atrust_api_id="你的API_ID"
fly secrets set atrust_api_key="你的API_KEY"
```

### 步骤 6：部署

```bash
# 部署应用
fly deploy

# 首次部署需要 5-10 分钟
```

### 步骤 7：检查状态

```bash
# 查看应用状态
fly status

# 查看日志
fly logs
```

### 步骤 8：访问服务

```bash
# 打开浏览器访问
fly open
```

Fly.io 会自动分配一个域名，格式如：

- `https://atrust-vip-query.fly.dev`

### 常用 Fly.io 命令

| 命令 | 说明 |
| ------ | ------ |
| `fly deploy` | 部署应用 |
| `fly status` | 查看状态 |
| `fly logs` | 查看日志 |
| `fly ssh console` | SSH 进入容器 |
| `fly volumes list` | 查看数据卷 |
| `fly apps list` | 查看所有应用 |
| `fly apps destroy <name>` | 删除应用 |

---

## 方案四：导入模式使用说明

如果你的 aTrust 设备无法通过网络访问，可以使用**导入模式**：

### 工作原理

```
aTrust 控制台 ──导出日志──> CSV/Excel 文件 ──上传到 Replit──> 系统解析并存储
```

### 步骤 1：部署系统

按照「方案二：Replit 部署」的步骤完成部署。

### 步骤 2：从 aTrust 导出日志

1. 登录 aTrust 管理控制台
2. 进入 **日志 → 访问日志** 页面
3. 设置时间范围和筛选条件
4. 点击 **导出**，选择 CSV 或 Excel 格式
5. 保存导出的文件

### 步骤 3：上传导入

1. 打开浏览器访问 React 前端
2. 点击 **📥 导入数据** 标签页
3. 点击 **Browse files** 选择导出的日志文件
4. 点击 **👁️ 预览数据** 检查数据格式
5. 确认无误后点击 **📥 开始导入**

### 步骤 4：使用查询功能

导入完成后，即可使用：

- **📋 查询虚拟IP**：输入用户名查询
- **🔄 反查用户**：输入虚拟IP反查用户
- **📜 历史记录**：查看历史分配记录

### 导入模式注意事项

| 项目 | 说明 |
| ------ | ------ |
| 数据时效性 | 导入的是历史快照，非实时数据 |
| 更新频率 | 建议定期导出最新日志并重新导入 |
| 文件大小 | 单次导入建议不超过 10MB |
| 编码格式 | 支持 UTF-8 和 GBK 编码 |
| 重复导入 | 重复数据会自动更新，不会产生重复记录 |

---

## 常见问题

### Q1: Replit 免费版有什么限制？

- 内存：500MB
- 存储：1GB
- 运行时间：有空闲限制（长时间无操作会自动停止）
- 适合开发测试，不适合生产环境

### Q2: Fly.io 免费额度是多少？

- 3 个共享型虚拟机
- 160GB 出站流量/月
- 3GB 持久化存储
- 足够运行本项目

### Q3: 如何更新代码？

**腾讯云主机（当前推荐）：**

```bash
git pull origin main
docker compose up -d --build
```

**Replit（历史）：**

- 直接在 Replit 编辑器中修改
- 或推送到 GitHub 后在 Replit 中 Pull

**Fly.io（历史）：**

```bash
# 修改代码后
git add .
git commit -m "更新说明"
git push

# 重新部署
fly deploy
```

### Q4: Syslog 端口 514 需要特殊配置吗？

- **腾讯云主机（当前推荐）**：需要在防火墙/安全组中放行 `514` UDP 与 TCP 端口（docker-compose.yml 已映射 514 和 8000）
- **Replit（历史）**：支持，无需额外配置
- **Fly.io（历史）**：已在 `fly.toml` 中配置，无需额外操作

### Q5: 数据库文件在哪里？

- **腾讯云主机（当前推荐）**：docker 命名卷 `vip-data` 中，容器内路径 `/app/data/vip_data.db`（`docker compose down` 不会删除，`docker compose down -v` 才会）
- **Replit（历史）**：在 Replit 的文件系统中，路径为 `./data/vip_data.db`
- **Fly.io（历史）**：在数据卷中，路径为 `/app/data/vip_data.db`

### Q6: 如何查看日志？

**腾讯云主机（当前推荐）：**

```bash
docker compose logs -f
```

**Replit（历史）：**

- 在 Console 面板直接查看

**Fly.io（历史）：**

```bash
fly logs
```

---

## 下一步

部署成功后，你需要：

1. **配置 aTrust 设备**：将 Syslog 转发到你的云服务器地址
2. **配置 API 凭证**：在配置文件中填入 aTrust API 的 ID 和 Key
3. **测试功能**：通过 Web 界面或 API 文档测试各项功能

如有问题，请查看项目 README 或提交 GitHub Issue。
