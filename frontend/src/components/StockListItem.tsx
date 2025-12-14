import React, { memo } from 'react';
import { BarChart2, MoreHorizontal } from 'lucide-react';

interface Stock {
    code: string;
    name: string;
    price: number;
    change_pct: number;
    volume?: string;
    marketValue?: string;
    pe?: number;
}

interface StockListItemProps {
    stock: Stock;
    onSelect: (code: string, name: string) => void;
    isSelected: boolean;
}

/**
 * StockListItem - 股票列表项组件
 * 参考 AlphaSight AI 设计风格
 */
const StockListItem: React.FC<StockListItemProps> = memo(({ stock, onSelect, isSelected }) => {
    const isUp = stock.change_pct >= 0;

    return (
        <div
            onClick={() => onSelect(stock.code, stock.name)}
            className={`
        flex items-center justify-between p-4 mb-3 rounded-xl border cursor-pointer transition-all duration-200
        ${isSelected
                    ? 'bg-blue-50 dark:bg-blue-900/20 border-blue-200 dark:border-blue-800 shadow-md transform scale-[1.01]'
                    : 'bg-white dark:bg-slate-800 border-slate-100 dark:border-slate-700 hover:border-slate-300 dark:hover:border-slate-600 hover:shadow-sm'
                }
      `}
        >
            {/* Left: Name & Code */}
            <div className="flex items-center space-x-4 min-w-[120px]">
                <div className={`w-10 h-10 rounded-full flex items-center justify-center ${isSelected
                        ? 'bg-blue-100 dark:bg-blue-800 text-blue-600 dark:text-blue-300'
                        : 'bg-slate-100 dark:bg-slate-700 text-slate-500 dark:text-slate-400'
                    }`}>
                    <BarChart2 size={20} />
                </div>
                <div>
                    <h4 className="font-bold text-slate-800 dark:text-slate-100">{stock.name}</h4>
                    <span className="text-xs text-slate-400 dark:text-slate-500 font-mono">{stock.code}</span>
                </div>
            </div>

            {/* Middle: Stats (hidden on mobile) */}
            <div className="hidden md:flex space-x-8 text-sm text-slate-500 dark:text-slate-400">
                {stock.volume && (
                    <div className="flex flex-col items-end">
                        <span className="text-xs text-slate-400 dark:text-slate-500">量 (Volume)</span>
                        <span className="font-mono">{stock.volume}</span>
                    </div>
                )}
                {stock.marketValue && (
                    <div className="flex flex-col items-end">
                        <span className="text-xs text-slate-400 dark:text-slate-500">市值 (Cap)</span>
                        <span className="font-mono">{stock.marketValue}</span>
                    </div>
                )}
                {stock.pe && (
                    <div className="flex flex-col items-end">
                        <span className="text-xs text-slate-400 dark:text-slate-500">PE (TTM)</span>
                        <span className="font-mono">{stock.pe.toFixed(2)}</span>
                    </div>
                )}
            </div>

            {/* Right: Price & Change */}
            <div className="flex items-center space-x-4">
                <div className="text-right">
                    <div className={`font-bold font-mono text-lg ${isUp ? 'text-up' : 'text-down'}`}>
                        {stock.price.toFixed(2)}
                    </div>
                    <div className={`text-xs font-medium px-2 py-0.5 rounded-full inline-block ${isUp
                            ? 'bg-red-50 dark:bg-red-900/30 text-up'
                            : 'bg-emerald-50 dark:bg-emerald-900/30 text-down'
                        }`}>
                        {stock.change_pct > 0 ? '+' : ''}{stock.change_pct.toFixed(2)}%
                    </div>
                </div>
                <button className="text-slate-300 dark:text-slate-600 hover:text-slate-500 dark:hover:text-slate-400">
                    <MoreHorizontal size={20} />
                </button>
            </div>
        </div>
    );
});

StockListItem.displayName = 'StockListItem';

export default StockListItem;
