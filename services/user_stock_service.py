import json
import os
from typing import Dict, List, Any
from services.market_data_service import MarketDataService

class UserStockService:
    """用户股票分组管理服务"""
    
    def __init__(self, data_file: str = "data/user_stocks.json"):
        self.data_file = data_file
        self.market_service = MarketDataService()
        self._ensure_data_file()

    def _ensure_data_file(self):
        """确保数据文件存在"""
        if not os.path.exists("data"):
            os.makedirs("data")
        
        if not os.path.exists(self.data_file):
            initial_data = {
                "favorites": [], # 自选股
                "holdings": [],  # 持有股
                "watching": []   # 观测股
            }
            with open(self.data_file, 'w', encoding='utf-8') as f:
                json.dump(initial_data, f, ensure_ascii=False, indent=2)

    def _read_data(self) -> Dict[str, List[str]]:
        """读取数据"""
        try:
            with open(self.data_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error reading user stocks: {e}")
            return {"favorites": [], "holdings": [], "watching": []}

    def _save_data(self, data: Dict[str, List[str]]):
        """保存数据"""
        try:
            with open(self.data_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Error saving user stocks: {e}")

    def get_stocks(self) -> Dict[str, List[Dict[str, Any]]]:
        """获取所有分组的股票列表（包含实时行情）"""
        data = self._read_data()
        result = {
            "favorites": [],
            "holdings": [],
            "watching": []
        }
        
        # 收集所有需要查询的股票代码
        all_codes = set()
        for group in data.values():
            all_codes.update(group)
            
        # 这里可以优化为批量查询，目前先逐个查询
        # 注意：实际项目中应使用批量接口以提高性能
        
        quotes = {}
        # 简单的缓存机制或批量查询逻辑可以在这里实现
        # 暂时复用 get_cn_index (虽然名字叫index，但逻辑里有查个股的fallback)
        # 或者我们需要在 MarketDataService 增加查个股的方法
        
        # 暂时只返回代码，前端负责查询或者这里简单模拟
        # 为了演示效果，我们尝试获取一些基本信息
        # 由于 MarketDataService.get_cn_index 主要针对指数，我们需要一个查个股的方法
        # 让我们假设 MarketDataService 有一个 get_stock_quote 方法
        
        # 修正：我们需要在 MarketDataService 中添加 get_stock_quote 方法
        # 或者直接在这里使用 akshare
        
        return data # 暂时只返回代码列表，后续完善行情获取

    def add_stock(self, group: str, code: str) -> bool:
        """添加股票到分组"""
        if group not in ["favorites", "holdings", "watching"]:
            return False
            
        data = self._read_data()
        if code not in data[group]:
            data[group].append(code)
            self._save_data(data)
            return True
        return False

    def remove_stock(self, group: str, code: str) -> bool:
        """从分组删除股票"""
        if group not in ["favorites", "holdings", "watching"]:
            return False
            
        data = self._read_data()
        if code in data[group]:
            data[group].remove(code)
            self._save_data(data)
            return True
        return False
