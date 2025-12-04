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
                    updated_at TEXT
                )
            ''')
            
            # 创建索引加速查询
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_stock_code_date 
                ON stock_history (code, date DESC)
            ''')
            
            conn.commit()
            print(f"✅ 数据库初始化完成: {self.db_path}")
    
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
        
        with sqlite3.connect(self.db_path) as conn:
            # 使用 INSERT OR REPLACE 实现增量更新
            records_before = conn.execute(
                "SELECT COUNT(*) FROM stock_history WHERE code = ?", (code,)
            ).fetchone()[0]
            
            df.to_sql('stock_history', conn, if_exists='append', index=False,
                     method='multi', chunksize=500)
            
            # 删除重复记录（保留最新）
            conn.execute('''
                DELETE FROM stock_history 
                WHERE rowid NOT IN (
                    SELECT MIN(rowid) FROM stock_history 
                    GROUP BY code, date
                )
            ''')
            
            records_after = conn.execute(
                "SELECT COUNT(*) FROM stock_history WHERE code = ?", (code,)
            ).fetchone()[0]
            
            # 更新同步日志
            last_date = df['date'].max()
            conn.execute('''
                INSERT OR REPLACE INTO sync_log 
                (code, last_sync_date, last_data_date, record_count, updated_at)
                VALUES (?, ?, ?, ?, ?)
            ''', (code, datetime.now().strftime('%Y-%m-%d %H:%M:%S'), 
                  last_date, records_after, datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
            
            conn.commit()
            
            new_records = records_after - records_before
            if new_records > 0:
                print(f"💾 {code}: 新增 {new_records} 条记录 (总计 {records_after} 条)")
            
            return new_records
    
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
            print(f"❌ 读取本地数据失败 {code}: {e}")
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
        except:
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
        except:
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
        except:
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
        except:
            return {"total_stocks": 0, "total_records": 0, "db_size_mb": 0}


# 全局单例
_local_data_service = None

def get_local_data_service() -> LocalDataService:
    """获取本地数据服务单例"""
    global _local_data_service
    if _local_data_service is None:
        _local_data_service = LocalDataService()
    return _local_data_service
