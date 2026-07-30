# ============================================================
# aTrust 用户虚拟IP查询系统 - Docker 配置（多阶段构建）
# ============================================================

# ---- 阶段 1：构建 React 前端 ----
FROM node:20-slim AS frontend-builder

WORKDIR /frontend

# 先装依赖（利用缓存层）
COPY frontend/package*.json ./
RUN npm install

# 再拷源码构建，产物在 /frontend/dist
COPY frontend/ ./
RUN npm run build


# ---- 阶段 2：Python 运行时 ----
FROM python:3.11-slim

WORKDIR /app

ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# 安装 Python 依赖（利用缓存层）
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制项目文件
COPY . .

# 从前端构建阶段拷入产物到 static/（app.py 从此目录提供 SPA）
COPY --from=frontend-builder /frontend/dist/ ./static/

# 创建数据和日志目录
RUN mkdir -p data logs

# 暴露端口
# 8000    - FastAPI 后端 + 前端静态服务
# 514     - Syslog 接收（协议由前端/config.yaml 选 UDP 或 TCP，这里两种都放行）
EXPOSE 8000
EXPOSE 514/udp
EXPOSE 514/tcp

# 健康检查
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8000/api/v1/system/health', timeout=3)" || exit 1

# 启动命令
CMD ["python", "app.py"]
