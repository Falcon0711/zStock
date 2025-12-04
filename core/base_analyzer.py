"""
核心分析器基类 - 所有市场分析器的基类
Base Analyzer for all market types
"""

import pandas as pd
import numpy as np
from abc import ABC, abstractmethod
from datetime import datetime, timedelta


class BaseAnalyzer(ABC):
    """分析器基类"""

    def __init__(self):
        self.cache_ttl = 300  # 缓存5分钟

    @abstractmethod
    def get_data(self, symbol: str, period: str = "1y") -> pd.DataFrame:
        """获取市场数据 - 子类必须实现"""
        pass

    @abstractmethod
    def calculate_indicators(self, data: pd.DataFrame) -> pd.DataFrame:
        """计算技术指标 - 子类必须实现"""
        pass

    @abstractmethod
    def generate_signals(self, data: pd.DataFrame) -> dict:
        """生成交易信号 - 子类必须实现"""
        pass

    def calculate_sma(self, data: pd.Series, window: int) -> pd.Series:
        """计算简单移动平均线"""
        return data.rolling(window=window).mean()

    def calculate_ema(self, data: pd.Series, window: int) -> pd.Series:
        """计算指数移动平均线"""
        return data.ewm(span=window, adjust=False).mean()

    def calculate_rsi(self, data: pd.Series, window: int = 14) -> pd.Series:
        """计算RSI相对强弱指标"""
        delta = data.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=window).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=window).mean()
        rs = gain / loss
        return 100 - (100 / (1 + rs))

    def calculate_bollinger_bands(self, data: pd.Series, window: int = 20, num_std: float = 2):
        """计算布林带"""
        sma = self.calculate_sma(data, window)
        std = data.rolling(window=window).std()
        upper_band = sma + (std * num_std)
        lower_band = sma - (std * num_std)
        return upper_band, sma, lower_band

    def calculate_macd(self, data: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9):
        """计算MACD指标"""
        ema_fast = self.calculate_ema(data, fast)
        ema_slow = self.calculate_ema(data, slow)
        macd_line = ema_fast - ema_slow
        signal_line = self.calculate_ema(macd_line, signal)
        histogram = macd_line - signal_line
        return macd_line, signal_line, histogram

    def calculate_kdj(self, high: pd.Series, low: pd.Series, close: pd.Series,
                      n: int = 9, m1: int = 3, m2: int = 3):
        """计算KDJ指标"""
        rsv = (close - low.rolling(window=n).min()) / (
                high.rolling(window=n).max() - low.rolling(window=n).min()) * 100
        k = rsv.ewm(alpha=1 / m1, adjust=False).mean()
        d = k.ewm(alpha=1 / m2, adjust=False).mean()
        j = 3 * k - 2 * d
        return k, d, j

    def calculate_bbi(self, close: pd.Series, periods: list = [3, 6, 12, 24]):
        """计算BBI多空指标"""
        ma_values = [self.calculate_sma(close, period) for period in periods]
        bbi = sum(ma_values) / len(ma_values)
        return bbi

    def calculate_score(self, signals: dict) -> int:
        """计算综合评分"""
        score = 50  # 基础分数
        # 根据各种信号调整分数
        for signal_type, signal_value in signals.items():
            if signal_value == "buy":
                if "rsi" in signal_type:
                    score += 15
                elif "macd" in signal_type:
                    score += 20
                elif "kdj" in signal_type:
                    score += 18
                elif "bbi" in signal_type:
                    score += 22
                elif "trend" in signal_type:
                    score += 25
                else:
                    score += 10
            elif signal_value == "sell":
                if "rsi" in signal_type:
                    score -= 15
                elif "macd" in signal_type:
                    score -= 20
                elif "kdj" in signal_type:
                    score -= 18
                elif "bbi" in signal_type:
                    score -= 22
                elif "trend" in signal_type:
                    score -= 25
                else:
                    score -= 10

        return max(0, min(100, score))  # 限制在0-100之间
