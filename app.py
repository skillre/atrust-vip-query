# ============================================================
# aTrust 用户虚拟IP查询系统 - 主程序入口
# 启动服务：FastAPI + React 前端 + Syslog
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


def create_app():
    """创建 FastAPI 应用（包含静态文件服务）"""
    from fastapi import FastAPI, Request
    from fastapi.middleware.cors import CORSMiddleware
    from fastapi.staticfiles import StaticFiles
    from fastapi.responses import FileResponse, RedirectResponse

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

    # 注册 API 路由
    app.include_router(api_router, prefix="/api/v1")

    # React 构建产物目录
    static_dir = Path(__file__).parent / "static"
    index_file = static_dir / "index.html"

    # 如果 React 构建产物存在，挂载静态文件服务
    if static_dir.exists() and index_file.exists():
        logger.info("检测到 React 前端构建产物，启用静态文件服务")

        # 挂载 assets 目录（JS、CSS 等）
        assets_dir = static_dir / "assets"
        if assets_dir.exists():
            app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="assets")

        # 根路径返回 React index.html
        @app.get("/")
        async def serve_react_root():
            return FileResponse(str(index_file))

        # 所有非 API 路径都返回 React index.html（支持前端路由）
        @app.get("/{full_path:path}")
        async def serve_react(request: Request, full_path: str):
            # API 路径不拦截
            if full_path.startswith("api/"):
                return None

            # 路径穿越防护：校验解析后路径仍在 static_dir 内
            file_path = (static_dir / full_path).resolve()
            if not str(file_path).startswith(str(static_dir.resolve())):
                return FileResponse(str(index_file))

            if file_path.is_file():
                return FileResponse(str(file_path))

            # 其他路径返回 index.html（SPA 路由）
            return FileResponse(str(index_file))

        logger.info(f"React 前端地址: http://{config.api.host}:{config.api.port}")
    else:
        logger.warning("未检测到 React 前端构建产物，请先运行 npm run build")
        logger.info(f"API 文档地址: http://localhost:{config.api.port}/docs")

    return app


def start_fastapi():
    """启动 FastAPI 服务"""
    import uvicorn

    config = get_config()
    app = create_app()

    # 启动 uvicorn
    logger.info(f"FastAPI 服务地址: http://{config.api.host}:{config.api.port}")
    logger.info(f"API 文档地址: http://localhost:{config.api.port}/docs")

    uvicorn.run(
        app,
        host=config.api.host,
        port=config.api.port,
        log_level="info"
    )


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
    logger.info(f"Syslog 端口: {config.syslog.port}")
    logger.info(f"数据库路径: {config.database.path}")
    logger.info(f"批量大小: {config.database.batch_size}")

    # 启动 FastAPI（主进程）
    start_fastapi()


if __name__ == "__main__":
    main()
