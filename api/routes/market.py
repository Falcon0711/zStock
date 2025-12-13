"""
市场数据相关路由
包含: 市场指数行情、行业板块、指数历史
"""

from fastapi import APIRouter, HTTPException
from typing import Optional
import time
from datetime import datetime
import akshare as ak

from utils.logger import get_logger
from services.market_data_service import MarketDataService
from services.sector_data_service import SectorDataService
from analyzers.stock_analyzer import StockAnalyzer

# 尝试加载配置
try:
    from config import ALPHA_VANTAGE_API_KEY, TUSHARE_TOKEN
except ImportError:
    ALPHA_VANTAGE_API_KEY = None
    TUSHARE_TOKEN = None

logger = get_logger(__name__)
router = APIRouter(prefix="/api", tags=["市场数据"])

# 初始化服务
market_data_service = MarketDataService(
    alpha_vantage_key=ALPHA_VANTAGE_API_KEY,
    tushare_token=TUSHARE_TOKEN
)
sector_service = SectorDataService()
analyzer = StockAnalyzer()

# 行情缓存
_ticker_cache = {
    "data": None,
    "update_time": 0
}
_ticker_cache_ttl = 30  # 缓存30秒


@router.get("/market/indices")
def get_market_indices():
    """获取市场指数"""
    return analyzer.get_market_indices()


@router.get("/market/ticker")
async def get_market_ticker():
    """获取市场指数行情（带缓存）"""
    try:
        current_time = time.time()
        if _ticker_cache["data"] is not None and len(_ticker_cache["data"].get("data", [])) > 0:
            if (current_time - _ticker_cache["update_time"]) < _ticker_cache_ttl:
                return _ticker_cache["data"]
        
        # A股指数
        a_share_indices = [
            {"code": "sh000001", "name": "上证指数"},
            {"code": "sh000300", "name": "沪深300"},
        ]
        
        # 港股指数
        hk_indices = [
            {"code": "^HSI", "name": "恒生指数"},
            {"code": "HSTECH.HK", "name": "恒生科技"},
        ]
        
        # 美股指数
        us_indices = [
            {"code": "QQQ", "name": "纳指100ETF (QQQ)"},
            {"code": "^GSPC", "name": "标普500"},
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
                logger.warning(f"获取 {index['name']} 失败: {e}")
        
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
                logger.warning(f"获取 {index['name']} 失败: {e}")
        
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
                logger.warning(f"获取 {index['name']} 失败: {e}")
        
        # 更新缓存
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
        logger.error(f"获取市场行情失败: {e}")
        return {
            "data": [],
            "update_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }


@router.get("/market/sectors")
async def get_hot_sectors():
    """获取热门行业板块"""
    return sector_service.get_hot_sectors(limit=10)


@router.get("/index/{code}/history")
async def get_index_history(code: str):
    """
    获取指数历史K线数据
    支持: A股指数(sh/sz开头), 港股指数(^HSI等), 美股指数(^NDX等)
    """
    try:
        history = []
        
        # A股指数
        if code.startswith('sh') or code.startswith('sz'):
            df = ak.stock_zh_index_daily(symbol=code)
            if df is not None and len(df) > 0:
                df = df.tail(90)
                for _, row in df.iterrows():
                    history.append({
                        "time": row['date'].strftime('%Y-%m-%d') if hasattr(row['date'], 'strftime') else str(row['date']),
                        "open": float(row['open']),
                        "high": float(row['high']),
                        "low": float(row['low']),
                        "close": float(row['close']),
                        "volume": int(row['volume']) if 'volume' in row else 0
                    })
        
        # 港股/美股指数
        elif code.startswith('^') or code.endswith('.HK'):
            import yfinance as yf
            ticker = yf.Ticker(code)
            df = ticker.history(period="3mo")
            if df is not None and len(df) > 0:
                for date, row in df.iterrows():
                    history.append({
                        "time": date.strftime('%Y-%m-%d'),
                        "open": float(row['Open']),
                        "high": float(row['High']),
                        "low": float(row['Low']),
                        "close": float(row['Close']),
                        "volume": int(row['Volume']) if 'Volume' in row else 0
                    })
        
        if not history:
            raise HTTPException(status_code=404, detail=f"无法获取指数 {code} 的历史数据")
        
        return history
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取指数 {code} 历史失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取指数历史失败: {e}")
