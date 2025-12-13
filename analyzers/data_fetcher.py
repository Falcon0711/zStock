"""
数据获取模块
负责从各种数据源获取股票数据，包含缓存逻辑
"""

import akshare as ak
import pandas as pd
import time
from datetime import datetime, timedelta
from typing import Dict, Tuple, Optional

from utils.logger import get_logger

# 尝试导入配置，失败则使用默认值
try:
    from settings import MEMORY_CACHE_TTL, MAX_CACHE_SIZE, MIN_DATA_DAYS
except ImportError:
    MEMORY_CACHE_TTL = 300
    MAX_CACHE_SIZE = 100
    MIN_DATA_DAYS = 60

logger = get_logger(__name__)

# ==================== 内存缓存 ====================
_stock_data_cache: Dict[str, Tuple[pd.DataFrame, float]] = {}


def clear_expired_cache():
    """清理过期的缓存条目"""
    current_time = time.time()
    expired_keys = [
        key for key, (_, cached_time) in _stock_data_cache.items()
        if current_time - cached_time > MEMORY_CACHE_TTL
    ]
    for key in expired_keys:
        del _stock_data_cache[key]
        logger.debug(f"清理过期缓存: {key}")


def is_trading_time() -> bool:
    """判断当前是否为A股交易时段"""
    now = datetime.now()
    # 周末不交易
    if now.weekday() >= 5:
        return False
    # 交易时间：9:30-11:30, 13:00-15:00
    current_time = now.time()
    morning_start = datetime.strptime("09:30", "%H:%M").time()
    morning_end = datetime.strptime("11:30", "%H:%M").time()
    afternoon_start = datetime.strptime("13:00", "%H:%M").time()
    afternoon_end = datetime.strptime("15:00", "%H:%M").time()
    
    return (morning_start <= current_time <= morning_end or 
            afternoon_start <= current_time <= afternoon_end)


def get_realtime_data(stock_code: str) -> Optional[pd.DataFrame]:
    """获取今日实时数据（交易时段使用）"""
    try:
        df = ak.stock_zh_a_spot_em()
        row = df[df['代码'] == stock_code]
        if row.empty:
            return None
        
        row = row.iloc[0]
        today = datetime.now().strftime('%Y-%m-%d')
        
        return pd.DataFrame([{
            'date': pd.to_datetime(today),
            'open': float(row['今开']),
            'high': float(row['最高']),
            'low': float(row['最低']),
            'close': float(row['最新价']),
            'volume': float(row['成交量'])
        }])
    except Exception as e:
        logger.warning(f"获取实时数据失败: {e}")
        return None


