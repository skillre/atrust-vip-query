# ============================================================
# aTrust 用户虚拟IP查询系统 - 主程序入口
# 启动所有服务：FastAPI + Streamlit + Syslog
# ============================================================

import sys
import signal
import threading
from contextlib import asynccontextmanager
from pathlib import Path

from loguru import logger

# 添加项目根目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent))

from src.config import load_config, get_config, ensure_directories
from src.storage.database import get_database
from src.api.routes import router as api_router
from src.collector.syslog_collector import get_syslog_receiver


def setup_logging():
    """配置日志"""
    config = get_config()

    # 移除默认处理器
    logger.remove()

    # 控制台输出
    logger.add(
        sys.stderr,
        level=config.logging.level,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
               "<level>{level: <8}</level> | "
               "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
               "<level>{message}</level>"
    )

    # 文件输出
    logger.add(
        config.logging.file,
        level=config.logging.level,
        rotation=f"{config.logging.max_size} MB",
        retention=config.logging.backup_count,
        encoding="utf-8"
    )

    logger.info("日志配置完成")


@asynccontextmanager
async def lifespan(app):
    """FastAPI 生命周期管理（替代已废弃的 on_event）"""
    # ---- 启动 ----
    logger.info("FastAPI 服务启动中...")

    # 初始化数据库
    get_database()
    logger.info("数据库初始化完成")

    # 检查运行模式
    config = get_config()
    if config.atrust.host and config.atrust.api_id and config.atrust.api_key:
        logger.info("aTrust API 已配置，启用实时查询模式")
        syslog = get_syslog_receiver()
        if syslog.start():
            logger.info("Syslog 接收器已启动")
        else:
            logger.warning("Syslog 接收器未启动")
    else:
        logger.info("aTrust API 未配置，运行在导入模式")
        logger.info("请通过 Web 界面上传日志文件导入数据")

    logger.info("FastAPI 服务启动完成")

    yield  # ---- 运行中 ----

    # ---- 关闭 ----
    logger.info("FastAPI 服务关闭中...")
    syslog = get_syslog_receiver()
    syslog.stop()
    logger.info("FastAPI 服务已关闭")


def start_fastapi():
    """启动 FastAPI 服务"""
    import uvicorn
    from fastapi import FastAPI
    from fastapi.middleware.cors import CORSMiddleware

    config = get_config()

    # 创建 FastAPI 应用（使用 lifespan）
    app = FastAPI(
        title="aTrust 用户虚拟IP查询系统 API",
        description="提供虚拟IP查询、反查、历史记录、数据导出等接口",
        version="2.0.0",
        lifespan=lifespan
    )

    # 添加 CORS 中间件
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # 注册路由
    app.include_router(api_router)

    # 启动 uvicorn
    logger.info(f"FastAPI 服务地址: http://{config.api.host}:{config.api.port}")
    logger.info(f"API 文档地址: http://localhost:{config.api.port}/docs")

    uvicorn.run(
        app,
        host=config.api.host,
        port=config.api.port,
        log_level="info"
    )


def start_streamlit():
    """启动 Streamlit 服务"""
    import subprocess
    import time

    config = get_config()

    # Streamlit 启动命令
    cmd = [
        sys.executable, "-m", "streamlit", "run",
        str(Path(__file__).parent / "src" / "web" / "app.py"),
        "--server.port", str(config.web.port),
        "--server.address", config.web.host,
        "--server.headless", "true",
        "--browser.gatherUsageStats", "false"
    ]

    logger.info(f"Streamlit 服务地址: http://{config.web.host}:{config.web.port}")

    # 在新线程中启动 Streamlit
    def run_streamlit():
        try:
            subprocess.run(cmd, check=True)
        except subprocess.CalledProcessError as e:
            logger.error(f"Streamlit 启动失败: {e}")
        except Exception as e:
            logger.error(f"Streamlit 异常: {e}")

    thread = threading.Thread(target=run_streamlit, daemon=True)
    thread.start()

    return thread


def signal_handler(signum, frame):
    """信号处理函数"""
    logger.info("收到退出信号，正在关闭服务...")

    syslog = get_syslog_receiver()
    syslog.stop()

    sys.exit(0)


def main():
    """主函数"""
    # 注册信号处理
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # 加载配置
    load_config()

    # 确保目录存在
    ensure_directories()

    # 配置日志
    setup_logging()

    logger.info("=" * 60)
    logger.info("aTrust 用户虚拟IP查询系统启动中...")
    logger.info("=" * 60)

    # 打印配置信息
    config = get_config()
    logger.info(f"FastAPI 端口: {config.api.port}")
    logger.info(f"Streamlit 端口: {config.web.port}")
    logger.info(f"Syslog 端口: {config.syslog.port}")
    logger.info(f"数据库路径: {config.database.path}")
    logger.info(f"批量大小: {config.database.batch_size}")

    # 启动 Streamlit（在后台线程）
    streamlit_thread = start_streamlit()

    # 等待一下让 Streamlit 启动
    import time
    time.sleep(2)

    # 启动 FastAPI（主进程）
    start_fastapi()


if __name__ == "__main__":
    main()
