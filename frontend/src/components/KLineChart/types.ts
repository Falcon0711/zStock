import type { Time } from 'lightweight-charts';
import type { Theme } from '../../ThemeContext';

// ===== K线数据类型 =====
export interface ChartData {
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

// ===== 组件 Props =====
export interface KLineChartProps {
    data: ChartData[];
    theme: Theme;
    stockCode?: string;
    stockName?: string;
}

// ===== Hover 数据类型 =====
export interface HoverData {
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

// ===== 趋势线数据类型 =====
export interface TrendLine {
    id: string;
    startTime: string;
    startPrice: number;
    endTime: string;
    endPrice: number;
}

// ===== 暴露给父组件的方法 =====
export interface KLineChartHandle {
    takeScreenshot: () => void;
}

// ===== Re-export Time type for convenience =====
export type { Time };
