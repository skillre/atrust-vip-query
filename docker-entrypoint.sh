#!/bin/sh
# ============================================================
# 容器启动入口脚本
# 作用：首次启动时若缺少 config.yaml，则从 config.yaml.example 生成，
#       保证容器开箱即用；已存在（如挂载进来的）则原样使用。
# ============================================================
set -e

CONFIG_FILE="/app/config.yaml"
CONFIG_EXAMPLE="/app/config.yaml.example"

if [ ! -f "$CONFIG_FILE" ]; then
	if [ -f "$CONFIG_EXAMPLE" ]; then
		echo "[entrypoint] 未找到 config.yaml，从 config.yaml.example 生成默认配置"
		cp "$CONFIG_EXAMPLE" "$CONFIG_FILE"
	else
		echo "[entrypoint] 警告：config.yaml 与 config.yaml.example 均不存在，将使用内置默认配置"
	fi
fi

# 确保运行时目录存在（数据卷挂载后可能为空目录）
mkdir -p /app/data /app/logs

echo "[entrypoint] 启动应用..."
exec "$@"
