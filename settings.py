"""
项目配置管理
集中管理所有配置项，支持环境变量覆盖
"""

import os
from pathlib import Path


# ==================== 路径配置 ====================
PROJECT_ROOT = Path(__file__).parent
DATA_DIR = PROJECT_ROOT / "data"
LOG_DIR = PROJECT_ROOT / "logs"


# ==================== 缓存配置 ====================
# 内存缓存TTL（秒）
MEMORY_CACHE_TTL = int(os.getenv("MEMORY_CACHE_TTL", 300))  # 默认5分钟

# 内存缓存最大条目数
MAX_CACHE_SIZE = int(os.getenv("MAX_CACHE_SIZE", 100))

# 股票列表缓存时间（秒）
STOCK_LIST_CACHE_TTL = int(os.getenv("STOCK_LIST_CACHE_TTL", 86400))  # 默认24小时


# ==================== 数据库配置 ====================
SQLITE_DB_PATH = os.getenv("SQLITE_DB_PATH", str(DATA_DIR / "stock_data.db"))


# ==================== 日志配置 ====================
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FILE = os.getenv("LOG_FILE", str(LOG_DIR / "app.log"))
LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


# ==================== 网络配置 ====================
# API 请求超时（秒）
REQUEST_TIMEOUT = int(os.getenv("REQUEST_TIMEOUT", 30))

# 请求重试次数
MAX_RETRIES = int(os.getenv("MAX_RETRIES", 3))

# 请求间隔（秒），防止被封
REQUEST_DELAY = float(os.getenv("REQUEST_DELAY", 0.3))


# ==================== 交易时间配置 ====================
MORNING_START = "09:30"
MORNING_END = "11:30"
AFTERNOON_START = "13:00"
AFTERNOON_END = "15:00"


# ==================== 数据配置 ====================
# 最少需要的历史数据天数
MIN_DATA_DAYS = 60


# ==================== API 配置 ====================
# 行情缓存时间（秒）
TICKER_CACHE_TTL = int(os.getenv("TICKER_CACHE_TTL", 30))
