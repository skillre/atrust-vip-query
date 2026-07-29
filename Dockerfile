# ============================================================
# aTrust 用户虚拟IP查询系统 - Docker 配置
# ============================================================

# 使用 Python 3.11 slim 镜像
FROM python:3.11-slim

# 设置工作目录
WORKDIR /app

# 设置环境变量
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# 安装依赖（利用 Docker 缓存层）
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制项目文件
COPY . .

# 创建数据和日志目录
RUN mkdir -p data logs

# 暴露端口
# 514/UDP - Syslog 接收
# 8000 - FastAPI 后端
# 8501 - Streamlit UI
EXPOSE 514/udp
EXPOSE 8000
EXPOSE 8501

# 健康检查
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8000/api/v1/system/health', timeout=3)" || exit 1

# 启动命令
CMD ["python", "app.py"]
