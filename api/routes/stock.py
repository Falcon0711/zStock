"""
股票分析相关路由
包含: 单股分析、批量分析、股票搜索、热门股票
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import List, Dict, Optional
import pandas as pd

from api.validators import validate_stock_code
from utils.logger import get_logger
from analyzers.stock_analyzer import StockAnalyzer
from services.stock_list_service import StockListService

logger = get_logger(__name__)
router = APIRouter(prefix="/api", tags=["股票分析"])

# 初始化服务
analyzer = StockAnalyzer()
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


@router.get("/stock/{code}")
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


@router.get("/stock/{code}/full")
def get_stock_full(code: str = Depends(validate_stock_code)):
    """
    合并端点：一次返回分析结果 + K线历史数据
    减少前端两次请求的开销
    """
    try:
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
            "kdj_k": float(result['kdj_k']) if pd.notna(result.get('kdj_k')) else 0,
            "kdj_d": float(result['kdj_d']) if pd.notna(result.get('kdj_d')) else 0,
            "kdj_j": float(result['kdj_j']) if pd.notna(result.get('kdj_j')) else 0,
            "bbi_value": float(result['bbi_value']) if pd.notna(result.get('bbi_value')) else 0,
            "zhixing_trend_value": float(result['zhixing_trend_value']) if pd.notna(result.get('zhixing_trend_value')) else 0,
            "zhixing_multi_value": float(result['zhixing_multi_value']) if pd.notna(result.get('zhixing_multi_value')) else 0
        }
        
        # 格式化历史数据
        df = result['data']
        history = []
        for _, row in df.iterrows():
            history.append({
                "time": row['date'].strftime('%Y-%m-%d') if hasattr(row['date'], 'strftime') else str(row['date']),
                "open": float(row['open']),
                "high": float(row['high']),
                "low": float(row['low']),
                "close": float(row['close']),
                "volume": int(row['volume']) if 'volume' in row else 0,
                "bbi": float(row['bbi']) if pd.notna(row.get('bbi')) else None,
                "zhixing_trend": float(row['zhixing_trend']) if pd.notna(row.get('zhixing_trend')) else None,
                "zhixing_multi": float(row['zhixing_multi']) if pd.notna(row.get('zhixing_multi')) else None,
                "kdj_j": float(row['kdj_j']) if pd.notna(row.get('kdj_j')) else None,
                # MACD 数据
                "macd": float(row['macd']) if pd.notna(row.get('macd')) else None,
                "macd_signal": float(row['macd_signal']) if pd.notna(row.get('macd_signal')) else None,
                "macd_hist": float(row['macd_hist']) if pd.notna(row.get('macd_hist')) else None,
                # 买卖信号
                "signal_buy": bool(row.get('signal_buy', False)) if pd.notna(row.get('signal_buy')) else False,
                "signal_sell": bool(row.get('signal_sell', False)) if pd.notna(row.get('signal_sell')) else False,
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


@router.post("/stock/batch")
def batch_analyze(codes: List[str]):
    """批量分析股票"""
    results = []
    for code in codes:
        try:
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


@router.get("/stocks/hot")
def get_hot_stocks():
    """获取热门股票"""
    return analyzer.get_hot_stocks()


@router.get("/stocks/search")
async def search_stocks(q: str, limit: int = 10):
    """
    搜索股票（支持名称或代码）
    """
    if not q or len(q) < 1:
        return []
    
    try:
        results = stock_list_service.search_by_name(q, limit)
        return results
    except Exception as e:
        logger.warning(f"搜索股票失败: {e}")
        return []
