from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import sys
import os
import time

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from analyzers.stock_analyzer import StockAnalyzer
from services.market_data_service import MarketDataService
from services.sector_data_service import SectorDataService
from services.user_stock_service import UserStockService
from services.stock_list_service import StockListService
from services.realtime_quotation_service import get_realtime_service
from services.realtime_kline_service import get_realtime_kline_service
from services.hk_quotation_service import get_hk_quotation_service
from services.hk_kline_service import get_hk_kline_service
from services.exchange_rate_service import get_exchange_rate_service
from api.validators import validate_stock_code
from utils.logger import get_logger
from fastapi.staticfiles import StaticFiles
import json
import pandas as pd
import akshare as ak
from datetime import datetime

logger = get_logger(__name__)

# Load API keys from config
try:
    from config import ALPHA_VANTAGE_API_KEY, TUSHARE_TOKEN
except ImportError:
    ALPHA_VANTAGE_API_KEY = None
    TUSHARE_TOKEN = None
    logger.warning("config.py not found or API keys not set.")

app = FastAPI(title="Stock Analysis API")

# CORS 配置: 生产环境应限制域名
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "*").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "DELETE"],
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
def analyze_stock(code: str = Depends(validate_stock_code)):
    """分析单只股票"""
    try:
        result = analyzer.analyze_stock(code)
        if not result:
            raise HTTPException(
                status_code=404, 
                detail=f"无法获取股票 {code} 的数据"
            )
        
        return {
            "latest_price": float(result['latest_price']),
            "score": int(result['score']),
            "signals": {k: bool(v) for k, v in result['signals'].items()},
            "kdj_k": float(result['kdj_k']),
            "kdj_d": float(result['kdj_d']),
            "bbi_value": float(result['bbi_value']),
            "zhixing_trend_value": float(result['zhixing_trend_value']),
            "zhixing_multi_value": float(result['zhixing_multi_value'])
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"分析股票 {code} 失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"分析股票时发生错误: {e}")


@app.get("/api/stock/{code}/full")
def get_stock_full(code: str = Depends(validate_stock_code)):
    """
    🆕 合并端点：一次返回分析结果 + K线历史数据
    减少前端两次请求的开销
    """
    try:
        # 只调用一次 analyze_stock，结果会被缓存
        result = analyzer.analyze_stock(code)
        if not result or 'data' not in result:
            raise HTTPException(
                status_code=404, 
                detail=f"无法获取股票 {code} 的数据"
            )
        
        # 格式化分析数据
        analysis = {
            "latest_price": float(result['latest_price']),
            "score": int(result['score']),
            "signals": {k: bool(v) for k, v in result['signals'].items()},
            "kdj_k": float(result['kdj_k']),
            "kdj_d": float(result['kdj_d']),
            "bbi_value": float(result['bbi_value']),
            "zhixing_trend_value": float(result['zhixing_trend_value']),
            "zhixing_multi_value": float(result['zhixing_multi_value'])
        }
        
        # 格式化历史数据（直接从缓存的 result['data'] 中取）
        df = result['data']
        history = []
        for _, row in df.iterrows():
            history.append({
                "time": row['date'].strftime('%Y-%m-%d'),
                "open": float(row['open']),
                "high": float(row['high']),
                "low": float(row['low']),
                "close": float(row['close']),
                "volume": int(row['volume']) if 'volume' in row else 0,
                # 自定义指标
                "bbi": float(row['bbi']) if pd.notna(row.get('bbi')) else None,
                "zhixing_trend": float(row['zhixing_trend']) if pd.notna(row.get('zhixing_trend')) else None,
                "zhixing_multi": float(row['zhixing_multi']) if pd.notna(row.get('zhixing_multi')) else None,
                "kdj_j": float(row['kdj_j']) if pd.notna(row.get('kdj_j')) else None,
            })
        
        return {
            "analysis": analysis,
            "history": history
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取股票 {code} 完整数据失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取数据时发生错误: {e}")


@app.post("/api/stock/batch")
def batch_analyze(codes: List[str]):
    """批量分析股票"""
    results = []
    for code in codes:
        try:
            # 简单校验
            if len(code) != 6 or not code.isdigit():
                continue
            result = analyzer.analyze_stock(code)
            if result:
                results.append({
                    "code": code,
                    "score": int(result['score']),
                    "latest_price": float(result['latest_price'])
                })
        except Exception as e:
            logger.warning(f"批量分析 {code} 失败: {e}")
            continue
    return results

@app.get("/api/stocks/hot")
def get_hot_stocks():
    return analyzer.get_hot_stocks()


@app.get("/api/market/indices")
def get_market_indices():
    return analyzer.get_market_indices()


@app.get("/api/index/{code}/history")
async def get_index_history(code: str):
    """
    获取指数历史K线数据
    支持: A股指数(sh/sz开头), 港股指数(^HSI等), 美股指数(^NDX等)
    """
    try:
        history = []
        
        # A股指数 (sh000001, sz399001 等)
        if code.startswith('sh') or code.startswith('sz'):
            df = ak.stock_zh_index_daily(symbol=code)
            if df is not None and len(df) > 0:
                # 取最近90天
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
        
        # 港股/美股指数 (^HSI, ^NDX, ^GSPC 等) - 使用 yfinance
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
    """获取用户股票分组信息（包含实时行情）- 使用缓存数据"""
    from analyzers.data_fetcher import get_stock_data
    
    groups = user_stock_service.get_stocks()
    
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
                "name": stock_list_service.get_stock_name(code) or code,
                "price": 0,
                "change_pct": 0
            }
            
            # 🆕 使用统一的缓存数据获取（复用 data_fetcher 的缓存）
            try:
                # 只需要最近几天数据计算涨跌幅，但用相同天数以命中缓存
                data = get_stock_data(code, days=90)
                if data is not None and len(data) >= 2:
                    latest = data.iloc[-1]
                    prev = data.iloc[-2]
                    close = float(latest['close'])
                    prev_close = float(prev['close'])
                    change_pct = (close - prev_close) / prev_close * 100 if prev_close else 0
                    stock_info['price'] = round(close, 2)
                    stock_info['change_pct'] = round(change_pct, 2)
            except Exception as e:
                logger.warning(f"获取 {code} 行情失败: {e}")
            
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


# ============================================
# 实时行情 API 端点
# ============================================

# 初始化实时行情服务
realtime_service = get_realtime_service('sina')
realtime_kline_service = get_realtime_kline_service('sina')
hk_quotation_service = get_hk_quotation_service()
hk_kline_service = get_hk_kline_service()
exchange_rate_service = get_exchange_rate_service()


@app.get("/api/realtime/{code}")
async def get_realtime_quote(code: str):
    """
    获取单只股票实时行情
    
    Args:
        code: 6位股票代码，如 '600519'
    
    Returns:
        实时行情数据（包含现价、开盘、最高、最低、成交量等）
    """
    try:
        # 验证股票代码格式
        if not code or len(code) != 6 or not code.isdigit():
            raise HTTPException(
                status_code=400,
                detail=f"股票代码格式错误: {code}。请输入6位数字代码"
            )
        
        data = realtime_service.get_realtime(code)
        
        if not data or code not in data:
            # 尝试带前缀查找
            for key in data:
                if key.endswith(code):
                    quote = data[key]
                    break
            else:
                raise HTTPException(
                    status_code=404,
                    detail=f"无法获取股票 {code} 的实时行情"
                )
        else:
            quote = data[code]
        
        # 计算涨跌幅
        now = quote.get('now', 0)
        close = quote.get('close', now)  # 昨收
        change_pct = 0
        if close and close > 0:
            change_pct = round((now - close) / close * 100, 2)
        
        return {
            "code": code,
            "name": quote.get('name', ''),
            "now": float(now),
            "open": float(quote.get('open', 0)),
            "close": float(close),
            "high": float(quote.get('high', 0)),
            "low": float(quote.get('low', 0)),
            "volume": int(quote.get('turnover', 0)),
            "turnover": float(quote.get('volume', 0)),
            "change_pct": change_pct,
            "bid1": float(quote.get('bid1', 0)),
            "ask1": float(quote.get('ask1', 0)),
            "time": quote.get('time', ''),
            "date": quote.get('date', datetime.now().strftime('%Y-%m-%d'))
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取 {code} 实时行情失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取实时行情失败: {e}")


@app.post("/api/realtime/batch")
async def get_realtime_batch(codes: List[str]):
    """
    批量获取实时行情（最多50只）
    
    Args:
        codes: 股票代码列表，如 ['600519', '000001', '300750']
    
    Returns:
        实时行情数据列表
    """
    try:
        # 限制批量数量
        if len(codes) > 50:
            codes = codes[:50]
        
        # 过滤无效代码
        valid_codes = [c for c in codes if c and len(c) == 6 and c.isdigit()]
        
        if not valid_codes:
            return []
        
        data = realtime_service.get_realtime(valid_codes)
        
        results = []
        for code in valid_codes:
            quote = data.get(code)
            if not quote:
                # 尝试带前缀查找
                for key in data:
                    if key.endswith(code):
                        quote = data[key]
                        break
            
            if quote and quote.get('now', 0) > 0:
                now = quote.get('now', 0)
                close = quote.get('close', now)
                change_pct = 0
                if close and close > 0:
                    change_pct = round((now - close) / close * 100, 2)
                
                results.append({
                    "code": code,
                    "name": quote.get('name', ''),
                    "now": float(now),
                    "change_pct": change_pct,
                    "high": float(quote.get('high', 0)),
                    "low": float(quote.get('low', 0)),
                    "volume": int(quote.get('turnover', 0)),
                })
        
        return results
    except Exception as e:
        logger.error(f"批量获取实时行情失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"批量获取实时行情失败: {e}")


@app.get("/api/realtime/market")
async def get_market_snapshot(limit: int = 50):
    """
    获取全市场行情快照
    
    Args:
        limit: 返回股票数量，默认50，最大500
    
    Returns:
        全市场行情数据列表
    """
    try:
        # 限制数量
        limit = min(max(1, limit), 500)
        
        data = realtime_service.get_market_snapshot(limit=limit)
        
        results = []
        for code, quote in data.items():
            if quote.get('now', 0) > 0:
                now = quote.get('now', 0)
                close = quote.get('close', now)
                change_pct = 0
                if close and close > 0:
                    change_pct = round((now - close) / close * 100, 2)
                
                results.append({
                    "code": code,
                    "name": quote.get('name', ''),
                    "now": float(now),
                    "change_pct": change_pct,
                    "high": float(quote.get('high', 0)),
                    "low": float(quote.get('low', 0)),
                    "volume": int(quote.get('turnover', 0)),
                })
        
        # 按涨跌幅排序
        results.sort(key=lambda x: x['change_pct'], reverse=True)
        
        return {
            "data": results,
            "total": len(results),
            "update_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
    except Exception as e:
        logger.error(f"获取市场快照失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取市场快照失败: {e}")


@app.get("/api/stock/{code}/kline-realtime")
async def get_kline_with_realtime(code: str, days: int = 90):
    """
    获取历史K线 + 实时更新
    
    如果当日交易中，会将实时行情合并到历史K线的最后一根K线中
    
    Args:
        code: 6位股票代码
        days: 历史天数，默认90天
    
    Returns:
        K线数据列表（历史 + 实时）
    """
    try:
        # 验证股票代码格式
        if not code or len(code) != 6 or not code.isdigit():
            raise HTTPException(
                status_code=400,
                detail=f"股票代码格式错误: {code}。请输入6位数字代码"
            )
        
        days = min(max(1, days), 365)  # 限制1-365天
        
        klines = realtime_kline_service.get_kline_with_realtime(code, days=days)
        
        if not klines:
            raise HTTPException(
                status_code=404,
                detail=f"无法获取股票 {code} 的K线数据"
            )
        
        return klines
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取 {code} 实时K线失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取实时K线失败: {e}")


# ============================================
# 分时走势 API 端点
# ============================================

@app.get("/api/stock/{code}/intraday")
async def get_stock_intraday(code: str):
    """
    获取股票当日分时走势数据
    
    Args:
        code: 6位股票代码，如 '600519'
    
    Returns:
        当日分时走势数据（分钟级别）
    """
    try:
        # 验证股票代码格式
        if not code or len(code) != 6 or not code.isdigit():
            raise HTTPException(
                status_code=400,
                detail=f"股票代码格式错误: {code}。请输入6位数字代码"
            )
        
        data = realtime_service.get_intraday(code)
        
        if 'error' in data:
            raise HTTPException(status_code=404, detail=data['error'])
        
        return data
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取 {code} 分时数据失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取分时数据失败: {e}")


# ============================================
# 港股行情 API 端点
# ============================================

@app.get("/api/hk/realtime/{code}")
async def get_hk_realtime_quote(code: str):
    """
    获取单只港股实时行情
    
    Args:
        code: 港股代码，如 '00700', '700', 'hk00700'
    
    Returns:
        港股实时行情数据
    """
    try:
        # 验证代码格式（允许4-5位数字或hk前缀）
        clean_code = code.replace("hk", "").replace("HK", "")
        if not clean_code.isdigit() or len(clean_code) > 5:
            raise HTTPException(
                status_code=400,
                detail=f"港股代码格式错误: {code}。请输入4-5位数字代码"
            )
        
        data = hk_quotation_service.get_stock_detail(code)
        
        if not data or data.get('price', 0) == 0:
            raise HTTPException(
                status_code=404,
                detail=f"无法获取港股 {code} 的实时行情"
            )
        
        return data
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取港股 {code} 实时行情失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取港股实时行情失败: {e}")


@app.post("/api/hk/realtime/batch")
async def get_hk_realtime_batch(codes: List[str]):
    """
    批量获取港股实时行情（最多30只）
    
    Args:
        codes: 港股代码列表，如 ['00700', '00941', '09988']
    
    Returns:
        港股实时行情数据列表
    """
    try:
        # 限制批量数量
        if len(codes) > 30:
            codes = codes[:30]
        
        # 过滤无效代码
        valid_codes = []
        for c in codes:
            clean_code = c.replace("hk", "").replace("HK", "")
            if clean_code.isdigit() and len(clean_code) <= 5:
                valid_codes.append(c)
        
        if not valid_codes:
            return []
        
        data = hk_quotation_service.get_realtime(valid_codes)
        
        results = []
        for code, quote in data.items():
            if quote.get('price', 0) > 0:
                results.append({
                    "code": code,
                    "name": quote.get('name', ''),
                    "price": float(quote.get('price', 0)),
                    "change": float(quote.get('change', 0)),
                    "change_pct": float(quote.get('change_pct', 0)),
                    "high": float(quote.get('high', 0)),
                    "low": float(quote.get('low', 0)),
                    "volume": float(quote.get('volume', 0)),
                    "amount": float(quote.get('amount', 0)),
                    "turnover": float(quote.get('turnover', 0)),
                })
        
        return results
    except Exception as e:
        logger.error(f"批量获取港股实时行情失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"批量获取港股实时行情失败: {e}")


@app.get("/api/hk/detail/{code}")
async def get_hk_stock_detail(code: str):
    """
    获取港股详细信息
    
    包含完整的行情数据、市值、52周高低等信息
    
    Args:
        code: 港股代码
    
    Returns:
        详细港股数据
    """
    try:
        data = hk_quotation_service.get_stock_detail(code)
        
        if not data:
            raise HTTPException(
                status_code=404,
                detail=f"无法获取港股 {code} 的详细信息"
            )
        
        return data
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取港股 {code} 详细信息失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取港股详细信息失败: {e}")


@app.get("/api/hk/kline/{code}")
async def get_hk_day_kline(code: str, days: int = 90):
    """
    获取港股历史日K线数据（前复权）
    
    Args:
        code: 港股代码
        days: 获取天数，默认90天，最大660天
    
    Returns:
        [{date, open, close, high, low, volume}, ...]
    """
    try:
        # 限制天数范围
        days = min(max(1, days), 660)
        
        klines = hk_kline_service.get_day_kline(code, days=days)
        
        if not klines:
            raise HTTPException(
                status_code=404,
                detail=f"无法获取港股 {code} 的K线数据"
            )
        
        return klines
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取港股 {code} K线数据失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取港股K线数据失败: {e}")


# ============================================
# 外汇牌价 API 端点
# ============================================

@app.get("/api/exchange/usd")
async def get_usd_exchange_rate():
    """
    获取美元汇率（中国银行）
    
    Returns:
        {
            'currency': '美元',
            'currency_code': 'USD',
            'buy_price': 7.25,
            'sell_price': 7.28,
            'middle_price': 7.265,
            'update_time': '2025-12-08 10:30:00'
        }
    """
    try:
        rate = exchange_rate_service.get_exchange_rate("USD")
        
        if not rate:
            raise HTTPException(
                status_code=404,
                detail="无法获取美元汇率数据"
            )
        
        return rate
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取美元汇率失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取美元汇率失败: {e}")


@app.get("/api/exchange/all")
async def get_all_exchange_rates():
    """
    获取所有支持的外汇牌价
    
    Returns:
        {'USD': {...}, ...}
    """
    try:
        rates = exchange_rate_service.get_all_rates()
        
        if not rates:
            raise HTTPException(
                status_code=404,
                detail="无法获取外汇牌价数据"
            )
        
        return rates
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取外汇牌价失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取外汇牌价失败: {e}")
