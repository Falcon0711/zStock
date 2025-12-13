import { useEffect, useRef, useState, useCallback, forwardRef, useImperativeHandle } from 'react';
import { createChart, ColorType } from 'lightweight-charts';
import type { IChartApi, ISeriesApi, SeriesMarker, Time } from 'lightweight-charts';

// ===== 类型定义 =====
interface ChartData {
    time: string;
    open: number;
    high: number;
    low: number;
    close: number;
    volume: number;
    bbi?: number | null;
    zhixing_trend?: number | null;
    zhixing_multi?: number | null;
    kdj_j?: number | null;
    macd?: number | null;
    macd_signal?: number | null;
    macd_hist?: number | null;
    signal_buy?: boolean;
    signal_sell?: boolean;
}

interface KLineChartProps {
    data: ChartData[];
    theme: any;
    stockCode?: string;
    stockName?: string;
}

interface HoverData {
    time: string;
    open: number;
    high: number;
    low: number;
    close: number;
    volume: number;
    bbi: number | null;
    zhixing_trend: number | null;
    zhixing_multi: number | null;
    kdj_j: number | null;
    macd: number | null;
    macd_signal: number | null;
    macd_hist: number | null;
    changePercent: number;
    x: number;
    y: number;
    priceY: number;
}

// 趋势线数据类型
interface TrendLine {
    id: string;
    startTime: string;
    startPrice: number;
    endTime: string;
    endPrice: number;
}

// 暴露给父组件的方法
export interface KLineChartHandle {
    takeScreenshot: () => void;
}

