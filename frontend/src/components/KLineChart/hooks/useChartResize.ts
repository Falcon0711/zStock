import { useEffect, useRef } from 'react';
import type { IChartApi } from 'lightweight-charts';

/**
 * Hook to handle chart resize using ResizeObserver.
 * Automatically updates chart width when container size changes.
 */
export function useChartResize(
    containerRef: React.RefObject<HTMLDivElement>,
    chartRef: React.RefObject<IChartApi | null>
) {
    const resizeObserverRef = useRef<ResizeObserver | null>(null);

    useEffect(() => {
        const container = containerRef.current;
        const chart = chartRef.current;

        if (!container || !chart) return;

        // ResizeObserver 持续监听容器尺寸变化
        resizeObserverRef.current = new ResizeObserver(() => {
            if (!containerRef.current) return;
            chart.applyOptions({ width: containerRef.current.clientWidth });
        });
        resizeObserverRef.current.observe(container);

        // 首帧 rAF 补偿，确保初始尺寸正确
        requestAnimationFrame(() => {
            if (!containerRef.current) return;
            chart.applyOptions({ width: containerRef.current.clientWidth });
        });

        return () => {
            resizeObserverRef.current?.disconnect();
        };
    }, [containerRef, chartRef]);
}
