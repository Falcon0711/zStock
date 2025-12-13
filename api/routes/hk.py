"""
港股相关路由
包含: 港股实时行情、批量行情、详细信息、K线数据
"""

from fastapi import APIRouter, HTTPException
from typing import List

from utils.logger import get_logger
from services.hk_quotation_service import get_hk_quotation_service
from services.hk_kline_service import get_hk_kline_service

logger = get_logger(__name__)
router = APIRouter(prefix="/api/hk", tags=["港股行情"])

# 初始化服务
hk_quotation_service = get_hk_quotation_service()
hk_kline_service = get_hk_kline_service()


@router.get("/realtime/{code}")
async def get_hk_realtime_quote(code: str):
    """获取单只港股实时行情"""
    try:
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


@router.post("/realtime/batch")
async def get_hk_realtime_batch(codes: List[str]):
    """批量获取港股实时行情（最多30只）"""
    try:
        if len(codes) > 30:
            codes = codes[:30]
        
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


@router.get("/detail/{code}")
async def get_hk_stock_detail(code: str):
    """获取港股详细信息"""
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


@router.get("/kline/{code}")
async def get_hk_day_kline(code: str, days: int = 90):
    """获取港股历史日K线数据（前复权）"""
    try:
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
