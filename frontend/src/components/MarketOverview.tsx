import React from 'react';
import { useTheme } from '../ThemeContext';

interface MarketOverviewProps {
    indices: any[];
    loading: boolean;
}

const MarketOverview: React.FC<MarketOverviewProps> = ({ indices, loading }) => {
    const { theme } = useTheme();
    console.log('✅ MarketOverview rendering, indices count:', indices.length);

    if (loading) {
        return (
            <div style={{
                padding: '4rem 2rem',
                textAlign: 'center',
                color: theme.colors.textSecondary
            }}>
                <div style={{
                    fontSize: '2rem',
                    marginBottom: '1rem',
                    animation: 'pulse 1.5s ease-in-out infinite'
                }}>
                    ⏳
                </div>
                <div style={{ fontSize: '1.1rem' }}>加载市场数据中...</div>
                <style>{`
                    @keyframes pulse {
                        0%, 100% { opacity: 0.6; transform: scale(1); }
                        50% { opacity: 1; transform: scale(1.1); }
                    }
                `}</style>
            </div>
        );
    }

    if (!indices || indices.length === 0) {
        return (
            <div style={{
                padding: '4rem 2rem',
                maxWidth: '800px',
                margin: '0 auto',
                textAlign: 'center'
            }}>
                <div style={{
                    background: theme.colors.bgSecondary,
                    border: `1px solid ${theme.colors.border}`,
                    borderRadius: '16px',
                    padding: '3rem 2rem',
                    transition: 'all 0.3s ease'
                }}>
                    <div style={{ fontSize: '3rem', marginBottom: '1rem' }}>🌏</div>
                    <h2 style={{
                        color: theme.colors.textPrimary,
                        fontSize: '1.5rem',
                        fontWeight: 600,
                        marginBottom: '0.75rem'
                    }}>
                        市场概览
                    </h2>
                    <p style={{
                        color: theme.colors.textSecondary,
                        fontSize: '1rem',
                        margin: 0
                    }}>
                        暂无市场数据，请在上方输入股票代码开始分析
                    </p>
                </div>
            </div>
        );
    }

    return (
        <div style={{
            padding: '2.5rem',
            maxWidth: '1400px',
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
                    市场概览
                </h2>
            </div>

            <div style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))',
                gap: '1.5rem'
            }}>
                {indices.map((index, i) => {
                    const isUp = index.change_pct >= 0;
                    return (
                        <div
                            key={index.code}
                            style={{
                                background: theme.colors.bgSecondary,
                                borderRadius: '20px',
                                padding: '1.75rem',
                                position: 'relative',
                                transition: 'all 0.3s cubic-bezier(0.4, 0, 0.2, 1)',
                                cursor: 'pointer',
                                boxShadow: theme.mode === 'dark'
                                    ? '0 4px 20px rgba(0,0,0,0.2)'
                                    : '0 4px 20px rgba(0,0,0,0.05)',
                                animation: `slideUp 0.5s ease-out ${i * 0.1}s backwards`
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
                                display: 'flex',
                                justifyContent: 'space-between',
                                alignItems: 'flex-start',
                                marginBottom: '1.5rem'
                            }}>
                                <div>
                                    <div style={{
                                        color: theme.colors.textSecondary,
                                        fontSize: '0.9rem',
                                        fontWeight: 600,
                                        marginBottom: '0.25rem',
                                        textTransform: 'uppercase',
                                        letterSpacing: '0.05em'
                                    }}>
                                        {index.name}
                                    </div>
                                    <div style={{
                                        fontSize: '2.2rem',
                                        fontWeight: 700,
                                        color: theme.colors.textPrimary,
                                        letterSpacing: '-0.03em'
                                    }}>
                                        {index.latest_price.toFixed(2)}
                                    </div>
                                </div>

                                <div style={{
                                    background: isUp ? theme.colors.success : theme.colors.error,
                                    color: '#fff',
                                    padding: '0.4rem 0.8rem',
                                    borderRadius: '20px',
                                    fontSize: '0.9rem',
                                    fontWeight: 600,
                                    display: 'flex',
                                    alignItems: 'center',
                                    gap: '0.25rem',
                                    boxShadow: `0 4px 10px ${isUp ? theme.colors.success : theme.colors.error}40`
                                }}>
                                    <span>{isUp ? '↑' : '↓'}</span>
                                    {Math.abs(index.change_pct).toFixed(2)}%
                                </div>
                            </div>

                            {/* Trend Line (Simulated) */}
                            <div style={{
                                height: '60px',
                                width: '100%',
                                display: 'flex',
                                alignItems: 'flex-end',
                                gap: '4px',
                                opacity: 0.5
                            }}>
                                {Array.from({ length: 20 }).map((_, idx) => (
                                    <div key={idx} style={{
                                        flex: 1,
                                        background: isUp ? theme.colors.success : theme.colors.error,
                                        height: `${30 + Math.random() * 70}%`,
                                        borderRadius: '2px'
                                    }} />
                                ))}
                            </div>
                        </div>
                    );
                })}
            </div>

            <style>{`
                @keyframes fadeIn {
                    from { opacity: 0; }
                    to { opacity: 1; }
                }
                @keyframes slideUp {
                    from {
                        opacity: 0;
                        transform: translateY(20px);
                    }
                    to {
                        opacity: 1;
                        transform: translateY(0);
                    }
                }
            `}</style>
        </div>
    );
};

export default MarketOverview;
