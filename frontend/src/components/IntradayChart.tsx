import React, { useEffect, useRef } from 'react';
import { createChart, ColorType } from 'lightweight-charts';

interface IntradayData {
    time: string;      // 时间 HH:mm
    price: number;     // 当前价
    avg: number;       // 均价
    volume: number;    // 成交量
}

interface IntradayChartProps {
    data: IntradayData[];
    theme: any;
    stockInfo: {
        name: string;
        now: number;
        open: number;
        close: number;
        high: number;
        low: number;
        change_pct: number;
        date?: string;  // 🆕 数据日期
    };
}

const IntradayChart: React.FC<IntradayChartProps> = ({ data, theme, stockInfo }) => {
    const chartContainerRef = useRef<HTMLDivElement>(null);

    useEffect(() => {
        if (!chartContainerRef.current || !data || data.length === 0) return;

        const handleResize = () => {
            chart.applyOptions({ width: chartContainerRef.current!.clientWidth });
        };

        // 创建图表
        const chart = createChart(chartContainerRef.current, {
            layout: {
                background: { type: ColorType.Solid, color: theme.mode === 'dark' ? '#1C1C1E' : '#FFFFFF' },
                textColor: theme.colors.textSecondary,
            },
            width: chartContainerRef.current.clientWidth,
            height: 400,
            grid: {
                vertLines: {
                    color: theme.mode === 'dark' ? 'rgba(255, 255, 255, 0.05)' : 'rgba(0, 0, 0, 0.05)',
                },
                horzLines: {
                    color: theme.mode === 'dark' ? 'rgba(255, 255, 255, 0.05)' : 'rgba(0, 0, 0, 0.05)',
                },
            },
            crosshair: {
                mode: 1, // 十字线模式
            },
            rightPriceScale: {
                borderColor: theme.mode === 'dark' ? 'rgba(255, 255, 255, 0.1)' : 'rgba(0, 0, 0, 0.1)',
            },
            timeScale: {
                borderColor: theme.mode === 'dark' ? 'rgba(255, 255, 255, 0.1)' : 'rgba(0, 0, 0, 0.1)',
                timeVisible: true,
                secondsVisible: false,
                tickMarkFormatter: (time: any) => {
                    // 格式化时间显示
                    return time;
                },
            },
        });

        // 价格线（蓝色）
        const priceSeries = chart.addLineSeries({
            color: '#007AFF',
            lineWidth: 2,
            priceLineVisible: true,
            lastValueVisible: true,
        });

        // 均价线（黄色）
        const avgSeries = chart.addLineSeries({
            color: '#FFD93D',
            lineWidth: 2,
            priceLineVisible: false,
            lastValueVisible: false,
        });

        // 格式化数据为时间戳
        const priceData = data.map((d, i) => ({
            time: i as any, // 使用索引作为时间
            value: d.price,
        }));

        const avgData = data.map((d, i) => ({
            time: i as any,
            value: d.avg,
        }));

        priceSeries.setData(priceData);
        avgSeries.setData(avgData);

        // 添加昨收线
        priceSeries.createPriceLine({
            price: stockInfo.close,
            color: theme.mode === 'dark' ? 'rgba(255, 255, 255, 0.3)' : 'rgba(0, 0, 0, 0.2)',
            lineWidth: 1 as const,
            lineStyle: 2,
            axisLabelVisible: true,
            title: '昨收',
        });

        chart.timeScale().fitContent();

        window.addEventListener('resize', handleResize);

        return () => {
            window.removeEventListener('resize', handleResize);
            chart.remove();
        };
    }, [data, theme, stockInfo]);

    // 计算涨跌颜色
    const priceColor = stockInfo.change_pct >= 0 ? '#FF3B30' : '#34C759';
    const changeSymbol = stockInfo.change_pct >= 0 ? '+' : '';

    return (
        <div>
            {/* 顶部信息栏 */}
            <div style={{
                display: 'flex',
                gap: '1.5rem',
                marginBottom: '1rem',
                padding: '0.75rem 1rem',
                background: theme.mode === 'dark' ? 'rgba(255, 255, 255, 0.05)' : 'rgba(0, 0, 0, 0.02)',
                borderRadius: '8px',
                fontSize: '0.9rem',
                flexWrap: 'wrap',
                alignItems: 'center'
            }}>
                <div>
                    <span style={{ color: '#FFD93D' }}>均: </span>
                    <span style={{ color: theme.colors.textPrimary, fontWeight: 500 }}>
                        {data.length > 0 ? data[data.length - 1].avg.toFixed(2) : '-'}
                    </span>
                </div>
                <div>
                    <span style={{ color: theme.colors.textSecondary }}>新: </span>
                    <span style={{ color: priceColor, fontWeight: 600 }}>
                        {stockInfo.now.toFixed(2)}
                    </span>
                    <span style={{ color: priceColor, marginLeft: '0.5rem' }}>
                        {changeSymbol}{stockInfo.change_pct.toFixed(2)}%
                    </span>
                </div>
                <div>
                    <span style={{ color: theme.colors.textSecondary }}>高: </span>
                    <span style={{ color: '#FF3B30' }}>{stockInfo.high.toFixed(2)}</span>
                </div>
                <div>
                    <span style={{ color: theme.colors.textSecondary }}>低: </span>
                    <span style={{ color: '#34C759' }}>{stockInfo.low.toFixed(2)}</span>
                </div>
                <div style={{ marginLeft: 'auto' }}>
                    <span style={{ color: theme.colors.textTertiary, fontSize: '0.8rem' }}>
                        {stockInfo.date && `${stockInfo.date} | `}共 {data.length} 个数据点
                    </span>
                </div>
            </div>

            {/* 图例 */}
            <div style={{
                display: 'flex',
                gap: '1.5rem',
                marginBottom: '0.5rem',
                fontSize: '0.85rem',
                alignItems: 'center'
            }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                    <div style={{
                        width: '20px',
                        height: '3px',
                        background: '#007AFF',
                        borderRadius: '2px'
                    }} />
                    <span style={{ color: theme.colors.textSecondary }}>分时价格</span>
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                    <div style={{
                        width: '20px',
                        height: '3px',
                        background: '#FFD93D',
                        borderRadius: '2px'
                    }} />
                    <span style={{ color: theme.colors.textSecondary }}>均价线</span>
                </div>
            </div>

            {/* 图表容器 */}
            <div
                ref={chartContainerRef}
                style={{
                    borderRadius: '12px',
                    overflow: 'hidden',
                    boxShadow: theme.mode === 'dark'
                        ? '0 2px 10px rgba(0,0,0,0.3)'
                        : '0 2px 10px rgba(0,0,0,0.08)',
                }}
            />

            {/* 非交易时段提示 */}
            {data.length === 0 && (
                <div style={{
                    padding: '3rem',
                    textAlign: 'center',
                    color: theme.colors.textTertiary,
                    fontSize: '0.9rem'
                }}>
                    <div style={{ fontSize: '2rem', marginBottom: '1rem' }}>📈</div>
                    <div>当前非交易时段或无分时数据</div>
                    <div style={{ marginTop: '0.5rem', fontSize: '0.8rem' }}>
                        交易时间: 周一至周五 09:30-11:30, 13:00-15:00
                    </div>
                </div>
            )}
        </div>
    );
};

export default IntradayChart;
