import React from 'react';
import { useTheme } from '../ThemeContext';
import KLineChart from './KLineChart';

interface DashboardProps {
    analysis: any;
    history: any[];
    loading: boolean;
}

const Dashboard: React.FC<DashboardProps> = ({ analysis, history, loading }) => {
    const { theme } = useTheme();
    console.log('✅ Dashboard rendering');

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

    if (!analysis) return null;

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
                    分析报告
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

            {/* Signals */}
            {analysis.signals && Object.keys(analysis.signals).length > 0 && (
                <div style={{
                    background: theme.colors.bgSecondary,
                    borderRadius: '24px',
                    padding: '2rem',
                    marginBottom: '2.5rem',
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
                        🚦 交易信号
                    </h3>
                    <div style={{
                        display: 'flex',
                        flexWrap: 'wrap',
                        gap: '1rem'
                    }}>
                        {Object.entries(analysis.signals)
                            .filter(([_, value]) => value)
                            .map(([key, _]) => (
                                <div
                                    key={key}
                                    style={{
                                        padding: '0.75rem 1.25rem',
                                        borderRadius: '16px',
                                        background: key.includes('buy')
                                            ? `${theme.colors.success}15`
                                            : `${theme.colors.error}15`,
                                        color: key.includes('buy') ? theme.colors.success : theme.colors.error,
                                        fontSize: '0.95rem',
                                        fontWeight: 600,
                                        display: 'flex',
                                        alignItems: 'center',
                                        gap: '0.5rem',
                                        transition: 'all 0.2s ease',
                                        border: 'none'
                                    }}
                                >
                                    <span>{key.includes('buy') ? '🟢' : '🔴'}</span>
                                    {formatSignalName(key)}
                                </div>
                            ))
                        }
                    </div>
                </div>
            )}

            {/* K线图表 */}
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
