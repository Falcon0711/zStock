import React, { useState, useEffect } from 'react';
import { useTheme } from '../ThemeContext';
import KLineChart from './KLineChart';
import IntradayChart from './IntradayChart';
import { fetchIntraday } from '../services/api';
import type { IntradayResponse } from '../services/api';

interface DashboardProps {
    analysis: any;
    history: any[];
    loading: boolean;
    stockCode?: string;  // 🆕 股票代码
    stockName?: string;  // 🆕 股票名称
}

const Dashboard: React.FC<DashboardProps> = ({ analysis, history, loading, stockCode, stockName }) => {
    const { theme } = useTheme();

    // 🆕 图表视图状态
    const [chartView, setChartView] = useState<'kline' | 'intraday'>('kline');
    const [intradayData, setIntradayData] = useState<IntradayResponse | null>(null);
    const [intradayLoading, setIntradayLoading] = useState(false);

    // 🆕 当切换到分时图时加载数据
    useEffect(() => {
        if (chartView === 'intraday' && stockCode && !intradayData) {
            setIntradayLoading(true);
            fetchIntraday(stockCode)
                .then(data => {
                    setIntradayData(data);
                })
                .catch(err => {
                    console.error('获取分时数据失败:', err);
                })
                .finally(() => {
                    setIntradayLoading(false);
                });
        }
    }, [chartView, stockCode, intradayData]);

    // 🆕 当股票代码变化时重置分时数据
    useEffect(() => {
        setIntradayData(null);
        setChartView('kline');
    }, [stockCode]);

    if (loading) {
        return (
            <div style={{
                padding: '4rem 2rem',
                textAlign: 'center',
                color: theme.colors.textSecondary
            }}>
                <div style={{ fontSize: '2rem', marginBottom: '1rem', animation: 'spin 2s linear infinite' }}>
                    📊
                </div>
                <div style={{ fontSize: '1.1rem' }}>分析中...</div>
                <style>{`
                    @keyframes spin {
                        from { transform: rotate(0deg); }
                        to { transform: rotate(360deg); }
                    }
                `}</style>
            </div>
        );
    }

    // 🆕 如果没有 analysis 但有 history，只显示K线图（用于指数展示）
    if (!analysis && history && history.length > 0) {
        return (
            <div style={{
                padding: '2.5rem',
                maxWidth: '1200px',
                margin: '0 auto',
                animation: 'fadeIn 0.5s ease-out'
            }}>
                <div style={{
                    background: theme.colors.bgSecondary,
                    borderRadius: '24px',
                    padding: '2rem',
                    boxShadow: theme.mode === 'dark'
                        ? '0 4px 20px rgba(0,0,0,0.2)'
                        : '0 4px 20px rgba(0,0,0,0.05)',
                    transition: 'all 0.3s ease'
                }}>
                    <h3 style={{
                        color: theme.colors.textPrimary,
                        fontSize: '1.2rem',
                        fontWeight: 600,
                        marginTop: 0,
                        marginBottom: '1.5rem',
                        display: 'flex',
                        alignItems: 'center',
                        gap: '0.5rem',
                        letterSpacing: '-0.01em'
                    }}>
                        📈 K线走势
                    </h3>
                    <KLineChart data={history} theme={theme} />
                </div>
                <style>{`
                    @keyframes fadeIn {
                        from { opacity: 0; transform: translateY(10px); }
                        to { opacity: 1; transform: translateY(0); }
                    }
                `}</style>
            </div>
        );
    }

    if (!analysis) return null;

    // 🆕 切换按钮样式
    const TabButton: React.FC<{
        active: boolean;
        onClick: () => void;
        children: React.ReactNode;
    }> = ({ active, onClick, children }) => (
        <button
            onClick={onClick}
            style={{
                padding: '0.5rem 1rem',
                borderRadius: '8px',
                border: 'none',
                background: active
                    ? (theme.mode === 'dark' ? 'rgba(0, 122, 255, 0.2)' : 'rgba(0, 122, 255, 0.1)')
                    : 'transparent',
                color: active ? '#007AFF' : theme.colors.textSecondary,
                fontSize: '0.9rem',
                fontWeight: active ? 600 : 400,
                cursor: 'pointer',
                transition: 'all 0.2s ease',
            }}
        >
            {children}
        </button>
    );

    return (
        <div style={{
            padding: '2.5rem',
            maxWidth: '1200px',
            margin: '0 auto',
            animation: 'fadeIn 0.5s ease-out'
        }}>
            <div style={{
                marginBottom: '2rem',
                display: 'flex',
                alignItems: 'center',
                gap: '0.75rem'
            }}>
                <h2 style={{
                    color: theme.colors.textPrimary,
                    fontSize: '2rem',
                    fontWeight: 700,
                    margin: 0,
                    letterSpacing: '-0.02em'
                }}>
                    {stockName && stockCode ? `${stockName}(${stockCode})` : '分析报告'}
                </h2>
            </div>

            {/* Metrics Grid */}
            <div style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))',
                gap: '1.5rem',
                marginBottom: '2.5rem'
            }}>
                <MetricCard
                    theme={theme}
                    icon="💰"
                    label="最新价格"
                    value={`¥${analysis.latest_price.toFixed(2)}`}
                    color={theme.colors.accent}
                />
                <MetricCard
                    theme={theme}
                    icon={analysis.score >= 60 ? '📈' : '📉'}
                    label="综合评分"
                    value={analysis.score.toString()}
                    color={analysis.score >= 60 ? theme.colors.success : theme.colors.error}
                />
                <MetricCard
                    theme={theme}
                    icon="📊"
                    label="KDJ K值"
                    value={analysis.kdj_k.toFixed(2)}
                    color={theme.colors.warning}
                />
                <MetricCard
                    theme={theme}
                    icon="📉"
                    label="BBI多空值"
                    value={analysis.bbi_value.toFixed(2)}
                    color={theme.colors.textPrimary}
                />
            </div>


            {/* 🆕 K线图表 / 分时图表 (带切换) */}
            {history && history.length > 0 && (
                <div style={{
                    background: theme.colors.bgSecondary,
                    borderRadius: '24px',
                    padding: '2rem',
                    boxShadow: theme.mode === 'dark'
                        ? '0 4px 20px rgba(0,0,0,0.2)'
                        : '0 4px 20px rgba(0,0,0,0.05)',
                    transition: 'all 0.3s ease'
                }}>
                    {/* 🆕 标题栏带切换按钮 */}
                    <div style={{
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'space-between',
                        marginBottom: '1.5rem',
                        flexWrap: 'wrap',
                        gap: '1rem'
                    }}>
                        {/* 左侧：标题 + 交易信号 */}
                        <div style={{
                            display: 'flex',
                            alignItems: 'center',
                            gap: '1.5rem',
                            flexWrap: 'wrap'
                        }}>
                            <h3 style={{
                                color: theme.colors.textPrimary,
                                fontSize: '1.2rem',
                                fontWeight: 600,
                                margin: 0,
                                display: 'flex',
                                alignItems: 'center',
                                gap: '0.5rem',
                                letterSpacing: '-0.01em'
                            }}>
                                📈 {chartView === 'kline' ? 'K线走势' : '当日走势'}
                            </h3>

                            {/* 🆕 交易信号标签 */}
                            {analysis.signals && Object.keys(analysis.signals).some(key => analysis.signals[key]) && (
                                <div style={{
                                    display: 'flex',
                                    alignItems: 'center',
                                    gap: '0.5rem',
                                    padding: '0.4rem 0.75rem',
                                    background: theme.mode === 'dark' ? 'rgba(255,255,255,0.05)' : 'rgba(0,0,0,0.03)',
                                    borderRadius: '8px'
                                }}>
                                    <span style={{
                                        fontSize: '0.8rem',
                                        color: theme.colors.textSecondary,
                                        display: 'flex',
                                        alignItems: 'center',
                                        gap: '0.25rem'
                                    }}>
                                        🚦 交易信号
                                    </span>
                                    {Object.entries(analysis.signals)
                                        .filter(([_, value]) => value)
                                        .map(([key, _]) => (
                                            <span
                                                key={key}
                                                style={{
                                                    padding: '0.25rem 0.6rem',
                                                    borderRadius: '6px',
                                                    background: key.includes('buy')
                                                        ? `${theme.colors.success}20`
                                                        : `${theme.colors.error}20`,
                                                    color: key.includes('buy') ? theme.colors.success : theme.colors.error,
                                                    fontSize: '0.75rem',
                                                    fontWeight: 600,
                                                    display: 'inline-flex',
                                                    alignItems: 'center',
                                                    gap: '0.25rem'
                                                }}
                                            >
                                                <span>{key.includes('buy') ? '🟢' : '🔴'}</span>
                                                {formatSignalName(key)}
                                            </span>
                                        ))
                                    }
                                </div>
                            )}
                        </div>

                        {/* 右侧：切换按钮组 */}
                        <div style={{
                            display: 'flex',
                            gap: '0.25rem',
                            background: theme.mode === 'dark' ? 'rgba(255,255,255,0.05)' : 'rgba(0,0,0,0.03)',
                            padding: '0.25rem',
                            borderRadius: '10px'
                        }}>
                            <TabButton
                                active={chartView === 'kline'}
                                onClick={() => setChartView('kline')}
                            >
                                K线走势
                            </TabButton>
                            <TabButton
                                active={chartView === 'intraday'}
                                onClick={() => setChartView('intraday')}
                            >
                                当日走势
                            </TabButton>
                        </div>
                    </div>

                    {/* 🆕 根据状态显示不同图表 */}
                    {chartView === 'kline' ? (
                        <KLineChart data={history} theme={theme} />
                    ) : intradayLoading ? (
                        <div style={{
                            padding: '4rem',
                            textAlign: 'center',
                            color: theme.colors.textSecondary
                        }}>
                            <div style={{ fontSize: '1.5rem', marginBottom: '0.5rem' }}>⏳</div>
                            <div>加载分时数据中...</div>
                        </div>
                    ) : intradayData ? (
                        <IntradayChart
                            data={intradayData.data}
                            theme={theme}
                            stockInfo={{
                                name: intradayData.name,
                                now: intradayData.now,
                                open: intradayData.open,
                                close: intradayData.close,
                                high: intradayData.high,
                                low: intradayData.low,
                                change_pct: intradayData.change_pct,
                                date: intradayData.date
                            }}
                        />
                    ) : (
                        <div style={{
                            padding: '4rem',
                            textAlign: 'center',
                            color: theme.colors.textTertiary
                        }}>
                            <div style={{ fontSize: '2rem', marginBottom: '1rem' }}>📈</div>
                            <div>暂无分时数据</div>
                        </div>
                    )}
                </div>
            )}

            <style>{`
                @keyframes fadeIn {
                    from { opacity: 0; transform: translateY(10px); }
                    to { opacity: 1; transform: translateY(0); }
                }
            `}</style>
        </div>
    );
};

