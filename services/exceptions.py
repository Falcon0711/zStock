# coding:utf8
"""
自定义异常类
用于数据获取过程中的错误分类和处理
"""


class DataSourceError(Exception):
    """数据源基础异常"""
    pass


class NetworkError(DataSourceError):
    """网络连接错误"""
    pass


class TimeoutError(DataSourceError):
    """请求超时错误"""
    pass


class RateLimitError(DataSourceError):
    """API 频率限制错误（IP被封禁等）"""
    pass


class ParseError(DataSourceError):
    """数据解析错误"""
    pass


class DataNotFoundError(DataSourceError):
    """数据不存在错误（股票代码无效等）"""
    pass


class AuthenticationError(DataSourceError):
    """认证错误（Token无效等）"""
    pass
