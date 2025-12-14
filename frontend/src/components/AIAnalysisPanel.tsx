import React, { memo } from 'react';
import { Bot, Sparkles, AlertCircle, RefreshCw, TrendingUp, TrendingDown } from 'lucide-react';

interface AIAnalysisPanelProps {
    stockName: string | null;
    stockCode: string | null;
    analysis: any | null;
    loading: boolean;
    onRefresh: () => void;
}

/**
 * AIAnalysisPanel - AI 分析右侧面板
 * 参考 AlphaSight AI 设计风格
 */
const AIAnalysisPanel: React.FC<AIAnalysisPanelProps> = memo(({
    stockCode,
    analysis,
    loading,
    onRefresh
}) => {
    // 未选择股票时的占位状态
    if (!stockCode) {
        return (
            <div className="h-full flex flex-col items-center justify-center text-slate-400 dark:text-slate-500 p-8 border-l border-slate-100 dark:border-slate-800 bg-white/50 dark:bg-slate-900/50">
                <Bot size={64} className="mb-4 text-slate-200 dark:text-slate-700" />
                <p className="text-center">选择一支股票以启动 AI 深度分析</p>
            </div>
        );
    }

    // 计算多空评分（从 analysis 中提取）
    const bullishScore = analysis?.score || 50;
    const scoreColor = bullishScore >= 60 ? 'text-up' : bullishScore < 40 ? 'text-down' : 'text-yellow-500';
    const scoreBgColor = bullishScore >= 60 ? 'bg-up' : bullishScore < 40 ? 'bg-down' : 'bg-yellow-400';

    // 提取关键信号
    const getSignals = () => {
        if (!analysis?.signals) return [];
        return Object.entries(analysis.signals)
            .filter(([_, value]) => value)
            .map(([key]) => ({
                key,
                isBuy: key.includes('buy'),
                label: formatSignalName(key)
            }));
    };

    return (
        <aside className="bg-white dark:bg-slate-900 h-full border-l border-slate-200 dark:border-slate-800 flex flex-col shadow-xl z-20 w-full lg:w-[320px]">
            {/* Header */}
            <div className="p-6 border-b border-slate-100 dark:border-slate-800 bg-gradient-to-r from-blue-50 to-indigo-50 dark:from-slate-800 dark:to-indigo-900/20">
                <div className="flex items-center space-x-2 mb-1">
                    <Sparkles className="text-blue-500 animate-pulse" size={18} />
                    <h2 className="text-blue-900 dark:text-blue-100 font-bold">AI 智能分析</h2>
                </div>
                <p className="text-xs text-blue-400 dark:text-blue-500">A股智能分析系统 · 技术面综合评估</p>
            </div>

            {/* Content */}
            <div className="flex-1 overflow-y-auto p-6 space-y-6 custom-scrollbar">
                {/* 刷新按钮 */}
                <div className="flex justify-end">
                    <button
                        onClick={onRefresh}
                        disabled={loading}
                        className="p-2 bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 rounded-full transition-colors disabled:opacity-50"
                    >
                        <RefreshCw size={18} className={`text-slate-600 dark:text-slate-400 ${loading ? 'animate-spin' : ''}`} />
                    </button>
                </div>

                {/* Loading State */}
                {loading && (
                    <div className="space-y-3 animate-pulse">
                        <div className="h-4 bg-slate-100 dark:bg-slate-800 rounded w-3/4"></div>
                        <div className="h-4 bg-slate-100 dark:bg-slate-800 rounded w-full"></div>
                        <div className="h-4 bg-slate-100 dark:bg-slate-800 rounded w-5/6"></div>
                        <div className="h-32 bg-slate-100 dark:bg-slate-800 rounded w-full mt-4"></div>
                    </div>
                )}

                {/* Analysis Content */}
                {!loading && analysis && (
                    <div className="animate-fade-in space-y-6">
                        {/* Score Card */}
                        <div className="bg-slate-50 dark:bg-slate-800 rounded-xl p-4 border border-slate-100 dark:border-slate-700">
                            <div className="flex justify-between items-end mb-2">
                                <span className="text-sm font-medium text-slate-500 dark:text-slate-400">综合评分 (Bullish Score)</span>
                                <span className={`text-2xl font-bold ${scoreColor}`}>
                                    {bullishScore}/100
                                </span>
                            </div>
                            <div className="w-full bg-slate-200 dark:bg-slate-700 rounded-full h-2">
                                <div
                                    className={`h-2 rounded-full transition-all duration-1000 ${scoreBgColor}`}
                                    style={{ width: `${bullishScore}%` }}
                                ></div>
                            </div>
                        </div>

                        {/* Key Metrics */}
                        <div className="grid grid-cols-2 gap-3">
                            <MetricItem label="最新价格" value={`¥${analysis.latest_price?.toFixed(2) || '--'}`} />
                            <MetricItem label="KDJ J值" value={analysis.kdj_j?.toFixed(2) || '--'} />
                            <MetricItem label="BBI 多空值" value={analysis.bbi_value?.toFixed(2) || '--'} />
                            <MetricItem
                                label="趋势方向"
                                value={bullishScore >= 60 ? '看多' : bullishScore < 40 ? '看空' : '震荡'}
                                icon={bullishScore >= 60 ? <TrendingUp size={14} className="text-up" /> : <TrendingDown size={14} className="text-down" />}
                            />
                        </div>

                        {/* Trading Signals */}
                        {getSignals().length > 0 && (
                            <div>
                                <h4 className="text-sm font-bold text-slate-800 dark:text-slate-200 mb-3 flex items-center">
                                    <AlertCircle size={14} className="mr-2 text-indigo-500" />
                                    交易信号 (Trading Signals)
                                </h4>
                                <ul className="space-y-2">
                                    {getSignals().map((signal) => (
                                        <li
                                            key={signal.key}
                                            className={`flex items-start text-sm p-2 rounded-lg border ${signal.isBuy
                                                ? 'bg-red-50 dark:bg-red-900/20 border-red-100 dark:border-red-800 text-red-700 dark:text-red-400'
                                                : 'bg-emerald-50 dark:bg-emerald-900/20 border-emerald-100 dark:border-emerald-800 text-emerald-700 dark:text-emerald-400'
                                                }`}
                                        >
                                            <span className="mr-2">{signal.isBuy ? '🟢' : '🔴'}</span>
                                            {signal.label}
                                        </li>
                                    ))}
                                </ul>
                            </div>
                        )}

                        {/* Disclaimer */}
                        <div className="text-xs text-slate-300 dark:text-slate-600 pt-4 border-t border-slate-100 dark:border-slate-800 italic">
                            免责声明: AI生成内容仅供参考，不构成投资建议。股市有风险，入市需谨慎。
                        </div>
                    </div>
                )}
            </div>
        </aside>
    );
});

// 小型指标项组件
const MetricItem: React.FC<{ label: string; value: string; icon?: React.ReactNode }> = ({ label, value, icon }) => (
    <div className="bg-slate-50 dark:bg-slate-800 rounded-lg p-3 border border-slate-100 dark:border-slate-700">
        <div className="text-xs text-slate-400 dark:text-slate-500 mb-1">{label}</div>
        <div className="font-bold text-slate-700 dark:text-slate-200 flex items-center gap-1">
            {icon}
            {value}
        </div>
    </div>
);

// 信号名称格式化
const formatSignalName = (key: string): string => {
    const names: { [key: string]: string } = {
        'kdj_buy': 'KDJ 金叉买入',
        'kdj_sell': 'KDJ 死叉卖出',
        'bbi_buy': 'BBI 突破买入',
        'bbi_sell': 'BBI 跌破卖出',
        'macd_buy': 'MACD 金叉买入',
        'macd_sell': 'MACD 死叉卖出',
        'zhixing_buy': '知行趋势买入',
        'zhixing_sell': '知行趋势卖出'
    };
    return names[key] || key;
};

AIAnalysisPanel.displayName = 'AIAnalysisPanel';

export default AIAnalysisPanel;
