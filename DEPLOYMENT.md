# 部署指南

> 本文档提供详细的部署步骤，适用于没有 Replit 或 Fly.io 使用经验的用户。

---

## 目录

1. [前置准备](#前置准备)
2. [方案一：Replit 部署（推荐新手）](#方案一replit-部署推荐新手)
3. [方案二：Fly.io 部署（推荐生产）](#方案二flyio-部署推荐生产)
4. [常见问题](#常见问题)

---

## 前置准备

### 必需账号

| 平台 | 用途 | 注册地址 |
| ------ | ------ | ---------- |
| GitHub | 代码托管 | <https://github.com> |
| Replit | 在线开发运行 | <https://replit.com> |
| Fly.io | 正式部署（可选） | <https://fly.io> |

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

## 方案一：Replit 部署（推荐新手）

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
   Streamlit 服务地址: http://0.0.0.0:8501
   ```

### 步骤 6：访问服务

Replit 会自动分配一个公网地址，格式如：

- `https://你的用户名-atrust-vip-query.repl.co`

点击 **Webview** 面板即可看到 Streamlit 界面。

### Replit 使用技巧

| 操作 | 说明 |
| ------ | ------ |
| **Run** | 运行项目 |
| **Stop** | 停止运行 |
| **Shell** | 打开终端，可以执行命令 |
| **Secrets** | 设置环境变量（敏感信息） |

---

## 方案二：Fly.io 部署（推荐生产）

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

**Replit：**

- 直接在 Replit 编辑器中修改
- 或推送到 GitHub 后在 Replit 中 Pull

**Fly.io：**

```bash
# 修改代码后
git add .
git commit -m "更新说明"
git push

# 重新部署
fly deploy
```

### Q4: Syslog 端口 514 需要特殊配置吗？

- **Replit**：支持，无需额外配置
- **Fly.io**：已在 `fly.toml` 中配置，无需额外操作

### Q5: 数据库文件在哪里？

- **Replit**：在 Replit 的文件系统中，路径为 `./data/vip_data.db`
- **Fly.io**：在数据卷中，路径为 `/app/data/vip_data.db`

### Q6: 如何查看日志？

**Replit：**

- 在 Console 面板直接查看

**Fly.io：**

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