// ===== 主组件 =====
const KLineChart = forwardRef<KLineChartHandle, KLineChartProps>(({ data, theme, stockCode }, ref) => {
    // DOM 引用
    const mainChartRef = useRef<HTMLDivElement>(null);
    const containerRef = useRef<HTMLDivElement>(null);

    // 图表实例引用
    const mainChartInstance = useRef<IChartApi | null>(null);
    const candlestickSeriesRef = useRef<ISeriesApi<'Candlestick'> | null>(null);

    // 状态
    const [hoverData, setHoverData] = useState<HoverData | null>(null);
    const dataMap = useRef<Map<string, ChartData>>(new Map());

    // 画线工具状态
    const [isDrawingMode, setIsDrawingMode] = useState(false);
    const [trendLines, setTrendLines] = useState<TrendLine[]>([]);
    const [_drawingStart, setDrawingStart] = useState<{ time: string, price: number } | null>(null);
    // 保留 setDrawingStart 用于未来画线功能
    void _drawingStart; void setDrawingStart;

    // 数据映射
    useEffect(() => {
        dataMap.current.clear();
        data.forEach(d => dataMap.current.set(d.time, d));
    }, [data]);

    // 加载保存的趋势线
    useEffect(() => {
        if (stockCode) {
            const saved = localStorage.getItem(`trendlines_${stockCode}`);
            if (saved) {
                setTrendLines(JSON.parse(saved));
            }
        }
    }, [stockCode]);

    // 保存趋势线
    useEffect(() => {
        if (stockCode && trendLines.length > 0) {
            localStorage.setItem(`trendlines_${stockCode}`, JSON.stringify(trendLines));
        }
    }, [trendLines, stockCode]);

    // 格式化成交量
    const formatVolume = (vol: number) => {
        if (vol >= 100000000) return (vol / 100000000).toFixed(2) + '亿';
        if (vol >= 10000) return (vol / 10000).toFixed(2) + '万';
        return vol.toString();
    };

    // 截图功能
    const takeScreenshot = useCallback(() => {
        if (!containerRef.current) return;

        // 使用 html2canvas 或原生方法
        const mainCanvas = mainChartRef.current?.querySelector('canvas');

        if (!mainCanvas) return;

        // 创建 canvas
        const width = mainCanvas.width;
        const height = mainCanvas.height;

        const mergedCanvas = document.createElement('canvas');
        mergedCanvas.width = width;
        mergedCanvas.height = height;
        const ctx = mergedCanvas.getContext('2d');

        if (ctx) {
            ctx.drawImage(mainCanvas, 0, 0);

            // 下载
            const link = document.createElement('a');
            link.download = `${stockCode || 'chart'}_${new Date().toISOString().slice(0, 10)}.png`;
            link.href = mergedCanvas.toDataURL('image/png');
            link.click();
        }
    }, [stockCode]);

    // 暴露方法给父组件
    useImperativeHandle(ref, () => ({
        takeScreenshot
    }), [takeScreenshot]);

    // 主图表创建
    useEffect(() => {
        if (!mainChartRef.current || !data || data.length === 0) return;

        const chartBgColor = theme.mode === 'dark' ? '#1C1C1E' : '#FFFFFF';
        const textColor = theme.colors.textSecondary;
        const borderColor = theme.mode === 'dark' ? 'rgba(255, 255, 255, 0.1)' : 'rgba(0, 0, 0, 0.1)';

        // ====== 创建主图表 (K线 + 技术指标线) ======
        const mainChart = createChart(mainChartRef.current, {
            layout: {
                background: { type: ColorType.Solid, color: chartBgColor },
                textColor: textColor,
            },
            width: mainChartRef.current.clientWidth,
            height: 450,
            grid: {
                vertLines: { visible: false },
                horzLines: { color: borderColor },
            },
            crosshair: {
                mode: 1,
                vertLine: {
                    visible: true,
                    labelBackgroundColor: '#4A4A4A',
                    color: theme.mode === 'dark' ? 'rgba(255, 255, 255, 0.3)' : 'rgba(0, 0, 0, 0.2)',
                    style: 2,
                    width: 1,
                    labelVisible: true,
                },
                horzLine: {
                    visible: true,
                    labelBackgroundColor: '#4A4A4A',
                    color: theme.mode === 'dark' ? 'rgba(255, 255, 255, 0.3)' : 'rgba(0, 0, 0, 0.2)',
                    style: 2,
                    width: 1,
                    labelVisible: true,
                },
            },
            rightPriceScale: { borderColor },
            timeScale: {
                borderColor,
                visible: true,
                timeVisible: true,
                secondsVisible: false,
                fixLeftEdge: true,
                fixRightEdge: true,
            },
        });
        mainChartInstance.current = mainChart;

        // K线系列
        const candlestickSeries = mainChart.addCandlestickSeries({
            upColor: '#FF3B30',
            downColor: '#34C759',
            borderUpColor: '#FF3B30',
            borderDownColor: '#34C759',
            wickUpColor: '#FF3B30',
            wickDownColor: '#34C759',
            lastValueVisible: false,
            priceLineVisible: false,
        });
        candlestickSeriesRef.current = candlestickSeries;

        candlestickSeries.setData(data.map(d => ({
            time: d.time as Time,
            open: d.open,
            high: d.high,
            low: d.low,
            close: d.close,
        })));

        // 买卖信号标记
        const markers: SeriesMarker<Time>[] = data
            .filter(d => d.signal_buy || d.signal_sell)
            .map(d => ({
                time: d.time as Time,
                position: d.signal_buy ? 'belowBar' : 'aboveBar',
                color: d.signal_buy ? '#FF3B30' : '#34C759',
                shape: d.signal_buy ? 'arrowUp' : 'arrowDown',
                text: d.signal_buy ? '买' : '卖',
            } as SeriesMarker<Time>));

        if (markers.length > 0) {
            candlestickSeries.setMarkers(markers);
        }

        // BBI线
        if (data.some(d => d.bbi != null)) {
            const bbiSeries = mainChart.addLineSeries({
                color: '#8B5CF6',
                lineWidth: 2,
                priceLineVisible: false,
                lastValueVisible: false,
            });
            bbiSeries.setData(data.filter(d => d.bbi != null).map(d => ({ time: d.time as Time, value: d.bbi! })));
        }

        // 知行趋势线
        if (data.some(d => d.zhixing_trend != null)) {
            const trendSeries = mainChart.addLineSeries({
                color: '#FF6B6B',
                lineWidth: 2,
                priceLineVisible: false,
                lastValueVisible: false,
            });
            trendSeries.setData(data.filter(d => d.zhixing_trend != null).map(d => ({ time: d.time as Time, value: d.zhixing_trend! })));
        }

        // 知行多空线
        if (data.some(d => d.zhixing_multi != null)) {
            const multiSeries = mainChart.addLineSeries({
                color: '#FFD93D',
                lineWidth: 2,
                priceLineVisible: false,
                lastValueVisible: false,
            });
            multiSeries.setData(data.filter(d => d.zhixing_multi != null).map(d => ({ time: d.time as Time, value: d.zhixing_multi! })));
        }

        // ====== 在主图中添加成交量柱状图 ======
        const volumeSeries = mainChart.addHistogramSeries({
            priceFormat: { type: 'volume' },
            priceScaleId: 'volume',
            lastValueVisible: false,
        });
        volumeSeries.priceScale().applyOptions({
            scaleMargins: { top: 0.8, bottom: 0 },
            visible: false,
        });
        volumeSeries.setData(data.map((d, i) => ({
            time: d.time as Time,
            value: d.volume,
            color: i > 0 && d.close >= data[i - 1].close ? 'rgba(255, 59, 48, 0.3)' : 'rgba(52, 199, 89, 0.3)',
        })));

        // ====== 十字线同步 ======
        mainChart.subscribeCrosshairMove((param) => {
            if (!param.time || !param.point) {
                setHoverData(null);
                return;
            }

            const timeStr = param.time as string;
            const chartData = dataMap.current.get(timeStr);

            if (chartData && param.point) {
                const changePercent = chartData.open !== 0
                    ? ((chartData.close - chartData.open) / chartData.open) * 100 : 0;
                const priceY = candlestickSeriesRef.current?.priceToCoordinate(chartData.close) ?? param.point.y;

                setHoverData({
                    time: chartData.time,
                    open: chartData.open,
                    high: chartData.high,
                    low: chartData.low,
                    close: chartData.close,
                    volume: chartData.volume,
                    bbi: chartData.bbi ?? null,
                    zhixing_trend: chartData.zhixing_trend ?? null,
                    zhixing_multi: chartData.zhixing_multi ?? null,
                    kdj_j: chartData.kdj_j ?? null,
                    macd: chartData.macd ?? null,
                    macd_signal: chartData.macd_signal ?? null,
                    macd_hist: chartData.macd_hist ?? null,
                    changePercent,
                    x: param.point.x,
                    y: param.point.y,
                    priceY: priceY,
                });
            }
        });

        // 设置初始可见范围
        mainChart.timeScale().fitContent();
        if (data.length > 60) {
            const visibleData = data.slice(-60);
            mainChart.timeScale().setVisibleRange({
                from: visibleData[0].time as Time,
                to: visibleData[visibleData.length - 1].time as Time,
            });
        }

        // 窗口大小调整处理
        const handleResize = () => {
            if (mainChartRef.current) mainChart.applyOptions({ width: mainChartRef.current.clientWidth });
        };

        window.addEventListener('resize', handleResize);

        return () => {
            window.removeEventListener('resize', handleResize);
            mainChart.remove();
        };
    }, [data, theme]);

    const latestData = data.length > 0 ? data[data.length - 1] : null;
    const currentData = hoverData || latestData;

    // 清除趋势线
    const clearTrendLines = () => {
        setTrendLines([]);
        if (stockCode) {
            localStorage.removeItem(`trendlines_${stockCode}`);
        }
    };

    return (
        <div ref={containerRef} style={{ position: 'relative' }}>
            {/* 工具栏 */}
            <div style={{
                display: 'flex',
                gap: '0.5rem',
                marginBottom: '0.75rem',
                alignItems: 'center',
                flexWrap: 'wrap',
            }}>
                {/* 图例 */}
                <div style={{ display: 'flex', gap: '1rem', flex: 1, flexWrap: 'wrap', fontSize: '0.8rem' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.3rem' }}>
                        <div style={{ width: '16px', height: '3px', background: '#8B5CF6', borderRadius: '2px' }} />
                        <span style={{ color: '#8B5CF6' }}>BBI{currentData?.bbi != null ? `: ${currentData.bbi.toFixed(2)}` : ''}</span>
                    </div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.3rem' }}>
                        <div style={{ width: '16px', height: '3px', background: '#FF6B6B', borderRadius: '2px' }} />
                        <span style={{ color: '#FF6B6B' }}>趋势{currentData?.zhixing_trend != null ? `: ${currentData.zhixing_trend.toFixed(2)}` : ''}</span>
                    </div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.3rem' }}>
                        <div style={{ width: '16px', height: '3px', background: '#FFD93D', borderRadius: '2px' }} />
                        <span style={{ color: '#FFD93D' }}>多空{currentData?.zhixing_multi != null ? `: ${currentData.zhixing_multi.toFixed(2)}` : ''}</span>
                    </div>
                </div>

                {/* 工具按钮 */}
                <div style={{ display: 'flex', gap: '0.5rem' }}>
                    <button
                        onClick={() => setIsDrawingMode(!isDrawingMode)}
                        style={{
                            padding: '0.4rem 0.8rem',
                            borderRadius: '8px',
                            border: 'none',
                            background: isDrawingMode ? theme.colors.accent : theme.colors.bgTertiary,
                            color: isDrawingMode ? '#fff' : theme.colors.textPrimary,
                            cursor: 'pointer',
                            fontSize: '0.8rem',
                            transition: 'all 0.2s',
                        }}
                    >
                        ✏️ 画线
                    </button>
                    {trendLines.length > 0 && (
                        <button
                            onClick={clearTrendLines}
                            style={{
                                padding: '0.4rem 0.8rem',
                                borderRadius: '8px',
                                border: 'none',
                                background: theme.colors.bgTertiary,
                                color: theme.colors.error,
                                cursor: 'pointer',
                                fontSize: '0.8rem',
                            }}
                        >
                            🗑️ 清除
                        </button>
                    )}
                    <button
                        onClick={takeScreenshot}
                        style={{
                            padding: '0.4rem 0.8rem',
                            borderRadius: '8px',
                            border: 'none',
                            background: theme.colors.bgTertiary,
                            color: theme.colors.textPrimary,
                            cursor: 'pointer',
                            fontSize: '0.8rem',
                        }}
                    >
                        📸 截图
                    </button>
                </div>
            </div>

            {/* 主图表区域 */}
            <div style={{
                borderRadius: '12px',
                overflow: 'hidden',
                boxShadow: theme.mode === 'dark' ? '0 2px 10px rgba(0,0,0,0.3)' : '0 2px 10px rgba(0,0,0,0.08)',
            }}>
                {/* K线主图（含成交量） */}
                <div ref={mainChartRef} style={{ position: 'relative' }} />
            </div>

            {/* 图表信息 */}
            <div style={{
                marginTop: '0.5rem',
                fontSize: '0.75rem',
                color: theme.colors.textTertiary,
                display: 'flex',
                justifyContent: 'space-between',
            }}>
                <span>🔴 红涨 🟢 绿跌 | 共 {data.length} 个交易日</span>
                <span>↑买入信号 ↓卖出信号</span>
            </div>

            {/* 悬浮提示框 */}
            {hoverData && (() => {
                const chartWidth = mainChartRef.current?.clientWidth || 800;
                const isRightHalf = hoverData.x > chartWidth / 2;
                const isUp = hoverData.close >= hoverData.open;
                const priceColor = isUp ? '#FF3B30' : '#34C759';

                return (
                    <div style={{
                        position: 'absolute',
                        left: isRightHalf ? hoverData.x - 150 : hoverData.x + 20,
                        top: Math.max(hoverData.y, 10),
                        background: theme.mode === 'dark' ? 'rgba(28, 28, 30, 0.95)' : 'rgba(255, 255, 255, 0.95)',
                        borderRadius: '12px',
                        padding: '0.75rem 1rem',
                        boxShadow: theme.mode === 'dark' ? '0 4px 16px rgba(0,0,0,0.5)' : '0 4px 16px rgba(0,0,0,0.15)',
                        zIndex: 100,
                        pointerEvents: 'none',
                        backdropFilter: 'blur(12px)',
                        WebkitBackdropFilter: 'blur(12px)',
                        fontSize: '0.85rem',
                        lineHeight: 1.6,
                        border: theme.mode === 'dark' ? '1px solid rgba(255,255,255,0.1)' : '1px solid rgba(0,0,0,0.05)',
                    }}>
                        <div style={{ fontWeight: 600, color: theme.colors.textPrimary, marginBottom: '0.25rem' }}>{hoverData.time}</div>
                        <div style={{ color: priceColor }}>开盘: {hoverData.open.toFixed(2)}</div>
                        <div style={{ color: priceColor }}>最高: {hoverData.high.toFixed(2)}</div>
                        <div style={{ color: priceColor }}>最低: {hoverData.low.toFixed(2)}</div>
                        <div style={{ color: priceColor }}>收盘: {hoverData.close.toFixed(2)}</div>
                        <div style={{ color: theme.colors.textPrimary }}>成交量: {formatVolume(hoverData.volume)}</div>
                    </div>
                );
            })()}

            {/* 画线模式提示 */}
            {isDrawingMode && (
                <div style={{
                    position: 'absolute',
                    top: '50%',
                    left: '50%',
                    transform: 'translate(-50%, -50%)',
                    background: 'rgba(0,0,0,0.7)',
                    color: '#fff',
                    padding: '1rem 2rem',
                    borderRadius: '12px',
                    fontSize: '0.9rem',
                    pointerEvents: 'none',
                    zIndex: 200,
                }}>
                    📏 画线模式已开启 - 点击图表两点绘制趋势线
                </div>
            )}
        </div>
    );
});

KLineChart.displayName = 'KLineChart';

export default KLineChart;