def get_stock_data(stock_code: str, days: int = 90, start_date: str = None) -> pd.DataFrame:
    """
    获取股票数据（带本地缓存 + 实时数据优化 + 自动更新过期数据）
    
    优先级：
    1. 内存缓存（5分钟TTL）
    2. 本地SQLite数据库（历史数据）
    3. AkShare网络接口（兜底）
    
    新增：如果本地数据过期（落后于最近交易日），自动从网络获取最新数据并合并
    
    Args:
        stock_code: 股票代码
        days: 需要的天数
        start_date: 开始日期（可选）
    
    Returns:
        包含 date, open, high, low, close, volume 列的 DataFrame
    """
    cache_key = f"{stock_code}_{days}_{start_date}"
    current_time = time.time()
    
    # ===== 1. 内存缓存检查 =====
    if cache_key in _stock_data_cache:
        data, cached_time = _stock_data_cache[cache_key]
        if current_time - cached_time < MEMORY_CACHE_TTL:
            logger.info(f"内存缓存命中: {stock_code}")
            return data.copy()
        else:
            logger.debug(f"内存缓存过期: {stock_code}")
    
    # ===== 2. 尝试从本地SQLite读取 =====
    try:
        from services.local_data_service import get_local_data_service
        local_service = get_local_data_service()
        
        if local_service.has_data(stock_code, min_days=MIN_DATA_DAYS):
            local_data = local_service.get_stock_data(stock_code, days=days)
            
            if local_data is not None and len(local_data) >= MIN_DATA_DAYS:
                logger.info(f"本地数据命中: {stock_code} ({len(local_data)}天)")
                
                # 🆕 检查本地数据是否过期（与最近交易日比较）
                last_date = local_data['date'].max()
                last_trading_date = _get_last_trading_date()
                
                if last_date.date() < last_trading_date:
                    # 本地数据过期，从网络获取增量更新
                    logger.info(f"本地数据过期: {stock_code} 最新={last_date.date()}, 最近交易日={last_trading_date}")
                    try:
                        # 从本地最新日期后一天开始获取增量数据
                        incremental_start = (last_date + timedelta(days=1)).strftime('%Y%m%d')
                        incremental_data = _fetch_incremental_data(stock_code, incremental_start)
                        
                        if incremental_data is not None and len(incremental_data) > 0:
                            # 合并增量数据
                            local_data = pd.concat([local_data, incremental_data], ignore_index=True)
                            local_data = local_data.drop_duplicates(subset=['date']).sort_values('date').reset_index(drop=True)
                            
                            # 保存增量数据到本地数据库
                            saved_count = local_service.save_stock_data(stock_code, incremental_data)
                            logger.info(f"增量更新成功: {stock_code} 新增 {saved_count} 条记录")
                    except Exception as e:
                        logger.warning(f"增量更新失败: {stock_code} - {e}")
                
                # 交易时段：拼接今日实时数据
                if is_trading_time():
                    today_str = datetime.now().strftime('%Y-%m-%d')
                    last_date_str = local_data['date'].max().strftime('%Y-%m-%d')
                    
                    if last_date_str < today_str:
                        realtime = get_realtime_data(stock_code)
                        if realtime is not None:
                            local_data = pd.concat([local_data, realtime], ignore_index=True)
                            logger.info(f"已拼接实时数据: {stock_code}")
                
                # 限制返回天数
                if days and len(local_data) > days:
                    local_data = local_data.tail(days).reset_index(drop=True)
                
                _stock_data_cache[cache_key] = (local_data.copy(), current_time)
                return local_data
                
    except Exception as e:
        logger.warning(f"本地数据读取失败: {e}")
    
    # ===== 3. 从网络API获取 =====
    logger.info(f"从API获取数据: {stock_code}")
    return _fetch_from_network(stock_code, days, start_date, cache_key, current_time)


def _get_last_trading_date() -> datetime.date:
    """获取最近的交易日期（考虑周末和节假日）"""
    now = datetime.now()
    # 如果是周末，回退到周五
    while now.weekday() >= 5:  # 5=周六, 6=周日
        now -= timedelta(days=1)
    # 如果当天还没收盘（15:30之前），使用前一个交易日
    if now.time() < datetime.strptime("15:30", "%H:%M").time():
        now -= timedelta(days=1)
        while now.weekday() >= 5:
            now -= timedelta(days=1)
    return now.date()


def _fetch_incremental_data(stock_code: str, start_date: str) -> Optional[pd.DataFrame]:
    """获取增量数据（从指定日期到今天）"""
    try:
        end_date = datetime.now().strftime('%Y%m%d')
        data = ak.stock_zh_a_hist(
            symbol=stock_code,
            period="daily",
            start_date=start_date,
            end_date=end_date,
            adjust="qfq"
        )
        
        if data is not None and not data.empty:
            # 清洗数据
            column_mapping = {
                '日期': 'date',
                '开盘': 'open',
                '最高': 'high',
                '最低': 'low',
                '收盘': 'close',
                '成交量': 'volume'
            }
            for old_col, new_col in column_mapping.items():
                if old_col in data.columns:
                    data = data.rename(columns={old_col: new_col})
            
            required_cols = ['date', 'open', 'high', 'low', 'close', 'volume']
            if all(col in data.columns for col in required_cols):
                data = data[required_cols]
                data['date'] = pd.to_datetime(data['date'])
                for col in ['open', 'high', 'low', 'close', 'volume']:
                    data[col] = pd.to_numeric(data[col], errors='coerce')
                return data.dropna()
        
        return None
    except Exception as e:
        logger.warning(f"获取增量数据失败: {stock_code} - {e}")
        return None




