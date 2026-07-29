# ============================================================
# aTrust 用户虚拟IP查询系统 - Docker 配置
# 用于 Fly.io 部署
# ============================================================

# 使用 Python 3.11 slim 镜像
FROM python:3.11-slim

# 设置工作目录
WORKDIR /app

# 设置环境变量
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# 复制依赖文件
COPY requirements.txt .

# 安装依赖
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

# 启动命令
CMD ["python", "app.py"]
