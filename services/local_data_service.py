"""
本地数据存储服务
使用 SQLite 存储 A股历史K线数据，提升加载速度
"""

import sqlite3
import pandas as pd
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, List
import os
import time

# 使用统一配置和装饰器
from services.data_config import (
    REQUEST_TIMEOUT, MAX_RETRIES, RETRY_DELAY, RETRY_BACKOFF,
    DATA_COMPLETENESS_RATIO, API_RATE_LIMIT_DELAY,
    BATCH_SIZE, BATCH_DELAY
)
# 使用统一的数据源模块
from services.data_sources import TencentDataSource, AkShareDataSource
from utils.logger import get_logger
from services.data_config import REQUEST_TIMEOUT

logger = get_logger(__name__)


class LocalDataService:
    """本地数据服务 - SQLite存储"""
    
    def __init__(self, db_path: str = None):
        """
        初始化数据库连接
        db_path: 数据库文件路径，默认为 data/stock_data.db
        """
        if db_path is None:
            # 获取项目根目录
            project_root = Path(__file__).parent.parent
            db_path = project_root / "data" / "stock_data.db"
        
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        # 初始化数据源（使用统一模块）
        self._tencent = TencentDataSource()
        self._akshare = AkShareDataSource()
        
        # 初始化数据库表
        self._init_db()
    
    def _init_db(self):
        """初始化数据库表结构"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # 股票历史数据表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS stock_history (
                    code TEXT NOT NULL,
                    date TEXT NOT NULL,
                    open REAL,
                    high REAL,
                    low REAL,
                    close REAL,
                    volume REAL,
                    PRIMARY KEY (code, date)
                )
            ''')
            
            # 同步记录表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS sync_log (
                    code TEXT PRIMARY KEY,
                    last_sync_date TEXT,
                    last_data_date TEXT,
                    record_count INTEGER,
                    updated_at TEXT,
                    full_sync_completed INTEGER DEFAULT 0
                )
            ''')
            
            # 尝试添加 full_sync_completed 列（兼容旧数据库）
            try:
                cursor.execute('ALTER TABLE sync_log ADD COLUMN full_sync_completed INTEGER DEFAULT 0')
            except sqlite3.OperationalError:
                pass  # 列已存在
            
            # 创建索引加速查询
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_stock_code_date 
                ON stock_history (code, date DESC)
            ''')
            
            conn.commit()
            logger.info(f" 数据库初始化完成: {self.db_path}")
    
    def save_stock_data(self, code: str, df: pd.DataFrame) -> int:
        """
        保存股票数据到本地数据库（增量更新）
        
        Args:
            code: 股票代码
            df: 包含 date, open, high, low, close, volume 列的 DataFrame
        
        Returns:
            新增记录数
        """
        if df is None or df.empty:
            return 0
        
        # 确保日期格式统一
        df = df.copy()
        df['date'] = pd.to_datetime(df['date']).dt.strftime('%Y-%m-%d')
        df['code'] = code
        
        # 只保留需要的列
        columns = ['code', 'date', 'open', 'high', 'low', 'close', 'volume']
        df = df[columns]
        
        # 去重：dataframe内部去重
        df = df.drop_duplicates(subset=['code', 'date'])
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # 2. 过滤掉已存在的数据 (但允许更新当天的数据)
                existing_dates = set()
                cursor.execute("SELECT date FROM stock_history WHERE code = ?", (code,))
                for row in cursor.fetchall():
                     existing_dates.add(row[0])
                
                # 检查是否包含今天的数据
                today = datetime.now().strftime('%Y-%m-%d')
                if today in existing_dates and today in df['date'].values:
                    # 如果库里有今天，新数据也有今天，说明需要更新当天数据
                    # 先删除库里的今天数据
                    cursor.execute("DELETE FROM stock_history WHERE code = ? AND date = ?", (code, today))
                    existing_dates.remove(today)
                    logger.info(f" {code}: 更新当日({today})数据 (删除旧记录)")
                
                # ~df['date'].isin(existing_dates) 表示取反，即不在 existing_dates 中的
                new_data = df[~df['date'].isin(existing_dates)]
                
                if new_data.empty:
                    # logger.info(f" {code}: 没有新数据需要保存")
                    return 0
                
                # 3. 写入新数据
                records_before = len(existing_dates)
                new_data.to_sql('stock_history', conn, if_exists='append', index=False,
                          method='multi', chunksize=500)
                
                records_after = records_before + len(new_data)
                
                # 4. 更新同步日志
                last_date = df['date'].max() # 使用原始df的最大日期，确保updated_at准确
                cursor.execute('''
                    INSERT OR REPLACE INTO sync_log 
                    (code, last_sync_date, last_data_date, record_count, updated_at)
                    VALUES (?, ?, ?, ?, ?)
                ''', (code, datetime.now().strftime('%Y-%m-%d %H:%M:%S'), 
                      last_date, records_after, datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
                
                conn.commit()
                
                logger.info(f" {code}: 新增 {len(new_data)} 条记录 (总计 {records_after} 条)")
                return len(new_data)
                
        except Exception as e:
            logger.error(f" 保存数据失败 {code}: {e}")
            return 0
    
    def get_stock_data(self, code: str, days: int = 90) -> Optional[pd.DataFrame]:
        """
        从本地数据库获取股票历史数据
        
        Args:
            code: 股票代码
            days: 获取最近N天的数据
        
        Returns:
            DataFrame 或 None（无数据时）
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                query = '''
                    SELECT date, open, high, low, close, volume
                    FROM stock_history
                    WHERE code = ?
                    ORDER BY date DESC
                    LIMIT ?
                '''
                df = pd.read_sql_query(query, conn, params=(code, days))
                
                if df.empty:
                    return None
                
                # 转换日期类型并排序
                df['date'] = pd.to_datetime(df['date'])
                df = df.sort_values('date').reset_index(drop=True)
                
                return df
                
        except Exception as e:
            logger.error(f" 读取本地数据失败 {code}: {e}")
            return None
    
    def get_last_data_date(self, code: str) -> Optional[str]:
        """
        获取某只股票本地数据的最后日期
        
        Returns:
            日期字符串 'YYYY-MM-DD' 或 None
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                result = conn.execute('''
                    SELECT MAX(date) FROM stock_history WHERE code = ?
                ''', (code,)).fetchone()
                return result[0] if result[0] else None
        except sqlite3.Error as e:
            logger.warning(f"获取最后数据日期失败 {code}: {e}")
            return None
    
    def get_first_data_date(self, code: str) -> Optional[str]:
        """
        获取某只股票本地数据的最早日期
        
        Returns:
            日期字符串 'YYYY-MM-DD' 或 None
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                result = conn.execute('''
                    SELECT MIN(date) FROM stock_history WHERE code = ?
                ''', (code,)).fetchone()
                return result[0] if result[0] else None
        except sqlite3.Error as e:
            logger.warning(f"获取最早数据日期失败 {code}: {e}")
            return None
    
    def get_all_cached_stocks(self) -> List[dict]:
        """
        获取所有已缓存的股票列表及其状态
        
        Returns:
            [{'code': '600519', 'record_count': 2500, 'last_date': '2024-12-04'}, ...]
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                df = pd.read_sql_query('''
                    SELECT code, record_count, last_data_date as last_date, updated_at
                    FROM sync_log
                    ORDER BY updated_at DESC
                ''', conn)
                return df.to_dict('records')
        except sqlite3.Error as e:
            logger.warning(f"获取缓存股票列表失败: {e}")
            return []
    
    def has_data(self, code: str, min_days: int = 60) -> bool:
        """
        检查本地是否有足够的数据
        
        Args:
            code: 股票代码
            min_days: 最少需要的天数
        
        Returns:
            True/False
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                result = conn.execute('''
                    SELECT COUNT(*) FROM stock_history WHERE code = ?
                ''', (code,)).fetchone()
                return result[0] >= min_days
        except sqlite3.Error as e:
            logger.warning(f"检查数据是否存在失败 {code}: {e}")
            return False
    
    def get_stats(self) -> dict:
        """获取数据库统计信息"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                total_stocks = conn.execute(
                    "SELECT COUNT(DISTINCT code) FROM stock_history"
                ).fetchone()[0]
                
                total_records = conn.execute(
                    "SELECT COUNT(*) FROM stock_history"
                ).fetchone()[0]
                
                db_size = os.path.getsize(self.db_path) / (1024 * 1024)  # MB
                
                return {
                    "total_stocks": total_stocks,
                    "total_records": total_records,
                    "db_size_mb": round(db_size, 2)
                }
        except Exception as e:
            logger.error(f"获取数据库统计信息失败: {e}")
            return {"total_stocks": 0, "total_records": 0, "db_size_mb": 0}
    
    # ==================== 智能数据获取 ====================
    
    def get_last_trading_day(self) -> str:
        """
        获取最近的交易日
        - 周六日回退到周五
        - 当日15:30前返回昨天，15:30后返回今天
        """
        now = datetime.now()
        today = now.date()
        
        # 如果当前是15:30前，最后交易日是昨天
        if now.hour < 15 or (now.hour == 15 and now.minute < 30):
            target = today - timedelta(days=1)
        else:
            target = today
        
        # 跳过周末
        while target.weekday() >= 5:  # 5=周六, 6=周日
            target -= timedelta(days=1)
        
        return target.strftime('%Y-%m-%d')
    
    def needs_update(self, last_date: Optional[str]) -> bool:
        """
        判断数据是否需要更新
        
        规则：
        - 如果没有数据，需要更新
        - 如果最后数据日期 < 最近交易日，需要更新
        """
        if last_date is None:
            return True
        
        last_trading_day = self.get_last_trading_day()
        
        # 如果数据日期 < 最近交易日，肯定要更新
        if last_date < last_trading_day:
            return True
        
        # 如果数据日期 == 最近交易日（即今天），暂不需要更新
        # 陈旧数据检查由 _is_data_stale 方法处理
                
        return False
    
    def is_full_sync_completed(self, code: str) -> bool:
        """检查该股票是否已完成全量同步"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                result = conn.execute(
                    "SELECT full_sync_completed FROM sync_log WHERE code = ?", (code,)
                ).fetchone()
                return result is not None and result[0] == 1
        except sqlite3.Error as e:
            logger.warning(f"检查全量同步状态失败 {code}: {e}")
            return False
    
    def mark_full_sync_completed(self, code: str):
        """标记该股票已完成全量同步"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    "UPDATE sync_log SET full_sync_completed = 1 WHERE code = ?", (code,)
                )
                conn.commit()
        except Exception as e:
            logger.warning(f"标记全量同步失败 {code}: {e}")

    def _is_data_stale(self, code: str) -> bool:
        """
        检查数据是否陈旧（即：今天是交易日，且库里有今天数据，但是是在收盘前更新的）
        """
        try:
            # 1. 如果现在还在交易盘中，不需要认为陈旧（因为本来就是变动的）
            from utils.date_utils import is_trading_time
            if is_trading_time():
                return False
                
            # 2. 如果已经收盘
            # 检查同步日志
            with sqlite3.connect(self.db_path) as conn:
                row = conn.execute(
                    "SELECT updated_at, last_data_date FROM sync_log WHERE code = ?", (code,)
                ).fetchone()
                
                if not row:
                    return False
                    
                updated_at_str, last_date_str = row
                
                # 如果最后数据日期不是今天，那由 needs_update 处理，这里不管
                today_str = datetime.now().strftime('%Y-%m-%d')
                if last_date_str != today_str:
                    return False
                    
                # 如果最后数据是今天，且 updated_at 早于今天的 15:00
                updated_at = datetime.strptime(updated_at_str, '%Y-%m-%d %H:%M:%S')
                market_close_time = datetime.now().replace(hour=15, minute=0, second=0, microsecond=0)
                
                # 如果更新时间 < 今天15:00，且 现在时间 > 15:00
                if updated_at < market_close_time and datetime.now() > market_close_time:
                    logger.info(f" {code}: 数据陈旧 (更新于 {updated_at_str}, 收盘前)，强制更新")
                    return True
                    
        except Exception as e:
            logger.warning(f"检查数据陈旧失败 {code}: {e}")
            
        return False

    def get_stock_data_smart(self, code: str, days: int = 90, include_realtime: bool = True) -> Optional[pd.DataFrame]:
        """
        智能获取股票K线数据（统一入口，带实时融合）
        
        流程：
        1. 检查本地是否有足够数据
        2. 如果有：立即返回 + 后台异步更新/补全
        3. 如果没有：同步获取初始数据 + 后台异步补全历史
        4. 交易时段自动融合实时数据
        
        Args:
            code: 股票代码
            days: 需要的天数
            include_realtime: 是否融合实时数据（默认True）
        """
        from services.background_tasks import submit_background_task, TaskPriority
        from services.data_config import DATA_COMPLETENESS_RATIO, MAX_RETRIES
        from utils.date_utils import is_trading_time
        
        # 1. 尝试从本地获取
        local_data = self.get_stock_data(code, days=days)
        
        if local_data is not None and len(local_data) >= int(days * DATA_COMPLETENESS_RATIO):
            # 本地数据充足，立即返回
            logger.info(f"✅ {code}: 本地数据充足 ({len(local_data)} 条)")
            
            # 后台增量更新（高优先级 - 用户需要最新数据）
            last_date = self.get_last_data_date(code)
            if last_date and (self.needs_update(last_date) or self._is_data_stale(code)):
                submit_background_task(
                    self._background_incremental_update,
                    code,
                    task_name=f"增量更新-{code}",
                    priority=TaskPriority.HIGH  # 高优先级
                )
            
            # 后台补全历史数据（低优先级 - 不着急）
            if not self.is_full_sync_completed(code):
                submit_background_task(
                    self._background_backfill,
                    code,
                    task_name=f"历史补全-{code}",
                    priority=TaskPriority.LOW  # 低优先级
                )
            
            # 融合实时数据（交易时段）
            if include_realtime:
                local_data = self._merge_realtime_data(code, local_data)
            
            return local_data
        
        # 2. 本地数据不足，同步获取初始数据（带多源Fallback）
        logger.info(f"⚠️ {code}: 本地数据不足，获取初始数据...")
        
        initial_data = None
        
        # 优先使用腾讯
        for attempt in range(MAX_RETRIES):
            initial_data = self._tencent.fetch_kline(code, days=days)
            if initial_data is not None and not initial_data.empty:
                logger.info(f"✅ {code}: 腾讯获取成功 ({len(initial_data)} 条)")
                break
            logger.warning(f"❌ {code}: 腾讯获取失败，重试 {attempt + 1}/{MAX_RETRIES}")
            time.sleep(1)
        
        # 腾讯失败，尝试东财
        if initial_data is None or initial_data.empty:
            logger.info(f"🔄 {code}: 腾讯失败，尝试东财...")
            from services.data_sources import EastmoneyDataSource
            eastmoney = EastmoneyDataSource()
            initial_data = eastmoney.fetch_kline(code, days=min(days, 3000))
            if initial_data is not None and not initial_data.empty:
                logger.info(f"✅ {code}: 东财获取成功 ({len(initial_data)} 条)")
        
        # 东财也失败，尝试AkShare
        if initial_data is None or initial_data.empty:
            logger.info(f"🔄 {code}: 东财失败，尝试AkShare...")
            initial_data = self._akshare.fetch_kline(code, days=days)
            if initial_data is not None and not initial_data.empty:
                logger.info(f"✅ {code}: AkShare获取成功 ({len(initial_data)} 条)")
        
        if initial_data is not None and not initial_data.empty:
            self.save_stock_data(code, initial_data)
            logger.info(f"✅ {code}: 初始数据保存完成 ({len(initial_data)} 条)")
            
            # 后台补全历史（低优先级）
            submit_background_task(
                self._background_backfill,
                code,
                task_name=f"历史补全-{code}",
                priority=TaskPriority.LOW
            )
            
            # 融合实时数据
            if include_realtime:
                initial_data = self._merge_realtime_data(code, initial_data)
            
            return initial_data
        
        logger.warning(f"❌ {code}: 无法获取数据（重试 {MAX_RETRIES} 次后失败）")
        return None
    
    def _background_incremental_update(self, code: str):
        """后台增量更新任务"""
        logger.info(f"[后台任务] {code}: 开始增量更新")
        try:
            last_date = self.get_last_data_date(code)
            if not last_date:
                return
            
            # 如果是陈旧数据，从前一天开始获取
            if self._is_data_stale(code):
                fetch_start = (datetime.strptime(last_date, '%Y-%m-%d') - timedelta(days=1)).strftime('%Y-%m-%d')
            else:
                fetch_start = last_date
            
            new_data = self._fetch_incremental(code, fetch_start)
            if new_data is not None and not new_data.empty:
                self.save_stock_data(code, new_data)
                logger.info(f"[后台任务] {code}: 增量更新完成 ({len(new_data)} 条)")
        except Exception as e:
            logger.error(f"[后台任务] {code}: 增量更新失败 - {e}")
    
    def _background_backfill(self, code: str):
        """后台补全历史数据任务"""
        logger.info(f"[后台任务] {code}: 开始补全历史数据")
        try:
            from services.data_config import BACKFILL_MAX_ITERATIONS, API_RATE_LIMIT_DELAY
            
            first_date = self.get_first_data_date(code)
            if not first_date:
                logger.warning(f"[后台任务] {code}: 无法获取最早日期")
                return
            
            # 渐进式补全
            for i in range(BACKFILL_MAX_ITERATIONS):
                backward_data = self._fetch_backward_from_tencent(code, first_date)
                
                if backward_data is None or backward_data.empty:
                    logger.info(f"[后台任务] {code}: 已到达最早可用数据")
                    break
                
                self.save_stock_data(code, backward_data)
                first_date = self.get_first_data_date(code)
                logger.info(f"[后台任务] {code}: 补全第 {i+1} 批 ({len(backward_data)} 条)")
                
                time.sleep(API_RATE_LIMIT_DELAY * 2)  # 避免请求过快
            
            # 标记完成
            self.mark_full_sync_completed(code)
            logger.info(f"[后台任务] {code}: 历史数据补全完成")
            
        except Exception as e:
            logger.error(f"[后台任务] {code}: 补全失败 - {e}")
    
    def _merge_realtime_data(self, code: str, data: pd.DataFrame) -> pd.DataFrame:
        """
        融合实时数据（交易时段使用）
        
        Args:
            code: 股票代码
            data: 历史数据 DataFrame
        
        Returns:
            融合后的 DataFrame
        """
        from utils.date_utils import is_trading_time
        from datetime import datetime
        
        if not is_trading_time():
            return data
        
        try:
            from services.realtime_quotation_service import get_realtime_service
            
            today_str = datetime.now().strftime('%Y-%m-%d')
            last_date_str = data['date'].max().strftime('%Y-%m-%d')
            
            if last_date_str >= today_str:
                return data  # 已有今日数据
            
            # 获取实时行情
            service = get_realtime_service()
            quote = service.get_realtime_with_fallback(code)
            
            if not quote or code not in quote:
                return data
            
            realtime = quote[code]
            realtime_row = pd.DataFrame([{
                'date': pd.to_datetime(today_str),
                'open': float(realtime.get('open', 0)),
                'high': float(realtime.get('high', 0)),
                'low': float(realtime.get('low', 0)),
                'close': float(realtime.get('now', 0)),
                'volume': float(realtime.get('volume', 0) or realtime.get('turnover', 0))
            }])
            
            data = pd.concat([data, realtime_row], ignore_index=True)
            logger.debug(f"已融合实时数据: {code}")
            
        except Exception as e:
            logger.warning(f"融合实时数据失败 {code}: {e}")
        
        return data

    
    def _fetch_full_history(self, code: str, days: int = 365) -> Optional[pd.DataFrame]:
        """
        从网络获取完整历史数据（使用统一数据源模块）
        
        数据源优先级:
        - 如果 days <= 640: Tencent (快且稳) → AkShare
        - 如果 days > 640: AkShare (全量) → Tencent (兜底)
        
        Args:
            code: 股票代码
            days: 需要的天数 (9999 表示全量)
        
        Returns:
            DataFrame 或 None
        """
        # 全量同步场景 (days > 640): 腾讯接口最多640天，用 AkShare
        if days > 640:
            logger.info(f" [全量] {code}: 需要 {days} 天，使用 AkShare 获取历史...")
            
            # 1. AkShare（支持较长历史）
            df = self._akshare.fetch_kline(code, days)
            if df is not None:
                return df
            
            # 2. 腾讯兜底（虽然只有640天）
            df = self._tencent.fetch_kline(code, 640)
            if df is not None:
                logger.warning(f" [全量] {code}: 仅获取到腾讯640天数据")
                return df
        else:
            # 常规场景: 优先腾讯（快）
            df = self._tencent.fetch_kline(code, days)
            if df is not None:
                return df
            
            # AkShare 备用
            df = self._akshare.fetch_kline(code, days)
            if df is not None:
                return df
        
        logger.error(f" [full_history] {code} 所有数据源都失败")
        return None
    
    # ==================== 以下方法已迁移至 data_sources 模块 ====================
    # _fetch_from_akshare → AkShareDataSource.fetch_kline()
    # _fetch_from_tencent_qfq → TencentDataSource.fetch_kline()
    # _fetch_from_tushare → 已移除（不再使用）

    def _fetch_backward_from_tencent(self, code: str, first_date: str) -> Optional[pd.DataFrame]:
        """
        从腾讯获取指定日期之前的历史数据（向前补全）
        
        Args:
            code: 股票代码
            first_date: 本地最早日期 (YYYY-MM-DD)，获取该日期之前的数据
        
        Returns:
            DataFrame 或 None
        """
        try:
            import requests
            from datetime import datetime, timedelta
            
            # 计算结束日期（first_date 的前一天）
            end_dt = datetime.strptime(first_date, '%Y-%m-%d') - timedelta(days=1)
            end_date = end_dt.strftime('%Y-%m-%d')
            
            # 转换代码前缀
            if code.startswith(("5", "6", "9")):
                symbol = "sh" + code
            else:
                symbol = "sz" + code
            
            # 腾讯接口支持指定日期区间：param=code,day,start,end,count,qfq
            # 这里我们只指定 end_date，获取 end_date 之前的 640 天
            url = f"http://web.ifzq.gtimg.cn/appstock/app/fqkline/get?param={symbol},day,,{end_date},640,qfq"
            
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Referer": "http://gu.qq.com/"
            }
            
            resp = requests.get(url, headers=headers, timeout=REQUEST_TIMEOUT)
            data = resp.json()
            
            if not data.get('data') or symbol not in data['data']:
                return None
            
            stock_data = data['data'][symbol]
            klines = stock_data.get('qfqday', stock_data.get('day'))
            
            if not klines or len(klines) == 0:
                return None
            
            # 解析数据
            records = []
            for row in klines:
                if len(row) < 6:
                    continue
                record_date = row[0]
                # 过滤掉 >= first_date 的数据（防止重复）
                if record_date >= first_date:
                    continue
                records.append({
                    "date": record_date,
                    "open": float(row[1]),
                    "close": float(row[2]),
                    "high": float(row[3]),
                    "low": float(row[4]),
                    "volume": float(row[5])
                })
            
            if not records:
                return None
            
            df = pd.DataFrame(records)
            logger.info(f" [向前] {code} 获取 {len(df)} 条更早记录 (截至 {end_date})")
            return df
            
        except Exception as e:
            # 向前补全失败不是严重错误，静默处理
            return None

    def _fetch_incremental(self, code: str, last_date: str) -> Optional[pd.DataFrame]:
        """
        获取增量数据（从指定日期到今天）
        优先级: Tencent > AkShare
        """
        import akshare as ak
        
        # 0. 先尝试腾讯 (快且稳)
        # 计算大致需要的天数
        try:
            last = datetime.strptime(last_date, '%Y-%m-%d')
            delta = (datetime.now() - last).days
            if delta > 0:
                # 多请求一点以防万一
                df = self._tencent.fetch_kline(code, days=delta + 10)
                if df is not None and not df.empty:
                    # 过滤出 last_date 之后的数据
                    df = df[df['date'] > last_date]
                    if not df.empty:
                        logger.info(f" [增量] Tencent {code} 成功获取 {len(df)} 条新记录")
                        return df
        except Exception as e:
            logger.warning(f" [增量] Tencent 尝试失败: {e}")

        # ... 如果腾讯失败，回退到 AkShare ...
        
        # 从last_date后一天开始获取
        start = datetime.strptime(last_date, '%Y-%m-%d') + timedelta(days=1)
        end = datetime.now()
        
        # 如果起始日期已经超过今天，无需更新
        if start.date() > end.date():
            return None
        
        max_retries = 3
        delay = 2.0
        
        for attempt in range(max_retries + 1):
            try:
                df = ak.stock_zh_a_hist(
                    symbol=code,
                    period='daily',
                    start_date=start.strftime('%Y%m%d'),
                    end_date=end.strftime('%Y%m%d'),
                    adjust='qfq'
                )
                
                if df is None or df.empty:
                    return None
                
                # 重命名列
                df = df.rename(columns={
                    '日期': 'date',
                    '开盘': 'open',
                    '最高': 'high',
                    '最低': 'low',
                    '收盘': 'close',
                    '成交量': 'volume'
                })
                
                df = df[['date', 'open', 'high', 'low', 'close', 'volume']]
                
                logger.info(f" [增量] AkShare {code} 获取 {len(df)} 条新记录")
                return df
                
            except Exception as e:
                if attempt < max_retries:
                    logger.warning(f" [增量] AkShare {code} 获取失败 (尝试 {attempt + 1}/{max_retries + 1}): {e}")
                    # print(f"   等待 {delay:.1f} 秒后重试...")
                    time.sleep(delay)
                    delay *= 2  # 指数退避
                else:
                    logger.error(f" [增量] AkShare {code} 最终失败: {e}")
                    return None
        
        return None
    
    def update_all_cached_stocks(self, batch_size: int = 50, delay: float = 2.0):
        """
        更新所有已缓存股票的数据（收盘后批量更新）
        
        Args:
            batch_size: 每批更新的股票数量
            delay: 每批之间的延迟秒数（保护IP）
        """
        import time
        
        cached_stocks = self.get_all_cached_stocks()
        if not cached_stocks:
            logger.info("没有需要更新的股票")
            return
        
        logger.info(f" 开始更新 {len(cached_stocks)} 只股票...")
        
        updated_count = 0
        for i, stock in enumerate(cached_stocks):
            code = stock['code']
            last_date = stock.get('last_date')
            
            # 检查是否需要更新
            if not self.needs_update(last_date):
                continue
            
            try:
                new_data = self._fetch_incremental(code, last_date)
                if new_data is not None and not new_data.empty:
                    self.save_stock_data(code, new_data)
                    updated_count += 1
            except Exception as e:
                logger.error(f" 更新 {code} 失败: {e}")
            
            # 每批次后延迟，保护IP
            if (i + 1) % batch_size == 0:
                logger.info(f" 已处理 {i + 1}/{len(cached_stocks)}，休息 {delay} 秒...")
                time.sleep(delay)
        
        logger.info(f" 更新完成，共更新 {updated_count} 只股票")


# 全局单例
_local_data_service = None

def get_local_data_service() -> LocalDataService:
    """获取本地数据服务单例"""
    global _local_data_service
    if _local_data_service is None:
        _local_data_service = LocalDataService()
    return _local_data_service
