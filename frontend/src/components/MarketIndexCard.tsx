import React, { memo } from 'react';
import { TrendingUp, TrendingDown } from 'lucide-react';

interface MarketIndexData {
    code: string;
    name: string;
    value: number;
    change: number;
    changePercent: number;
}

interface MarketIndexCardProps {
    data: MarketIndexData;
    onClick?: (code: string, name: string) => void;
}

/**
 * MarketIndexCard - 市场指数卡片组件
 * 参考 AlphaSight AI 设计风格
 */
const MarketIndexCard: React.FC<MarketIndexCardProps> = memo(({ data, onClick }) => {
    const isUp = data.change >= 0;
    const Icon = isUp ? TrendingUp : TrendingDown;

    return (
        <div
            onClick={() => onClick?.(data.code, data.name)}
            className={`
        bg-white dark:bg-slate-800 rounded-xl p-4 shadow-sm border border-slate-100 dark:border-slate-700
        hover:shadow-md dark:hover:shadow-slate-900/30 transition-all duration-200 cursor-pointer group
        hover:scale-[1.02] active:scale-[0.98]
      `}
        >
            <div className="flex justify-between items-start mb-2">
                <div>
                    <h3 className="text-sm font-medium text-slate-500 dark:text-slate-400">{data.name}</h3>
                    <span className="text-xs text-slate-400 dark:text-slate-500 font-mono">{data.code}</span>
                </div>
                <div className={`p-1.5 rounded-full ${isUp ? 'bg-red-50 dark:bg-red-900/30' : 'bg-emerald-50 dark:bg-emerald-900/30'}`}>
                    <Icon size={16} className={isUp ? 'text-up' : 'text-down'} />
                </div>
            </div>
            <div className="flex items-baseline space-x-2">
                <span className={`text-2xl font-bold ${isUp ? 'text-up' : 'text-down'}`}>
                    {data.value.toFixed(2)}
                </span>
            </div>
            <div className={`flex items-center space-x-2 text-xs font-medium mt-1 ${isUp ? 'text-up' : 'text-down'}`}>
                <span>{data.change > 0 ? '+' : ''}{data.change.toFixed(2)}</span>
                <span>({data.changePercent > 0 ? '+' : ''}{data.changePercent.toFixed(2)}%)</span>
            </div>
        </div>
    );
});

MarketIndexCard.displayName = 'MarketIndexCard';

export default MarketIndexCard;
