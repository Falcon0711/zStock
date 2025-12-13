"""
股票列表服务 - 提供股票搜索功能
Stock List Service - Provides stock search functionality
"""

import akshare as ak
import pandas as pd
from typing import List, Dict, Optional
from functools import lru_cache
import time
import json
import os

from utils.logger import get_logger

logger = get_logger(__name__)


class StockListService:
    """股票列表服务，提供股票搜索和缓存功能"""
    
    # 本地缓存文件路径
    CACHE_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'stock_list_cache.json')
    
    def __init__(self):
        self._stock_list: Optional[pd.DataFrame] = None
        self._last_update: float = 0
        self._cache_duration: int = 86400  # 内存缓存24小时
        self._file_cache_max_age: int = 86400  # 文件缓存最多24小时
    
    def _is_cache_expired(self) -> bool:
        """检查本地缓存文件是否过期（超过24小时）"""
        if not os.path.exists(self.CACHE_FILE):
            return True
        try:
            file_mtime = os.path.getmtime(self.CACHE_FILE)
            age = time.time() - file_mtime
            return age > self._file_cache_max_age
        except (OSError, IOError) as e:
            logger.warning(f"检查缓存文件失败: {e}")
            return True
    
    def _refresh_cache_async(self):
        """异步刷新缓存（在后台更新，不阻塞主请求）"""
        import threading
        def update():
            try:
                logger.info("后台更新股票列表...")
                df = ak.stock_info_a_code_name()
                if 'code' in df.columns and 'name' in df.columns:
                    os.makedirs(os.path.dirname(self.CACHE_FILE), exist_ok=True)
                    with open(self.CACHE_FILE, 'w', encoding='utf-8') as f:
                        json.dump(df[['code', 'name']].to_dict('records'), f, ensure_ascii=False)
                    logger.info(f"股票列表后台更新完成，共 {len(df)} 只股票")
            except Exception as e:
                logger.warning(f"后台更新失败: {e}")
        
        thread = threading.Thread(target=update, daemon=True)
        thread.start()
    
    def get_stock_list(self) -> pd.DataFrame:
        """
        获取A股股票列表（优先从本地缓存加载，过期自动更新）
        返回包含code和name字段的DataFrame
        """
        current_time = time.time()
        
        # 如果内存缓存存在且未过期，直接返回
        if self._stock_list is not None and (current_time - self._last_update) < self._cache_duration:
            return self._stock_list
        
        # 检查本地缓存是否过期
        cache_expired = self._is_cache_expired()
        
        # 尝试从本地JSON文件加载（最快）
        if os.path.exists(self.CACHE_FILE):
            try:
                with open(self.CACHE_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                self._stock_list = pd.DataFrame(data)
                self._last_update = current_time
                
                if cache_expired:
                    logger.info(f"从本地缓存加载 {len(self._stock_list)} 只股票（缓存已过期，后台更新中...）")
                    self._refresh_cache_async()  # 后台异步更新
                else:
                    logger.debug(f"从本地缓存加载 {len(self._stock_list)} 只股票")
                
                return self._stock_list
            except (IOError, json.JSONDecodeError) as e:
                logger.warning(f"读取缓存文件失败: {e}")
        
        # 如果本地没有缓存，从网络获取
        try:
            logger.info("正在从网络获取股票列表...")
            df = ak.stock_info_a_code_name()
            
            if 'code' in df.columns and 'name' in df.columns:
                self._stock_list = df[['code', 'name']]
                self._last_update = current_time
                logger.info(f"股票列表已更新，共 {len(df)} 只股票")
                
                # 保存到本地缓存
                try:
                    os.makedirs(os.path.dirname(self.CACHE_FILE), exist_ok=True)
                    with open(self.CACHE_FILE, 'w', encoding='utf-8') as f:
                        json.dump(df[['code', 'name']].to_dict('records'), f, ensure_ascii=False)
                    logger.debug("股票列表已保存到本地缓存")
                except IOError as e:
                    logger.warning(f"保存缓存失败: {e}")
            else:
                if len(df.columns) >= 2:
                    df.columns = ['code', 'name'] + list(df.columns[2:])
                    self._stock_list = df[['code', 'name']]
                    self._last_update = current_time
                    
        except Exception as e:
            logger.error(f"获取股票列表失败: {e}")
            if self._stock_list is not None:
                logger.info("使用内存缓存的股票列表")
            else:
                self._stock_list = pd.DataFrame(columns=['code', 'name'])
        
        return self._stock_list

    
    def search_by_name(self, query: str, limit: int = 10) -> List[Dict[str, str]]:
        """
        按名称或代码模糊搜索股票
        
        参数:
            query: 搜索关键词（股票名称或代码的一部分）
            limit: 返回结果数量限制
            
        返回:
            股票列表，每项包含code和name
        """
        if not query:
            return []
        
        df = self.get_stock_list()
        
        if df.empty:
            return []
        
        query = query.strip()
        
        # 同时搜索代码和名称
        # 注意：使用case=False进行大小写不敏感搜索
        mask = (
            df['name'].str.contains(query, case=False, na=False) |
            df['code'].str.contains(query, case=False, na=False)
        )
        
        results = df[mask].head(limit)
        
        # 转换为字典列表
        return [
            {
                "code": str(row['code']),
                "name": str(row['name'])
            }
            for _, row in results.iterrows()
        ]
    
    def get_stock_info(self, code: str) -> Optional[Dict[str, str]]:
        """
        根据代码获取股票信息
        
        参数:
            code: 股票代码
            
        返回:
            股票信息字典，包含code和name，如果未找到返回None
        """
        df = self.get_stock_list()
        
        if df.empty:
            return None
        
        result = df[df['code'] == code]
        
        if result.empty:
            return None
        
        row = result.iloc[0]
        return {
            "code": str(row['code']),
            "name": str(row['name'])
        }
    
    def get_stock_name(self, code: str) -> Optional[str]:
        """
        根据代码获取股票中文名称
        
        参数:
            code: 股票代码
            
        返回:
            股票名称，如果未找到返回None
        """
        info = self.get_stock_info(code)
        return info['name'] if info else None
