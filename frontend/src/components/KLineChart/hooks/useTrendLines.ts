import { useEffect, useState } from 'react';
import type { TrendLine } from '../types';

/**
 * Hook to manage trend lines with localStorage persistence.
 */
export function useTrendLines(stockCode?: string) {
    const [trendLines, setTrendLines] = useState<TrendLine[]>([]);

    // 加载保存的趋势线
    useEffect(() => {
        if (stockCode) {
            const saved = localStorage.getItem(`trendlines_${stockCode}`);
            if (saved) {
                try {
                    setTrendLines(JSON.parse(saved));
                } catch {
                    setTrendLines([]);
                }
            } else {
                setTrendLines([]);
            }
        }
    }, [stockCode]);

    // 保存趋势线
    useEffect(() => {
        if (stockCode && trendLines.length > 0) {
            localStorage.setItem(`trendlines_${stockCode}`, JSON.stringify(trendLines));
        }
    }, [trendLines, stockCode]);

    // 清除趋势线
    const clearTrendLines = () => {
        setTrendLines([]);
        if (stockCode) {
            localStorage.removeItem(`trendlines_${stockCode}`);
        }
    };

    return { trendLines, setTrendLines, clearTrendLines };
}
