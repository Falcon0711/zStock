import React, { useState } from 'react';
import { useTheme } from '../ThemeContext';
import SearchSuggestions from './SearchSuggestions';

interface StockQuote {
    code: string;
    name: string;
    price: number;
    change_pct: number;
    time?: string;
}

interface StockGroupsData {
    favorites: StockQuote[];
    holdings: StockQuote[];
    watching: StockQuote[];
}

interface StockGroupsProps {
    onSelectStock: (code: string) => void;
    groups: StockGroupsData;  // 🆕 从父组件接收数据
    loading: boolean;         // 🆕 从父组件接收加载状态
    onRefresh: () => void;    // 🆕 刷新回调
}

const StockGroups: React.FC<StockGroupsProps> = ({ onSelectStock, groups, loading, onRefresh }) => {
    const { theme } = useTheme();
    const [addingTo, setAddingTo] = useState<string | null>(null);
    const [inputCode, setInputCode] = useState('');
    const [suggestions, setSuggestions] = useState<any[]>([]);
    const [showSuggestions, setShowSuggestions] = useState(false);

    const handleAddStock = async () => {
        if (!addingTo || !inputCode || inputCode.length !== 6) return;

        try {
            const response = await fetch('http://localhost:8000/api/user/stocks', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ group: addingTo, code: inputCode })
            });

            if (response.ok) {
                setInputCode('');
                setAddingTo(null);
                onRefresh(); // 🆕 通知父组件刷新
            }
        } catch (error) {
            console.error('Error adding stock:', error);
        }
    };

    const handleRemoveStock = async (group: string, code: string, e: React.MouseEvent) => {
        e.stopPropagation();

        try {
            const response = await fetch('http://localhost:8000/api/user/stocks', {
                method: 'DELETE',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ group, code })
            });

            if (response.ok) {
                onRefresh(); // 🆕 通知父组件刷新
            }
        } catch (error) {
            console.error('Error removing stock:', error);
        }
    };

    const getGroupName = (key: string) => {
        switch (key) {
            case 'favorites': return '⭐ 自选股';
            case 'holdings': return '💼 持有股';
            case 'watching': return '👀 观测股';
            default: return key;
        }
    };

    const renderGroup = (key: keyof StockGroupsData) => (
        <div style={{
            flex: 1,
            background: theme.mode === 'dark' ? 'rgba(28, 28, 30, 0.6)' : 'rgba(255, 255, 255, 0.6)',
            backdropFilter: 'blur(20px)',
            borderRadius: '16px',
            border: `1px solid ${theme.colors.border}`,
            padding: '1.5rem',
            display: 'flex',
            flexDirection: 'column',
            minWidth: '280px',
            height: '100%'
        }}>
            <div style={{
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                marginBottom: '1rem'
            }}>
                <h3 style={{ margin: 0, fontSize: '1.1rem', color: theme.colors.textPrimary }}>
                    {getGroupName(key)}
                </h3>
                <button
                    onClick={() => setAddingTo(key)}
                    style={{
                        background: 'transparent',
                        border: `1px solid ${theme.colors.border}`,
                        borderRadius: '50%',
                        width: '28px',
                        height: '28px',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        cursor: 'pointer',
                        color: theme.colors.textSecondary,
                        fontSize: '1.2rem',
                        lineHeight: 1
                    }}
                >
                    +
                </button>
            </div>

            {addingTo === key && (
                <div style={{ marginBottom: '1rem', display: 'flex', gap: '0.5rem', position: 'relative' }}>
                    <div style={{ flex: 1, position: 'relative' }}>
                        <input
                            type="text"
                            value={inputCode}
                            onChange={(e) => {
                                const val = e.target.value;
                                setInputCode(val);
                                // 搜索建议逻辑
                                if (val.length > 0) {
                                    fetch(`http://localhost:8000/api/stocks/search?q=${val}`)
                                        .then(res => res.json())
                                        .then(data => {
                                            setSuggestions(data);
                                            setShowSuggestions(true);
                                        })
                                        .catch(() => setSuggestions([]));
                                } else {
                                    setSuggestions([]);
                                    setShowSuggestions(false);
                                }
                            }}
                            placeholder="输入股票代码或名称"
                            autoFocus
                            style={{
                                width: '100%',
                                padding: '0.5rem',
                                borderRadius: '8px',
                                border: `1px solid ${theme.colors.accent}`,
                                background: theme.mode === 'dark' ? 'rgba(0,0,0,0.2)' : '#fff',
                                color: theme.colors.textPrimary,
                                outline: 'none'
                            }}
                            onKeyDown={(e) => e.key === 'Enter' && handleAddStock()}
                            onBlur={() => {
                                // 延迟隐藏，以便点击建议项
                                setTimeout(() => setShowSuggestions(false), 200);
                            }}
                        />
                        <SearchSuggestions
                            suggestions={suggestions}
                            visible={showSuggestions}
                            searchQuery={inputCode}
                            onSelect={(code) => {
                                setInputCode(code);
                                setShowSuggestions(false);
                                // 可选：自动提交
                                // handleAddStock(); 
                            }}
                        />
                    </div>
                    <button
                        onClick={handleAddStock}
                        style={{
                            padding: '0.5rem 1rem',
                            borderRadius: '8px',
                            border: 'none',
                            background: theme.colors.accent,
                            color: '#fff',
                            cursor: 'pointer',
                            whiteSpace: 'nowrap'
                        }}
                    >
                        确认
                    </button>
                    <button
                        onClick={() => {
                            setAddingTo(null);
                            setInputCode('');
                            setSuggestions([]);
                        }}
                        style={{
                            padding: '0.5rem',
                            borderRadius: '8px',
                            border: 'none',
                            background: 'transparent',
                            color: theme.colors.textSecondary,
                            cursor: 'pointer'
                        }}
                    >
                        ✕
                    </button>
                </div>
            )}

            {loading && groups[key].length === 0 ? (
                <div style={{ textAlign: 'center', padding: '2rem', color: theme.colors.textTertiary }}>
                    加载中...
                </div>
            ) : (
                <div style={{ flex: 1, overflowY: 'auto' }}>
                    {groups[key].length === 0 ? (
                        <div style={{
                            textAlign: 'center',
                            color: theme.colors.textTertiary,
                            marginTop: '2rem',
                            fontSize: '0.9rem'
                        }}>
                            点击 + 添加股票
                        </div>
                    ) : (
                        groups[key].map((stock) => (
                            <div
                                key={stock.code}
                                onClick={() => onSelectStock(stock.code)}
                                style={{
                                    padding: '0.8rem',
                                    marginBottom: '0.5rem',
                                    background: theme.mode === 'dark' ? 'rgba(255,255,255,0.05)' : 'rgba(0,0,0,0.02)',
                                    borderRadius: '10px',
                                    cursor: 'pointer',
                                    transition: 'transform 0.2s',
                                    display: 'flex',
                                    justifyContent: 'space-between',
                                    alignItems: 'center',
                                    position: 'relative'
                                }}
                                onMouseEnter={(e) => {
                                    e.currentTarget.style.transform = 'translateY(-2px)';
                                    const btn = e.currentTarget.querySelector('.delete-btn') as HTMLElement;
                                    if (btn) btn.style.opacity = '1';
                                }}
                                onMouseLeave={(e) => {
                                    e.currentTarget.style.transform = 'translateY(0)';
                                    const btn = e.currentTarget.querySelector('.delete-btn') as HTMLElement;
                                    if (btn) btn.style.opacity = '0';
                                }}
                            >
                                <div>
                                    <div style={{ fontWeight: 600, color: theme.colors.textPrimary }}>{stock.name}</div>
                                    <div style={{ fontSize: '0.8rem', color: theme.colors.textTertiary }}>{stock.code}</div>
                                </div>
                                <div style={{ textAlign: 'right' }}>
                                    <div style={{
                                        fontWeight: 600,
                                        color: stock.change_pct >= 0 ? '#FF3B30' : '#34C759'
                                    }}>
                                        {stock.price.toFixed(2)}
                                    </div>
                                    <div style={{
                                        fontSize: '0.8rem',
                                        color: stock.change_pct >= 0 ? '#FF3B30' : '#34C759'
                                    }}>
                                        {stock.change_pct >= 0 ? '+' : ''}{stock.change_pct.toFixed(2)}%
                                    </div>
                                </div>

                                <button
                                    className="delete-btn"
                                    onClick={(e) => handleRemoveStock(key, stock.code, e)}
                                    style={{
                                        position: 'absolute',
                                        right: '-8px',
                                        top: '-8px',
                                        width: '20px',
                                        height: '20px',
                                        borderRadius: '50%',
                                        background: theme.colors.textTertiary,
                                        color: '#fff',
                                        border: 'none',
                                        display: 'flex',
                                        alignItems: 'center',
                                        justifyContent: 'center',
                                        fontSize: '12px',
                                        cursor: 'pointer',
                                        opacity: 0,
                                        transition: 'opacity 0.2s'
                                    }}
                                >
                                    ✕
                                </button>
                            </div>
                        ))
                    )}
                </div>
            )}
        </div>
    );

    return (
        <div style={{
            display: 'flex',
            gap: '1.5rem',
            height: '600px', // Fixed height or flex
            width: '100%',
            maxWidth: '1200px',
            margin: '2rem auto',
            padding: '0 1rem'
        }}>
            {renderGroup('favorites')}
            {renderGroup('holdings')}
            {renderGroup('watching')}
        </div>
    );
};

export default StockGroups;
