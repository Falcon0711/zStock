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

        // 获取数据日期，用于构建时间戳
        const dataDate = stockInfo.date || new Date().toISOString().split('T')[0];

        // 时间字符串转Unix时间戳（秒）- 使用UTC时间（不加时区偏移）
        // 这样 lightweight-charts 会直接显示这个时间
        const timeStringToTimestamp = (timeStr: string): number => {
            const [hours, minutes] = timeStr.split(':').map(Number);
            const [year, month, day] = dataDate.split('-').map(Number);
            // 直接构建UTC时间戳，这样charts会显示我们设置的时间
            const dateObj = new Date(Date.UTC(year, month - 1, day, hours, minutes, 0));
            return Math.floor(dateObj.getTime() / 1000);
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
                mode: 1,
            },
            rightPriceScale: {
                borderColor: theme.mode === 'dark' ? 'rgba(255, 255, 255, 0.1)' : 'rgba(0, 0, 0, 0.1)',
            },
            timeScale: {
                borderColor: theme.mode === 'dark' ? 'rgba(255, 255, 255, 0.1)' : 'rgba(0, 0, 0, 0.1)',
                timeVisible: true,
                secondsVisible: false,
                fixLeftEdge: true,
                fixRightEdge: true,
            },
            localization: {
                timeFormatter: (timestamp: number) => {
                    const date = new Date(timestamp * 1000);
                    const hours = date.getUTCHours().toString().padStart(2, '0');
                    const mins = date.getUTCMinutes().toString().padStart(2, '0');
                    return `${hours}:${mins}`;
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

        // 格式化数据，使用真实时间戳
        const priceData = data.map((d) => ({
            time: timeStringToTimestamp(d.time) as any,
            value: d.price,
        }));

        const avgData = data.map((d) => ({
            time: timeStringToTimestamp(d.time) as any,
            value: d.avg,
        }));

        // 添加边界点来固定X轴范围为整个交易日
        const boundarySeries = chart.addLineSeries({
            color: 'transparent',
            lineWidth: 1,
            priceLineVisible: false,
            lastValueVisible: false,
            visible: false,
        });

        // 边界时间戳：09:30 开盘 和 15:00 收盘
        const openTime = timeStringToTimestamp('09:30');
        const closeTime = timeStringToTimestamp('15:00');
        const boundaryPrice = data.length > 0 ? data[0].price : stockInfo.close;

        boundarySeries.setData([
            { time: openTime as any, value: boundaryPrice },
            { time: closeTime as any, value: boundaryPrice },
        ]);

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

        // 自适应显示完整范围
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
