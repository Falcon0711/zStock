"""
通用容灾执行器模块

提供统一的多数据源容灾切换机制，消除重复的容灾逻辑
"""

import time
from typing import Callable, List, Optional, Any, TypeVar
from functools import wraps

from utils.logger import get_logger
from services.data_config import MAX_RETRIES, RETRY_DELAY, RETRY_BACKOFF

logger = get_logger(__name__)

T = TypeVar('T')


class FallbackExecutor:
    """
    通用容灾执行器
    
    依次尝试多个数据源，直到成功或全部失败
    
    用法:
        executor = FallbackExecutor([
            lambda: sina.get_realtime(code),
            lambda: tencent.get_realtime(code),
            lambda: eastmoney.get_realtime(code),
        ], names=['新浪', '腾讯', '东方财富'])
        result = executor.execute()
    """
    
    def __init__(
        self, 
        providers: List[Callable[[], T]], 
        names: Optional[List[str]] = None,
        context: str = ""
    ):
        """
        初始化容灾执行器
        
        Args:
            providers: 数据提供者函数列表
            names: 数据源名称列表（用于日志）
            context: 上下文说明（如股票代码）
        """
        self.providers = providers
        self.names = names or [f"Provider_{i+1}" for i in range(len(providers))]
        self.context = context
    
    def execute(self) -> Optional[T]:
        """
        依次执行每个provider，返回第一个成功的结果
        
        Returns:
            成功的结果，或 None（全部失败）
        """
        for i, provider in enumerate(self.providers):
            name = self.names[i] if i < len(self.names) else f"Provider_{i+1}"
            try:
                result = provider()
                if result is not None:
                    if i > 0:
                        logger.info(f"[{name}] 获取成功 (容灾切换) {self.context}")
                    return result
                else:
                    logger.debug(f"[{name}] 返回空数据 {self.context}")
            except Exception as e:
                logger.warning(f"[{name}] 获取失败 {self.context}: {e}")
                if i < len(self.providers) - 1:
                    next_name = self.names[i+1] if i+1 < len(self.names) else f"Provider_{i+2}"
                    logger.info(f"🔄 切换到 {next_name} {self.context}")
        
        logger.error(f"❌ 所有数据源都失败 {self.context}")
        return None


def with_retry(
    max_retries: int = MAX_RETRIES,
    delay: float = RETRY_DELAY,
    backoff: float = RETRY_BACKOFF,
    exceptions: tuple = (Exception,)
):
    """
    重试装饰器
    
    Args:
        max_retries: 最大重试次数
        delay: 初始延迟秒数
        backoff: 延迟倍数（指数退避）
        exceptions: 需要重试的异常类型
    
    用法:
        @with_retry(max_retries=3, delay=2.0)
        def fetch_data():
            ...
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            current_delay = delay
            last_exception = None
            
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt < max_retries:
                        logger.warning(f"{func.__name__} 失败 (尝试 {attempt + 1}/{max_retries + 1}): {e}")
                        logger.info(f"等待 {current_delay:.1f} 秒后重试...")
                        time.sleep(current_delay)
                        current_delay *= backoff
                    else:
                        logger.error(f"{func.__name__} 最终失败: {e}")
            
            return None
        return wrapper
    return decorator


def rate_limited(delay: float = 1.0):
    """
    限流装饰器
    
    确保函数调用间隔不小于指定时间，保护IP
    
    Args:
        delay: 调用间隔秒数
    """
    last_call = [0.0]  # 使用列表以便在闭包中修改
    
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            elapsed = time.time() - last_call[0]
            if elapsed < delay:
                time.sleep(delay - elapsed)
            result = func(*args, **kwargs)
            last_call[0] = time.time()
            return result
        return wrapper
    return decorator
