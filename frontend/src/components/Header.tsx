import React, { memo, useRef, useCallback } from 'react';
import { useTheme } from '../ThemeContext';
import SearchSuggestions from './SearchSuggestions';
import AddToGroupMenu from './AddToGroupMenu';
import type { StockSuggestion, StockGroupKey } from '../types';

interface HeaderProps {
    searchInput: string;
    onSearchChange: (value: string) => void;
    onSearch: () => void;
    onBack: () => void;
    showBackButton: boolean;
    loading: boolean;
    suggestions: StockSuggestion[];
    showSuggestions: boolean;
    onShowSuggestions: (show: boolean) => void;
    onSelectSuggestion: (suggestion: StockSuggestion) => void;
    onAddToGroup?: (group: StockGroupKey) => Promise<void>;
    showAddButton: boolean;
    addingToGroup: boolean;
}

/**
 * Header component - Main navigation header with search functionality
 */
const Header: React.FC<HeaderProps> = memo(({
    searchInput,
    onSearchChange,
    onSearch,
    onBack,
    showBackButton,
    loading,
    suggestions,
    showSuggestions,
    onShowSuggestions,
    onSelectSuggestion,
    onAddToGroup,
    showAddButton,
    addingToGroup
}) => {
    const { theme, toggleTheme } = useTheme();
    const inputRef = useRef<HTMLInputElement>(null);

    const handleKeyPress = useCallback((e: React.KeyboardEvent) => {
        if (e.key === 'Enter') {
            onSearch();
        }
    }, [onSearch]);

    const handleFocus = useCallback(() => {
        if (suggestions.length > 0) {
            onShowSuggestions(true);
        }
    }, [suggestions.length, onShowSuggestions]);

    const handleBlur = useCallback(() => {
        // Delay to allow clicking on suggestions
        setTimeout(() => onShowSuggestions(false), 200);
    }, [onShowSuggestions]);

    return (
        <header className="header header-glass">
            <div style={{ display: 'flex', gap: '1rem', alignItems: 'center', flex: 1 }}>
                {/* Back Button */}
                {showBackButton && (
                    <button className="btn btn-secondary" onClick={onBack}>
                        <span>←</span>
                        <span>返回</span>
                    </button>
                )}

                {/* Search Input */}
                <div style={{ position: 'relative', width: '280px', flexShrink: 0 }}>
                    <input
                        ref={inputRef}
                        type="text"
                        className="input input-with-icon"
                        placeholder="搜索股票 (如: 平安、000001)"
                        value={searchInput}
                        onChange={e => onSearchChange(e.target.value)}
                        onKeyPress={handleKeyPress}
                        onFocus={handleFocus}
                        onBlur={handleBlur}
                    />
                    <span style={{
                        position: 'absolute',
                        left: '0.8rem',
                        top: '50%',
                        transform: 'translateY(-50%)',
                        color: 'var(--color-text-tertiary)',
                        fontSize: '0.9rem',
                        pointerEvents: 'none'
                    }}>🔍</span>

                    <SearchSuggestions
                        suggestions={suggestions}
                        onSelect={onSelectSuggestion}
                        visible={showSuggestions}
                        searchQuery={searchInput}
                    />
                </div>

                {/* Search Button */}
                <button
                    className="btn btn-primary"
                    onClick={onSearch}
                    disabled={loading}
                    style={{ opacity: loading ? 0.7 : 1 }}
                >
                    {loading ? '分析中...' : '分析'}
                </button>

                {/* Add to Group Button */}
                {showAddButton && onAddToGroup && (
                    <AddToGroupMenu onAdd={onAddToGroup} loading={addingToGroup} />
                )}
            </div>

            <div style={{ display: 'flex', alignItems: 'center', gap: '1.5rem' }}>
                <div style={{
                    color: 'var(--color-text-secondary)',
                    fontSize: '0.85rem',
                    fontWeight: 500,
                    letterSpacing: '-0.01em'
                }}>
                    A股智能分析系统 v2.0
                </div>

                {/* Theme Toggle */}
                <button
                    className="btn btn-icon btn-secondary"
                    onClick={toggleTheme}
                    title={`切换到${theme.mode === 'dark' ? '亮色' : '暗色'}模式`}
                >
                    {theme.mode === 'dark' ? '☀️' : '🌙'}
                </button>
            </div>
        </header>
    );
});

Header.displayName = 'Header';

export default Header;
