import React, { useEffect, useRef } from 'react';
import { createChart, ColorType } from 'lightweight-charts';

interface ChartData {
    time: string;
    open: number;
    high: number;
    low: number;
    close: number;
    volume: number;
    ma5?: number | null;
    ma10?: number | null;
    ma20?: number | null;
}

interface KLineChartProps {
    data: ChartData[];
    theme: any;
}

const KLineChart: React.FC<KLineChartProps> = ({ data, theme }) => {
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
            height: 500,
            grid: {
                vertLines: {
                    color: theme.mode === 'dark' ? 'rgba(255, 255, 255, 0.05)' : 'rgba(0, 0, 0, 0.05)',
                },
                horzLines: {
                    color: theme.mode === 'dark' ? 'rgba(255, 255, 255, 0.05)' : 'rgba(0, 0, 0, 0.05)',
                },
            },
            crosshair: {
                mode: 0,
            },
            rightPriceScale: {
                borderColor: theme.mode === 'dark' ? 'rgba(255, 255, 255, 0.1)' : 'rgba(0, 0, 0, 0.1)',
            },
            timeScale: {
                borderColor: theme.mode === 'dark' ? 'rgba(255, 255, 255, 0.1)' : 'rgba(0, 0, 0, 0.1)',
                timeVisible: true,
                secondsVisible: false,
            },
        });

        // 添加K线图
        const candlestickSeries = chart.addCandlestickSeries({
            upColor: '#FF3B30',
            downColor: '#34C759',
            borderUpColor: '#FF3B30',
            borderDownColor: '#34C759',
            wickUpColor: '#FF3B30',
            wickDownColor: '#34C759',
        });

        const candleData = data.map(d => ({
            time: d.time,
            open: d.open,
            high: d.high,
            low: d.low,
            close: d.close,
        }));

        candlestickSeries.setData(candleData);

        // 添加MA5均线
        if (data.some(d => d.ma5 !== null && d.ma5 !== undefined)) {
            const ma5Series = chart.addLineSeries({
                color: '#FF6B6B',
                lineWidth: 2,
            });
            const ma5Data = data
                .filter(d => d.ma5 !== null && d.ma5 !== undefined)
                .map(d => ({
                    time: d.time,
                    value: d.ma5!,
                }));
            ma5Series.setData(ma5Data);
        }

        // 添加MA10均线
        if (data.some(d => d.ma10 !== null && d.ma10 !== undefined)) {
            const ma10Series = chart.addLineSeries({
                color: '#4ECDC4',
                lineWidth: 2,
            });
            const ma10Data = data
                .filter(d => d.ma10 !== null && d.ma10 !== undefined)
                .map(d => ({
                    time: d.time,
                    value: d.ma10!,
                }));
            ma10Series.setData(ma10Data);
        }

        // 添加MA20均线
        if (data.some(d => d.ma20 !== null && d.ma20 !== undefined)) {
            const ma20Series = chart.addLineSeries({
                color: '#FFD93D',
                lineWidth: 2,
            });
            const ma20Data = data
                .filter(d => d.ma20 !== null && d.ma20 !== undefined)
                .map(d => ({
                    time: d.time,
                    value: d.ma20!,
                }));
            ma20Series.setData(ma20Data);
        }

        chart.timeScale().fitContent();

        // 设置默认显示最近60个交易日
        if (data.length > 60) {
            const visibleData = data.slice(-60);
            const fromTime = visibleData[0].time;
            const toTime = visibleData[visibleData.length - 1].time;
            chart.timeScale().setVisibleRange({
                from: fromTime as any,
                to: toTime as any,
            });
        }

        window.addEventListener('resize', handleResize);

        return () => {
            window.removeEventListener('resize', handleResize);
            chart.remove();
        };
    }, [data, theme]);

    return (
        <div>
            {/* 图例 */}
            <div style={{
                display: 'flex',
                gap: '1.5rem',
                marginBottom: '1rem',
                fontSize: '0.85rem',
                flexWrap: 'wrap'
            }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                    <div style={{
                        width: '20px',
                        height: '3px',
                        background: '#FF6B6B',
                        borderRadius: '2px'
                    }} />
                    <span style={{ color: theme.colors.textSecondary }}>MA5</span>
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                    <div style={{
                        width: '20px',
                        height: '3px',
                        background: '#4ECDC4',
                        borderRadius: '2px'
                    }} />
                    <span style={{ color: theme.colors.textSecondary }}>MA10</span>
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                    <div style={{
                        width: '20px',
                        height: '3px',
                        background: '#FFD93D',
                        borderRadius: '2px'
                    }} />
                    <span style={{ color: theme.colors.textSecondary }}>MA20</span>
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginLeft: 'auto' }}>
                    <span style={{ color: theme.colors.textTertiary, fontSize: '0.8rem' }}>
                        🔴 红涨 🟢 绿跌 | 共 {data.length} 个交易日 {data.length > 60 && '(默认显示最近60日)'}
                    </span>
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
        </div>
    );
};

export default KLineChart;
