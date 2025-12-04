from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import sys
import os
import time

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(project_root)

from analyzers.stock_analyzer import StockAnalyzer
from services.market_data_service import MarketDataService
from services.sector_data_service import SectorDataService
from services.user_stock_service import UserStockService
from services.stock_list_service import StockListService
from fastapi.staticfiles import StaticFiles
import json
import pandas as pd
import akshare as ak
from datetime import datetime

# Load API keys from config
try:
    from config import ALPHA_VANTAGE_API_KEY, TUSHARE_TOKEN
except ImportError:
    ALPHA_VANTAGE_API_KEY = None
    TUSHARE_TOKEN = None
    print("Warning: config.py not found or API keys not set.")

app = FastAPI(title="Stock Analysis API")

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


analyzer = StockAnalyzer()
market_data_service = MarketDataService(
    alpha_vantage_key=ALPHA_VANTAGE_API_KEY,
    tushare_token=TUSHARE_TOKEN
)
sector_service = SectorDataService()
user_stock_service = UserStockService()
stock_list_service = StockListService()

class StockRequest(BaseModel):
    code: str

class AnalysisResponse(BaseModel):
    latest_price: float
    score: int
    signals: Dict[str, bool]
    kdj_k: float
    kdj_d: float
    bbi_value: float
    zhixing_trend_value: float
    zhixing_multi_value: float

class StockItem(BaseModel):
    group: str
    code: str

@app.get("/")
def read_root():
    return {"message": "Stock Analysis API is running"}

@app.get("/api/stock/{code}")
def analyze_stock(code: str):
    try:
        # 验证股票代码格式
        if not code or len(code) != 6 or not code.isdigit():
            raise HTTPException(
                status_code=400, 
                detail=f"股票代码格式错误: {code}。请输入6位数字代码（如：600328、000001）"
            )
        
        result = analyzer.analyze_stock(code)
        if not result:
            raise HTTPException(
                status_code=404, 
                detail=f"无法获取股票 {code} 的数据。请检查股票代码是否正确，或稍后重试。"
            )
        
        # Convert numpy types to native python types for JSON serialization
        response = {
            "latest_price": float(result['latest_price']),
            "score": int(result['score']),
            "signals": {k: bool(v) for k, v in result['signals'].items()},
            "kdj_k": float(result['kdj_k']),
            "kdj_d": float(result['kdj_d']),
            "bbi_value": float(result['bbi_value']),
            "zhixing_trend_value": float(result['zhixing_trend_value']),
            "zhixing_multi_value": float(result['zhixing_multi_value'])
        }
        return response
    except HTTPException:
        raise
    except Exception as e:
        error_msg = str(e)
        # 提供更友好的错误信息
        if "无法获取股票" in error_msg or "获取股票数据失败" in error_msg:
            raise HTTPException(
                status_code=404,
                detail=f"无法获取股票 {code} 的真实数据。{error_msg}"
            )
        raise HTTPException(status_code=500, detail=f"分析股票时发生错误: {error_msg}")

@app.post("/api/stock/batch")
def batch_analyze(codes: List[str]):
    results = []
    for code in codes:
        try:
            result = analyzer.analyze_stock(code)
            if result:
                results.append({
                    "code": code,
                    "score": int(result['score']),
                    "latest_price": float(result['latest_price'])
                })
        except:
            continue
    return results

@app.get("/api/stocks/hot")
def get_hot_stocks():
    return analyzer.get_hot_stocks()

@app.get("/api/market/indices")
def get_market_indices():
    return analyzer.get_market_indices()

@app.get("/api/stocks/search")
async def search_stocks(q: str, limit: int = 10):
    """
    搜索股票（支持名称或代码）
    参数:
        q: 搜索关键词
        limit: 返回结果数量限制（默认10）
    """
    if not q or len(q) < 1:
        return []
    
    try:
        # 如果输入的是纯数字且长度为6，可能是股票代码
        # 仍然进行搜索以验证代码有效性
        results = stock_list_service.search_by_name(q, limit)
        return results
    except Exception as e:
        print(f"搜索股票失败: {e}")
        return []

# 行情缓存
_ticker_cache = {
    "data": None,
    "update_time": 0
}
_ticker_cache_ttl = 30  # 缓存30秒

