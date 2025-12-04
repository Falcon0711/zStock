"""
日志系统 - 统一日志管理
Logging system for the trading platform
"""

import logging
import os
from datetime import datetime

def setup_logger(name: str = "TradingSystem", level: int = logging.INFO) -> logging.Logger:
    """设置并返回日志记录器"""
    # 确保日志目录存在
    log_dir = "logs"
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
    # 创建日志文件名（按日期）
    log_filename = f"{log_dir}/trading_system_{datetime.now().strftime('%Y%m%d')}.log"
    # 创建格式化器
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s'
    )
    # 创建日志记录器
    logger = logging.getLogger(name)
    logger.setLevel(level)
    # 避免重复添加处理器
    if not logger.handlers:
        # 文件处理器
        file_handler = logging.FileHandler(log_filename, encoding='utf-8')
        file_handler.setLevel(level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
        # 控制台处理器
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.WARNING)  # 控制台只显示警告以上级别
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
    return logger

def get_logger(name: str) -> logging.Logger:
    """获取指定名称的日志记录器"""
    return logging.getLogger(f"TradingSystem.{name}")

# 创建默认日志记录器
default_logger = setup_logger()
