import axios from 'axios';

const api = axios.create({
    baseURL: '/api',
});

export interface StockInfo {
    code: string;
    name: string;
    market_cap: string;
}

export interface AnalysisResult {
    latest_price: number;
    score: number;
    kdj_k: number;
    bbi_value: number;
    signals: {
        [key: string]: boolean;
    };
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
}

export interface IndexData {
    code: string;
    name: string;
    latest_price: number;
    change_pct: number;
    data: { time: string; value: number }[];
}

// 🆕 合并数据类型
export interface FullStockData {
    analysis: AnalysisResult;
    history: ChartData[];
}

export const fetchHotStocks = async (): Promise<StockInfo[]> => {
    const response = await api.get('/stocks/hot');
    return response.data;
};

export const fetchMarketIndices = async (): Promise<IndexData[]> => {
    const response = await api.get('/market/indices');
    return response.data;
};

export const analyzeStock = async (code: string): Promise<AnalysisResult> => {
    const response = await api.get(`/stock/${code}`);
    return response.data;
};

export const fetchHistory = async (code: string): Promise<ChartData[]> => {
    const response = await api.get(`/stock/${code}/history`);
    return response.data;
};

// 🆕 使用合并端点一次获取分析和历史数据
export const fetchStockFull = async (code: string): Promise<FullStockData> => {
    const response = await api.get(`/stock/${code}/full`);
    return response.data;
};

// 🆕 获取指数历史K线数据
export const fetchIndexHistory = async (code: string): Promise<ChartData[]> => {
    const response = await api.get(`/index/${code}/history`);
    return response.data;
};

export const fetchHotSectors = async (): Promise<any[]> => {
    const response = await api.get('/market/sectors');
    return response.data;
};

export interface StockSuggestion {
    code: string;
    name: string;
}

export const searchStocks = async (query: string, limit: number = 10): Promise<StockSuggestion[]> => {
    if (!query || query.length < 1) {
        return [];
    }
    const response = await api.get(`/stocks/search?q=${encodeURIComponent(query)}&limit=${limit}`);
    return response.data;
};
