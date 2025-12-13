"""
股票代码工具函数
提供股票代码格式化、验证、市场类型判断等功能
"""

from typing import Optional


def get_stock_type(code: str) -> str:
    """
    根据股票代码判断市场类型
    
    匹配规则:
    - ['43', '83', '87', '92'] 开头为 bj (北交所)
    - ['5', '6', '7', '9', '110', '113', '118', '132', '204'] 开头为 sh (上交所)
    - 其余为 sz (深交所)
    
    Args:
        code: 股票代码，如 '600519' 或 'sh600519'
    
    Returns:
        'sh' - 上海
        'sz' - 深圳
        'bj' - 北交所
    """
    if not code:
        return 'sz'
    
    assert isinstance(code, str), "stock code need str type"
    
    # 如果已有前缀直接返回
    if code.startswith(("sh", "sz", "zz", "bj")):
        return code[:2]
    
    # 北交所
    bj_head = ("43", "83", "87", "92")
    if code.startswith(bj_head):
        return "bj"
    
    # 上交所
    sh_head = ("5", "6", "7", "9", "110", "113", "118", "132", "204")
    if code.startswith(sh_head):
        return "sh"
    
    # 默认深交所
    return "sz"


def format_stock_code(code: str, with_prefix: bool = False) -> str:
    """
    格式化股票代码
    
    Args:
        code: 原始股票代码（可能带前缀）
        with_prefix: 是否返回带市场前缀的代码
    
    Returns:
        格式化后的股票代码
    """
    # 移除可能的前缀
    clean_code = code.replace('sh', '').replace('sz', '').replace('bj', '')
    clean_code = clean_code.replace('SH', '').replace('SZ', '').replace('BJ', '')
    
    # 补齐到6位
    clean_code = clean_code.zfill(6)
    
    if with_prefix:
        prefix = get_stock_type(clean_code)
        return f"{prefix}{clean_code}"
    
    return clean_code


def validate_stock_code(code: str) -> bool:
    """
    验证股票代码格式是否有效
    
    Args:
        code: 股票代码
    
    Returns:
        True - 有效, False - 无效
    """
    if not code:
        return False
    
    # 移除前缀
    clean = code.replace('sh', '').replace('sz', '').replace('bj', '')
    clean = clean.replace('SH', '').replace('SZ', '').replace('BJ', '')
    
    # 必须是6位数字
    return len(clean) == 6 and clean.isdigit()


def is_index_code(code: str) -> bool:
    """
    判断是否为指数代码
    
    Args:
        code: 代码
    
    Returns:
        True - 是指数, False - 不是指数
    """
    if code.startswith('^'):  # 美股/港股指数
        return True
    if code.endswith('.HK'):  # 港股指数
        return True
    
    # A股指数 (带前缀格式)
    if code.startswith('sh') or code.startswith('sz'):
        pure = code[2:]
        if pure.startswith('000') and len(pure) == 6:  # 上证指数
            return True
        if pure.startswith('399') and len(pure) == 6:  # 深证指数
            return True
    
    return False


def format_hk_code(code: str) -> str:
    """
    格式化港股代码为5位（补前导零）
    
    Args:
        code: 港股代码（可能带前缀）
    
    Returns:
        5位格式的港股代码
    """
    clean = code.replace('hk', '').replace('HK', '')
    return clean.zfill(5)
