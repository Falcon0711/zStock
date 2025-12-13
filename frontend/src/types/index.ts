// ===========================================
// Type Definitions
// A股智能分析系统类型定义
// ===========================================

// ===== Theme Types =====
export type ThemeMode = 'dark' | 'light';

export interface ThemeColors {
  bgPrimary: string;
  bgSecondary: string;
  bgTertiary: string;
  textPrimary: string;
  textSecondary: string;
  textTertiary: string;
  accent: string;
  accentHover: string;
  success: string;
  error: string;
  warning: string;
  border: string;
  borderHover: string;
}

export interface Theme {
  mode: ThemeMode;
  colors: ThemeColors;
}

export interface ThemeContextType {
  theme: Theme;
  toggleTheme: () => void;
}

// ===== Stock Types =====
export interface StockQuote {
  code: string;
  name: string;
  price: number;
  change_pct: number;
  time?: string;
}

export interface StockGroupsData {
  favorites: StockQuote[];
  holdings: StockQuote[];
  watching: StockQuote[];
}

export type StockGroupKey = keyof StockGroupsData;

// ===== API Types =====
export interface StockInfo {
  code: string;
  name: string;
  market_cap: string;
}

export interface AnalysisResult {
  latest_price: number;
  score: number;
  kdj_k: number;
  kdj_j?: number;
  bbi_value: number;
  signals: Record<string, boolean>;
}

export interface ChartData {
  time: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
  ma5?: number;
  ma10?: number;
  ma20?: number;
  ma30?: number;
  ma60?: number;
  bbi?: number | null;
  zhixing_trend?: number | null;
  zhixing_multi?: number | null;
  kdj_j?: number | null;
  // MACD 数据
  macd?: number | null;
  macd_signal?: number | null;
  macd_hist?: number | null;
  // 买卖信号
  signal_buy?: boolean;
  signal_sell?: boolean;
}

export interface IndexData {
  code: string;
  name: string;
  latest_price: number;
  change_pct: number;
  data: { time: string; value: number }[];
}

export interface FullStockData {
  analysis: AnalysisResult;
  history: ChartData[];
}

export interface StockSuggestion {
  code: string;
  name: string;
}

// ===== Intraday Types =====
export interface IntradayData {
  time: string;
  price: number;
  avg: number;
  volume: number;
}

export interface IntradayResponse {
  code: string;
  name: string;
  now: number;
  open: number;
  close: number;
  high: number;
  low: number;
  change_pct: number;
  volume: number;
  data: IntradayData[];
  date: string;
  update_time: string;
}

// ===== Ticker Types =====
export interface TickerData {
  code: string;
  name: string;
  price: number;
  change: number;
  change_pct: number;
  volume: string;
  time: string;
}

export interface TickerResponse {
  data: TickerData[];
  update_time: string;
}

// ===== Component Props Types =====
export interface MetricCardProps {
  icon: string;
  label: string;
  value: string;
  color: string;
}

export interface TabButtonProps {
  active: boolean;
  onClick: () => void;
  children: React.ReactNode;
}

export interface CardProps {
  children: React.ReactNode;
  className?: string;
  hover?: boolean;
  glass?: boolean;
  onClick?: () => void;
}

// ===== Hover Data (for Charts) =====
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
  changePercent: number;
  x: number;
  y: number;
  priceY: number;
}
