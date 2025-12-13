"""
数据获取统一配置模块

集中管理所有数据获取相关的配置参数，消除魔法数字
"""

# ==================== 网络请求配置 ====================
REQUEST_TIMEOUT = 15        # 请求超时(秒)
MAX_RETRIES = 3             # 最大重试次数
RETRY_DELAY = 2.0           # 初始重试延迟(秒)
RETRY_BACKOFF = 2.0         # 重试延迟倍数(指数退避)

# ==================== 缓存配置 ====================
MEMORY_CACHE_TTL = 300      # 内存缓存时长(秒) - 5分钟
REALTIME_CACHE_TTL = 3      # 实时行情缓存(秒)
MAX_CACHE_SIZE = 100        # 最大缓存条目数
ANALYSIS_CACHE_TTL = 300    # 分析结果缓存(秒) - 5分钟
ANALYSIS_CACHE_SIZE = 50    # 分析结果缓存条目数

# ==================== 数据完整性配置 ====================
DATA_COMPLETENESS_RATIO = 0.8  # 数据完整性阈值(80%)
MIN_DATA_DAYS = 60             # 最少数据天数

# ==================== 数据源配置 ====================

# 实时行情数据源优先级（按顺序尝试）
REALTIME_PROVIDERS = ['eastmoney', 'tencent', 'sina']

# 分时数据源优先级
INTRADAY_PROVIDERS = ['eastmoney', 'tencent', 'sina']

# K线数据源优先级 (东财支持最多3000天)
KLINE_PROVIDERS = ['tencent', 'eastmoney', 'akshare']

# 市场指数数据源优先级
INDEX_PROVIDERS = ['eastmoney', 'sina', 'tencent']

# 美股指数: 新浪(首选，支持 int_dji/int_nasdaq)
US_INDEX_PROVIDERS = ['sina']

# 网络请求超时时间（秒）
REQUEST_TIMEOUT = 15

# 请求重试次数
MAX_RETRIES = 3

# 请求间隔（秒）
REQUEST_DELAY = 0.5

# ==================== 后台任务配置 ====================

# 后台工作线程数
BACKGROUND_WORKERS = 2

# 单次补全批次大小（天数）
BACKFILL_BATCH_SIZE = 640

# 最大补全迭代次数
BACKFILL_MAX_ITERATIONS = 10

# ==================== 接口限流配置 ====================
API_RATE_LIMIT_DELAY = 1.0  # 接口调用间隔(秒)，保护IP
BATCH_SIZE = 50             # 批量更新时每批数量
BATCH_DELAY = 2.0           # 批次之间延迟(秒)

# ==================== HTTP Headers ====================
DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
}

SINA_HEADERS = {
    **DEFAULT_HEADERS,
    "Referer": "https://finance.sina.com.cn/",
}

TENCENT_HEADERS = {
    **DEFAULT_HEADERS,
    "Referer": "https://gu.qq.com/",
}

EASTMONEY_HEADERS = {
    **DEFAULT_HEADERS,
    "Referer": "https://quote.eastmoney.com/",
}
