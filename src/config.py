# ============================================================
# 配置管理模块
# 读取 config.yaml，提供全局配置访问
# ============================================================

import os
from pathlib import Path
from typing import Optional

import yaml
from pydantic import BaseModel
from loguru import logger


# 项目根目录
BASE_DIR = Path(__file__).parent.parent


class AtrustConfig(BaseModel):
    """aTrust 设备配置"""
    host: str = "https://192.168.1.100:4433"
    api_id: str = ""
    api_key: str = ""
    timeout: int = 10


class SyslogConfig(BaseModel):
    """Syslog 接收配置"""
    enabled: bool = True
    host: str = "0.0.0.0"
    port: int = 514
    protocol: str = "udp"


class DatabaseConfig(BaseModel):
    """数据库配置"""
    path: str = "./data/vip_data.db"
    retention_days: int = 90


class WebConfig(BaseModel):
    """Web 界面配置（Streamlit）"""
    host: str = "0.0.0.0"
    port: int = 8501
    title: str = "aTrust 用户虚拟IP查询系统"


class ApiConfig(BaseModel):
    """API 服务配置（FastAPI）"""
    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = False


class LoggingConfig(BaseModel):
    """日志配置"""
    level: str = "INFO"
    file: str = "./logs/app.log"
    max_size: int = 10
    backup_count: int = 5


class AppConfig(BaseModel):
    """应用总配置"""
    atrust: AtrustConfig = AtrustConfig()
    syslog: SyslogConfig = SyslogConfig()
    database: DatabaseConfig = DatabaseConfig()
    web: WebConfig = WebConfig()
    api: ApiConfig = ApiConfig()
    logging: LoggingConfig = LoggingConfig()


# 全局配置实例
_config: Optional[AppConfig] = None


def load_config(config_path: Optional[str] = None) -> AppConfig:
    """
    加载配置文件
    
    Args:
        config_path: 配置文件路径，默认为项目根目录下的 config.yaml
    
    Returns:
        AppConfig 配置对象
    """
    global _config
    
    if config_path is None:
        config_path = str(BASE_DIR / "config.yaml")
    
    config_file = Path(config_path)
    
    if not config_file.exists():
        logger.warning(f"配置文件不存在: {config_path}，使用默认配置")
        _config = AppConfig()
        return _config
    
    try:
        with open(config_file, "r", encoding="utf-8") as f:
            raw_config = yaml.safe_load(f) or {}
        
        _config = AppConfig(**raw_config)
        logger.info(f"配置加载成功: {config_path}")
        return _config
        
    except Exception as e:
        logger.error(f"配置加载失败: {e}")
        logger.info("使用默认配置")
        _config = AppConfig()
        return _config


def get_config() -> AppConfig:
    """
    获取全局配置
    
    Returns:
        AppConfig 配置对象
    """
    global _config
    if _config is None:
        _config = load_config()
    return _config


def ensure_directories() -> None:
    """确保必要的目录存在"""
    config = get_config()
    
    # 数据库目录
    db_dir = Path(config.database.path).parent
    db_dir.mkdir(parents=True, exist_ok=True)
    
    # 日志目录
    log_dir = Path(config.logging.file).parent
    log_dir.mkdir(parents=True, exist_ok=True)
    
    logger.debug("目录检查完成")
