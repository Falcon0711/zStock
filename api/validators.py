"""
API 输入校验器
集中管理所有输入校验逻辑，避免重复代码
"""

import re
from fastapi import HTTPException, Depends
from typing import Annotated


def validate_stock_code(code: str) -> str:
    """
    校验A股股票代码格式
    
    规则:
    - 必须是6位数字
    - 不能为空
    
    用法 (作为路径参数依赖):
        @app.get("/api/stock/{code}")
        def get_stock(code: Annotated[str, Depends(validate_stock_code)]):
            ...
    """
    if not code:
        raise HTTPException(
            status_code=400,
            detail="股票代码不能为空"
        )
    
    code = code.strip()
    
    if len(code) != 6:
        raise HTTPException(
            status_code=400,
            detail=f"股票代码必须是6位，当前输入: {code}"
        )
    
    if not code.isdigit():
        raise HTTPException(
            status_code=400,
            detail=f"股票代码必须是纯数字，当前输入: {code}"
        )
    
    return code


def validate_group_name(group: str) -> str:
    """
    校验股票分组名称
    
    规则:
    - 必须是 favorites, holdings, watching 之一
    """
    valid_groups = {"favorites", "holdings", "watching"}
    
    if group not in valid_groups:
        raise HTTPException(
            status_code=400,
            detail=f"无效的分组名称: {group}。有效值: {', '.join(valid_groups)}"
        )
    
    return group


def validate_search_query(q: str) -> str:
    """
    校验搜索关键词
    
    规则:
    - 不能为空
    - 长度至少1个字符
    """
    if not q or len(q.strip()) < 1:
        raise HTTPException(
            status_code=400,
            detail="搜索关键词不能为空"
        )
    
    return q.strip()


# 类型别名，方便在 API 中使用
ValidStockCode = Annotated[str, Depends(validate_stock_code)]
ValidGroupName = Annotated[str, Depends(validate_group_name)]
ValidSearchQuery = Annotated[str, Depends(validate_search_query)]