def _fetch_from_network(stock_code: str, days: int, start_date: str, 
                        cache_key: str, current_time: float) -> pd.DataFrame:
    """从网络获取股票数据（内部函数）"""
    max_retries = 3
    base_retry_delay = 2
    
    for attempt in range(max_retries):
        try:
            if start_date is None:
                start_date = (datetime.now() - timedelta(days=days + 10)).strftime('%Y%m%d')
            
            if attempt > 0:
                delay = base_retry_delay * (2 ** (attempt - 1))
                logger.debug(f"等待 {delay} 秒后重试...")
                time.sleep(delay)
            
            # 尝试东方财富
            data = None
            try:
                if attempt == 0:
                    time.sleep(0.5)
                
                data = ak.stock_zh_a_hist(
                    symbol=stock_code,
                    period="daily",
                    start_date=start_date,
                    adjust="qfq"
                )
            except Exception as em_error:
                logger.warning(f"东方财富API失败，尝试腾讯数据源...")
                try:
                    # 腾讯数据源
                    if stock_code.startswith('6'):
                        tencent_code = f"sh{stock_code}"
                    else:
                        tencent_code = f"sz{stock_code}"
                    
                    end_date = datetime.now().strftime('%Y%m%d')
                    data = ak.stock_zh_a_daily(
                        symbol=tencent_code,
                        start_date=start_date,
                        end_date=end_date,
                        adjust="qfq"
                    )
                except Exception as tx_error:
                    if attempt < max_retries - 1:
                        continue
                    else:
                        raise Exception(
                            f"网络连接失败，无法获取股票 {stock_code} 的数据。"
                        )
            
            if data is not None and not data.empty:
                data = _clean_data(data, days)
                
                # ===== 自动保存到本地SQLite数据库 =====
                try:
                    from services.local_data_service import get_local_data_service
                    local_service = get_local_data_service()
                    saved_count = local_service.save_stock_data(stock_code, data)
                    if saved_count > 0:
                        logger.info(f"已保存到本地: {stock_code} ({saved_count}条新记录)")
                except Exception as save_error:
                    logger.warning(f"保存到本地失败: {save_error}")
                
                # 更新内存缓存
                if len(_stock_data_cache) >= MAX_CACHE_SIZE:
                    clear_expired_cache()
                    if len(_stock_data_cache) >= MAX_CACHE_SIZE:
                        oldest_key = min(_stock_data_cache.keys(), 
                                       key=lambda k: _stock_data_cache[k][1])
                        del _stock_data_cache[oldest_key]
                
                _stock_data_cache[cache_key] = (data.copy(), current_time)
                logger.info(f"已缓存: {stock_code} ({len(data)}天)")
                
                return data
            else:
                raise ValueError(f"获取的数据为空: {stock_code}")

        except Exception as e:
            if attempt < max_retries - 1:
                logger.warning(f"获取 {stock_code} 失败，重试中...")
                continue
            else:
                raise
    
    raise Exception(f"获取股票 {stock_code} 数据失败")


def _clean_data(data: pd.DataFrame, days: int) -> pd.DataFrame:
    """清洗数据（内部函数）"""
    column_mapping = {
        '日期': 'date',
        '开盘': 'open',
        '最高': 'high',
        '最低': 'low',
        '收盘': 'close',
        '成交量': 'volume'
    }
    
    for old_col, new_col in column_mapping.items():
        if old_col in data.columns:
            data = data.rename(columns={old_col: new_col})
    
    required_cols = ['date', 'open', 'high', 'low', 'close', 'volume']
    if not all(col in data.columns for col in required_cols):
        raise ValueError("数据列不完整")
    
    data['date'] = pd.to_datetime(data['date'])
    data = data.sort_values('date').reset_index(drop=True)
    
    if days and len(data) > days:
        data = data.tail(days).reset_index(drop=True)
    
    if len(data) < MIN_DATA_DAYS:
        raise ValueError(f"获取的数据不足{MIN_DATA_DAYS}天，只有{len(data)}天")
    
    numeric_cols = ['open', 'high', 'low', 'close', 'volume']
    for col in numeric_cols:
        data[col] = pd.to_numeric(data[col], errors='coerce')
    
    data = data.dropna(subset=numeric_cols)
    
    if len(data) < MIN_DATA_DAYS:
        raise ValueError(f"清理后数据不足{MIN_DATA_DAYS}天")
    
    return data
