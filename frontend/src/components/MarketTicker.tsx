import React, { useEffect, useState } from 'react';
import { useTheme } from '../ThemeContext';
import axios from 'axios';

interface TickerData {
    code: string;
    name: string;
    price: number;
    change: number;
    change_pct: number;
    volume: string;
    time: string;
}

interface TickerResponse {
    data: TickerData[];
    update_time: string;
}

const MarketTicker: React.FC = () => {
    const { theme } = useTheme();
    const [tickers, setTickers] = useState<TickerData[]>([]);
    const [loading, setLoading] = useState(true);
    const [updateTime, setUpdateTime] = useState<string>('');

    const fetchTickers = async () => {
        try {
            const response = await axios.get<TickerResponse>('/api/market/ticker');
            setTickers(response.data.data || []);
            setUpdateTime(response.data.update_time || '');
            setLoading(false);
        } catch (error) {
            console.error('获取行情数据失败:', error);
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchTickers();

        // 每30秒刷新一次
        const interval = setInterval(fetchTickers, 30000);

        return () => clearInterval(interval);
    }, []);

    if (loading && tickers.length === 0) {
        return (
            <div style={{
                background: theme.mode === 'dark' ? 'rgba(18, 18, 18, 0.95)' : 'rgba(255, 255, 255, 0.95)',
                backdropFilter: 'blur(20px)',
                WebkitBackdropFilter: 'blur(20px)',
                borderBottom: `1px solid ${theme.colors.border}`,
                padding: '1rem 2rem',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center'
            }}>
                <span style={{ color: theme.colors.textTertiary, fontSize: '0.85rem' }}>加载行情数据...</span>
            </div>
        );
    }

    // 简化显示代码的辅助函数
    const getDisplayCode = (code: string): string => {
        // 简化A股代码显示
        if (code.startsWith('sh') || code.startsWith('sz')) {
            return code.substring(2); // 移除sh/sz前缀
        }
        return code;
    };

    return (
        <div style={{
            background: theme.mode === 'dark' ? 'rgba(18, 18, 18, 0.95)' : 'rgba(248, 248, 248, 0.95)',
            backdropFilter: 'blur(20px)',
            WebkitBackdropFilter: 'blur(20px)',
            borderBottom: `1px solid ${theme.colors.border}`,
            padding: '1.2rem 2rem',
            position: 'relative',
            overflow: 'hidden'
        }}>
            {/* 更新时间 */}
            {updateTime && (
                <div style={{
                    fontSize: '0.7rem',
                    color: theme.colors.textTertiary,
                    marginBottom: '0.8rem',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '0.3rem'
                }}>
                    <span>🕐</span>
                    <span>更新时间: {updateTime}</span>
                </div>
            )}

            {/* 滑动容器 */}
            <div style={{
                display: 'flex',
                gap: '1rem',
                overflowX: 'auto',
                overflowY: 'hidden',
                scrollBehavior: 'smooth',
                paddingBottom: '0.5rem',
                // 隐藏滚动条但保留滚动功能
                scrollbarWidth: 'none',
                msOverflowStyle: 'none',
                WebkitOverflowScrolling: 'touch'
            } as React.CSSProperties & { scrollbarWidth?: string; msOverflowStyle?: string; WebkitOverflowScrolling?: string }}>
                {tickers.map((ticker) => {
                    const isUp = ticker.change_pct >= 0;
                    const changeColor = isUp ? '#FF3B30' : '#34C759'; // 红涨绿跌

                    return (
                        <div
                            key={ticker.code}
                            style={{
                                display: 'flex',
                                flexDirection: 'column',
                                gap: '0.4rem',
                                padding: '0.9rem 1rem',
                                borderRadius: '10px',
                                background: theme.mode === 'dark' ? 'rgba(38, 38, 40, 0.6)' : 'rgba(255, 255, 255, 0.8)',
                                border: `1px solid ${theme.mode === 'dark' ? 'rgba(58, 58, 60, 0.4)' : 'rgba(0, 0, 0, 0.06)'}`,
                                transition: 'all 0.2s ease',
                                cursor: 'pointer',
                                minWidth: '150px',
                                flexShrink: 0
                            }}
                            onMouseEnter={(e) => {
                                e.currentTarget.style.transform = 'translateY(-2px)';
                                e.currentTarget.style.boxShadow = theme.mode === 'dark'
                                    ? '0 4px 12px rgba(0, 0, 0, 0.3)'
                                    : '0 4px 12px rgba(0, 0, 0, 0.08)';
                            }}
                            onMouseLeave={(e) => {
                                e.currentTarget.style.transform = 'translateY(0)';
                                e.currentTarget.style.boxShadow = 'none';
                            }}
                        >
                            {/* 指数名称和代码 */}
                            <div style={{
                                display: 'flex',
                                flexDirection: 'column',
                                gap: '0.2rem'
                            }}>
                                <div style={{
                                    color: theme.colors.textPrimary,
                                    fontSize: '0.8rem',
                                    fontWeight: 600,
                                    letterSpacing: '0.01em'
                                }}>
                                    {ticker.name}
                                </div>
                                <div style={{
                                    color: theme.colors.textTertiary,
                                    fontSize: '0.7rem',
                                    fontWeight: 400
                                }}>
                                    ({getDisplayCode(ticker.code)})
                                </div>
                            </div>

                            {/* 当前价格 */}
                            <div style={{
                                color: changeColor,
                                fontSize: '1.6rem',
                                fontWeight: 700,
                                fontFamily: '-apple-system, BlinkMacSystemFont, "SF Pro Display", "Helvetica Neue", sans-serif',
                                letterSpacing: '-0.02em',
                                lineHeight: 1.2,
                                marginTop: '0.2rem'
                            }}>
                                {ticker.price.toFixed(2)}
                            </div>

                            {/* 涨跌信息 */}
                            <div style={{
                                display: 'flex',
                                alignItems: 'center',
                                gap: '0.5rem',
                                fontSize: '0.75rem',
                                color: changeColor,
                                fontWeight: 500
                            }}>
                                <span>
                                    {isUp ? '+' : ''}{ticker.change.toFixed(2)}
                                </span>
                                <span>
                                    {isUp ? '+' : ''}{ticker.change_pct.toFixed(2)}%
                                </span>
                            </div>
                        </div>
                    );
                })}
            </div>

            {/* 添加CSS样式来隐藏滚动条 */}
            <style>{`
                div::-webkit-scrollbar {
                    display: none;
                }
            `}</style>
        </div>
    );
};

export default MarketTicker;