const MetricCard: React.FC<{
    theme: any;
    icon: string;
    label: string;
    value: string;
    color: string;
}> = ({ theme, icon, label, value, color }) => {
    return (
        <div
            style={{
                background: theme.colors.bgSecondary,
                borderRadius: '24px',
                padding: '1.75rem',
                transition: 'all 0.3s cubic-bezier(0.4, 0, 0.2, 1)',
                cursor: 'default',
                position: 'relative',
                overflow: 'hidden',
                boxShadow: theme.mode === 'dark'
                    ? '0 4px 20px rgba(0,0,0,0.2)'
                    : '0 4px 20px rgba(0,0,0,0.05)'
            }}
            onMouseEnter={(e) => {
                e.currentTarget.style.transform = 'scale(1.02)';
                e.currentTarget.style.boxShadow = theme.mode === 'dark'
                    ? '0 12px 30px rgba(0,0,0,0.3)'
                    : '0 12px 30px rgba(0,0,0,0.1)';
            }}
            onMouseLeave={(e) => {
                e.currentTarget.style.transform = 'scale(1)';
                e.currentTarget.style.boxShadow = theme.mode === 'dark'
                    ? '0 4px 20px rgba(0,0,0,0.2)'
                    : '0 4px 20px rgba(0,0,0,0.05)';
            }}
        >
            <div style={{
                position: 'absolute',
                top: '-10px',
                right: '-10px',
                fontSize: '5rem',
                opacity: 0.05,
                pointerEvents: 'none',
                filter: 'grayscale(100%)'
            }}>
                {icon}
            </div>

            <div style={{ position: 'relative', zIndex: 1 }}>
                <div style={{
                    color: theme.colors.textSecondary,
                    fontSize: '0.9rem',
                    marginBottom: '0.5rem',
                    fontWeight: 600,
                    display: 'flex',
                    alignItems: 'center',
                    gap: '0.5rem',
                    textTransform: 'uppercase',
                    letterSpacing: '0.05em'
                }}>
                    {label}
                </div>
                <div style={{
                    fontSize: '2rem',
                    fontWeight: 700,
                    color,
                    letterSpacing: '-0.03em'
                }}>
                    {value}
                </div>
            </div>
        </div>
    );
};

const formatSignalName = (key: string): string => {
    const names: { [key: string]: string } = {
        'kdj_buy': 'KDJ 金叉买入',
        'kdj_sell': 'KDJ 死叉卖出',
        'bbi_buy': 'BBI 突破买入',
        'bbi_sell': 'BBI 跌破卖出',
        'macd_buy': 'MACD 金叉买入',
        'macd_sell': 'MACD 死叉卖出',
        'zhixing_buy': '知行趋势买入',
        'zhixing_sell': '知行趋势卖出'
    };
    return names[key] || key;
};

export default Dashboard;