@app.get("/api/market/ticker")
async def get_market_ticker():
    """
    获取市场指数行情（带缓存）
    """
    try:
        # 检查缓存（只有有效数据才会被缓存）
        current_time = time.time()
        if _ticker_cache["data"] is not None and len(_ticker_cache["data"].get("data", [])) > 0:
            if (current_time - _ticker_cache["update_time"]) < _ticker_cache_ttl:
                return _ticker_cache["data"]
        
        # A股指数
        a_share_indices = [
            {"code": "sh000001", "name": "上证指数"},
            {"code": "sz399001", "name": "深证成指"},
            {"code": "sz399006", "name": "创业板指"},
            {"code": "sh000300", "name": "沪深300"},
        ]
        
        # 港股指数
        hk_indices = [
            {"code": "^HSI", "name": "恒生指数"},
            {"code": "HSTECH.HK", "name": "恒生科技"},
        ]
        
        valid_results = []
        
        # 获取A股指数
        for index in a_share_indices:
            try:
                data = market_data_service.get_cn_index(index["code"])
                if data:
                    valid_results.append({
                        "code": index["code"],
                        "name": index["name"],
                        "price": float(data["price"]),
                        "change": float(data["change"]),
                        "change_pct": float(data["change_pct"]),
                        "volume": "",
                        "time": data["time"]
                    })
            except Exception as e:
                print(f"Error fetching {index['name']}: {e}")
        
        # 获取港股指数
        for index in hk_indices:
            try:
                data = market_data_service.get_hk_index(index["code"])
                if data:
                    valid_results.append({
                        "code": index["code"],
                        "name": index["name"],
                        "price": float(data["price"]),
                        "change": float(data["change"]),
                        "change_pct": float(data["change_pct"]),
                        "volume": "",
                        "time": data["time"]
                    })
            except Exception as e:
                print(f"Error fetching {index['name']}: {e}")
        
        # 美股指数
        us_indices = [
            {"code": "^NDX", "name": "纳斯达克100"},
            {"code": "^GSPC", "name": "标普500"},
        ]
        
        # 获取美股指数
        for index in us_indices:
            try:
                data = market_data_service.get_us_index_quote(index["code"])
                if data:
                    valid_results.append({
                        "code": index["code"],
                        "name": index["name"],
                        "price": float(data["price"]),
                        "change": float(data["change"]),
                        "change_pct": float(data["change_pct"]),
                        "volume": "",
                        "time": data["time"]
                    })
            except Exception as e:
                print(f"Error fetching {index['name']}: {e}")
        
        # 更新缓存（只缓存有效数据）
        if valid_results:
            response = {
                "data": valid_results,
                "update_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            _ticker_cache["data"] = response
            _ticker_cache["update_time"] = current_time
            return response
        
        return {
            "data": [],
            "update_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
    except Exception as e:
        print(f"Error in get_market_ticker: {e}")
        return {
            "data": [],
            "update_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }

@app.get("/api/market/sectors")
async def get_hot_sectors():
    """获取热门行业板块"""
    return sector_service.get_hot_sectors(limit=10)

@app.get("/api/user/stocks")
async def get_user_stocks():
    """获取用户股票分组信息（快速返回，不获取实时行情）"""
    # 获取分组列表
    groups = user_stock_service.get_stocks()
    
    # 填充数据
    result = {
        "favorites": [],
        "holdings": [],
        "watching": []
    }
    
    # 填充每个股票的信息
    for group_name, codes in groups.items():
        for code in codes:
            stock_info = {
                "code": code,
                "name": code,  # 默认值
                "price": 0,
                "change_pct": 0
            }
            
            # 从stock_list_service获取股票名称（已缓存，速度快）
            try:
                stock_name = stock_list_service.get_stock_name(code)
                if stock_name:
                    stock_info["name"] = stock_name
            except Exception as e:
                pass
            
            result[group_name].append(stock_info)
    
    return result

@app.post("/api/user/stocks")
async def add_user_stock(item: StockItem):
    """添加股票到分组"""
    success = user_stock_service.add_stock(item.group, item.code)
    return {"success": success}

@app.delete("/api/user/stocks")
async def remove_user_stock(item: StockItem):
    """从分组删除股票"""
    success = user_stock_service.remove_stock(item.group, item.code)
    return {"success": success}

@app.get("/api/stock/{code}/history")
def get_stock_history(code: str):
    try:
        # 验证股票代码格式
        if not code or len(code) != 6 or not code.isdigit():
            raise HTTPException(
                status_code=400, 
                detail=f"股票代码格式错误: {code}。请输入6位数字代码"
            )
        
        result = analyzer.analyze_stock(code)
        if not result or 'data' not in result:
            raise HTTPException(
                status_code=404, 
                detail=f"无法获取股票 {code} 的历史数据。请检查股票代码是否正确。"
            )
        
        df = result['data']
        # Convert to format expected by Lightweight Charts
        # { time: '2018-12-22', open: 75.16, high: 82.84, low: 36.16, close: 45.72 }
        history = []
        for _, row in df.iterrows():
            history.append({
                "time": row['date'].strftime('%Y-%m-%d'),
                "open": float(row['open']),
                "high": float(row['high']),
                "low": float(row['low']),
                "close": float(row['close']),
                "volume": int(row['volume']) if 'volume' in row else 0,
                "ma5": float(row['ma5']) if pd.notna(row['ma5']) else None,
                "ma10": float(row['ma10']) if pd.notna(row['ma10']) else None,
                "ma20": float(row['ma20']) if pd.notna(row['ma20']) else None,
                "ma30": float(row['ma30']) if pd.notna(row['ma30']) else None,
                "ma60": float(row['ma60']) if pd.notna(row['ma60']) else None
            })
        return history
    except HTTPException:
        raise
    except Exception as e:
        error_msg = str(e)
        if "无法获取股票" in error_msg or "获取股票数据失败" in error_msg:
            raise HTTPException(
                status_code=404,
                detail=f"无法获取股票 {code} 的真实历史数据: {error_msg}"
            )
        raise HTTPException(status_code=500, detail=f"获取历史数据时发生错误: {error_msg}")
