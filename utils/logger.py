"""
日志系统 - 统一日志管理
使用 Python logging 模块，支持文件 + 控制台输出
"""

import logging
import os
import sys
from datetime import datetime
from pathlib import Path

# 导入配置
try:
    from settings import LOG_LEVEL, LOG_DIR, LOG_FORMAT, LOG_DATE_FORMAT
except ImportError:
    LOG_LEVEL = "INFO"
    LOG_DIR = Path(__file__).parent.parent / "logs"
    LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
    LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

# 确保日志目录存在
os.makedirs(LOG_DIR, exist_ok=True)

# 日志文件路径（按日期）
LOG_FILE = LOG_DIR / f"app_{datetime.now().strftime('%Y%m%d')}.log"

# 创建根日志器
_root_logger = logging.getLogger("Stock")
_root_logger.setLevel(getattr(logging, LOG_LEVEL, logging.INFO))

# 避免重复添加处理器
if not _root_logger.handlers:
    # 文件处理器
    file_handler = logging.FileHandler(LOG_FILE, encoding='utf-8')
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(logging.Formatter(LOG_FORMAT, LOG_DATE_FORMAT))
    _root_logger.addHandler(file_handler)
    
    # 控制台处理器（只显示 INFO 及以上）
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(logging.Formatter(LOG_FORMAT, LOG_DATE_FORMAT))
    _root_logger.addHandler(console_handler)


def get_logger(name: str) -> logging.Logger:
    """
    获取指定模块的日志记录器
    
    Usage:
        from utils.logger import get_logger
        logger = get_logger(__name__)
        logger.info("消息")
        logger.error("错误", exc_info=True)
    """
    return logging.getLogger(f"Stock.{name}")


# 便捷函数
def debug(msg: str): _root_logger.debug(msg)
def info(msg: str): _root_logger.info(msg)
def warning(msg: str): _root_logger.warning(msg)
def error(msg: str, exc_info=False): _root_logger.error(msg, exc_info=exc_info)

