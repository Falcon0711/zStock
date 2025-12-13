"""
数据获取模块
代理到 local_data_service，保持向后兼容

历史数据统一通过 SQLite 存储和获取，实现：
1. 自动检查数据完整性
2. 收盘后智能更新
3. 减少接口访问频率
4. 统一的实时数据融合
"""

import pandas as pd
from typing import Optional

from utils.logger import get_logger

logger = get_logger(__name__)


def get_stock_data(stock_code: str, days: int = 90, include_realtime: bool = True) -> Optional[pd.DataFrame]:
    """
    获取股票K线数据（统一入口）
    
    通过 local_data_service.get_stock_data_smart() 实现：
    - 本地数据充足：立即返回 + 后台异步更新
    - 本地数据不足：同步获取初始数据 + 后台异步补全
    - 自动融合实时数据（交易时段）
    
    Args:
        stock_code: 股票代码
        days: 需要的天数
        include_realtime: 是否融合实时数据（默认True）
    
    Returns:
        包含 date, open, high, low, close, volume 列的 DataFrame
    """
    try:
        from services.local_data_service import get_local_data_service
        local_service = get_local_data_service()
        
        # 使用智能获取方法（实时融合已内置）
        data = local_service.get_stock_data_smart(
            stock_code, 
            days=days, 
            include_realtime=include_realtime
        )
        
        if data is not None and len(data) > 0:
            logger.info(f"数据获取成功: {stock_code} ({len(data)}条)")
            return data
            
    except Exception as e:
        logger.error(f"获取数据失败: {stock_code} - {e}")
    
    return None


# ==================== 向后兼容说明 ====================
# 以下函数已迁移到 local_data_service，不再在此暴露
# 如需使用，请直接调用 local_data_service 的公开方法
