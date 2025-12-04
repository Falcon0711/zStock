import akshare as ak
import pandas as pd
from typing import List, Dict, Any
import time
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError

class SectorDataService:
    """行业板块数据服务"""

    def _fetch_sectors_with_timeout(self, timeout: int = 5) -> pd.DataFrame:
        """带超时的板块数据获取"""
        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(ak.stock_board_industry_name_em)
            try:
                return future.result(timeout=timeout)
            except FuturesTimeoutError:
                print(f"Sector fetch timed out after {timeout}s")
                return pd.DataFrame()
            except Exception as e:
                print(f"Error in sector fetch: {e}")
                return pd.DataFrame()

    def get_hot_sectors(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        获取热门行业板块（按涨幅排序）
        如果API失败，返回模拟数据
        """
        try:
            print(f"Fetching hot sectors with timeout...")
            df = self._fetch_sectors_with_timeout(timeout=5)
            
            if df is not None and not df.empty and '涨跌幅' in df.columns:
                df_sorted = df.sort_values(by='涨跌幅', ascending=False)
                
                sectors = []
                for _, row in df_sorted.head(limit).iterrows():
                    sectors.append({
                        "name": row['板块名称'],
                        "code": row['板块代码'],
                        "change_pct": float(row['涨跌幅']),
                        "price": float(row['最新价']) if '最新价' in row else 0.0,
                        "top_stock": row['领涨股票'] if '领涨股票' in row else "",
                        "top_stock_change": float(row['领涨股票-涨跌幅']) if '领涨股票-涨跌幅' in row else 0.0
                    })
                
                print(f"Successfully fetched {len(sectors)} hot sectors.")
                return sectors
        except Exception as e:
            print(f"Error fetching hot sectors: {e}")
        
        # 返回模拟数据作为fallback
        print("Using mock sector data as fallback")
        return self._get_mock_sectors(limit)
    
    def _get_mock_sectors(self, limit: int = 10) -> List[Dict[str, Any]]:
        """返回模拟板块数据"""
        mock_sectors = [
            {"name": "计算机设备", "code": "BK0429", "change_pct": 3.56, "price": 0, "top_stock": "紫光股份", "top_stock_change": 5.23},
            {"name": "半导体", "code": "BK0436", "change_pct": 2.89, "price": 0, "top_stock": "中芯国际", "top_stock_change": 4.12},
            {"name": "新能源汽车", "code": "BK0493", "change_pct": 2.34, "price": 0, "top_stock": "比亚迪", "top_stock_change": 3.45},
            {"name": "人工智能", "code": "BK0800", "change_pct": 1.98, "price": 0, "top_stock": "科大讯飞", "top_stock_change": 2.87},
            {"name": "云计算", "code": "BK0737", "change_pct": 1.67, "price": 0, "top_stock": "用友网络", "top_stock_change": 2.34},
            {"name": "5G", "code": "BK0634", "change_pct": 1.23, "price": 0, "top_stock": "中兴通讯", "top_stock_change": 1.98},
            {"name": "医药", "code": "BK0456", "change_pct": 0.98, "price": 0, "top_stock": "恒瑞医药", "top_stock_change": 1.56},
            {"name": "新材料", "code": "BK0478", "change_pct": 0.76, "price": 0, "top_stock": "万华化学", "top_stock_change": 1.23},
            {"name": "光伏", "code": "BK0481", "change_pct": 0.54, "price": 0, "top_stock": "隆基绿能", "top_stock_change": 0.98},
            {"name": "储能", "code": "BK0928", "change_pct": 0.32, "price": 0, "top_stock": "宁德时代", "top_stock_change": 0.67},
        ]
        return mock_sectors[:limit]

    def get_hot_concepts(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        获取热门概念板块
        """
        max_retries = 3
        for attempt in range(max_retries):
            try:
                # 获取东方财富概念板块实时行情
                df = ak.stock_board_concept_name_em()
                
                if df is None or df.empty:
                    continue

                if '涨跌幅' in df.columns:
                    df_sorted = df.sort_values(by='涨跌幅', ascending=False)
                    
                    sectors = []
                    for _, row in df_sorted.head(limit).iterrows():
                        sectors.append({
                            "name": row['板块名称'],
                            "code": row['板块代码'],
                            "change_pct": float(row['涨跌幅']),
                            "price": float(row['最新价']) if '最新价' in row else 0.0,
                            "top_stock": row['领涨股票'] if '领涨股票' in row else "",
                            "top_stock_change": float(row['领涨股票-涨跌幅']) if '领涨股票-涨跌幅' in row else 0.0
                        })
                    return sectors
            except Exception as e:
                print(f"Error fetching hot concepts: {e}")
                if attempt < max_retries - 1:
                    time.sleep(1)
        return []
