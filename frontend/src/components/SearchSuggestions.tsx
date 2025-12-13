import React from 'react';
import { useTheme } from '../ThemeContext';

interface Suggestion {
    code: string;
    name: string;
}

interface SearchSuggestionsProps {
    suggestions: Suggestion[];
    onSelect: (suggestion: Suggestion) => void;
    visible: boolean;
    searchQuery: string;
}

const SearchSuggestions: React.FC<SearchSuggestionsProps> = ({
    suggestions,
    onSelect,
    visible,
    searchQuery
}) => {
    const { theme } = useTheme();

    if (!visible || suggestions.length === 0) {
        return null;
    }

    // 高亮匹配文本
    const highlightMatch = (text: string, query: string) => {
        if (!query) return text;

        const index = text.toLowerCase().indexOf(query.toLowerCase());
        if (index === -1) return text;

        return (
            <>
                {text.substring(0, index)}
                <span style={{
                    background: theme.colors.accent,
                    color: '#fff',
                    padding: '0 2px',
                    borderRadius: '2px'
                }}>
                    {text.substring(index, index + query.length)}
                </span>
                {text.substring(index + query.length)}
            </>
        );
    };

    return (
        <div style={{
            position: 'absolute',
            top: '100%',
            left: 0,
            right: 0,
            background: theme.mode === 'dark' ? 'rgba(38, 38, 40, 0.98)' : 'rgba(255, 255, 255, 0.98)',
            backdropFilter: 'blur(20px)',
            WebkitBackdropFilter: 'blur(20px)',
            border: `1px solid ${theme.colors.border}`,
            borderRadius: '10px',
            marginTop: '0.5rem',
            maxHeight: '320px',
            overflowY: 'auto',
            zIndex: 9999,  // 提高z-index确保在最上层
            boxShadow: theme.mode === 'dark'
                ? '0 8px 24px rgba(0, 0, 0, 0.4)'
                : '0 8px 24px rgba(0, 0, 0, 0.12)'
        }}>
            {suggestions.map((item, index) => (
                <div
                    key={item.code}
                    onClick={() => onSelect(item)}
                    style={{
                        padding: '0.85rem 1rem',
                        cursor: 'pointer',
                        borderBottom: index < suggestions.length - 1 ? `1px solid ${theme.colors.border}` : 'none',
                        transition: 'all 0.15s ease',
                        background: 'transparent'
                    }}
                    onMouseEnter={(e) => {
                        e.currentTarget.style.background = theme.mode === 'dark'
                            ? 'rgba(58, 58, 60, 0.6)'
                            : 'rgba(0, 0, 0, 0.04)';
                    }}
                    onMouseLeave={(e) => {
                        e.currentTarget.style.background = 'transparent';
                    }}
                >
                    {/* 股票名称 */}
                    <div style={{
                        color: theme.colors.textPrimary,
                        fontSize: '0.95rem',
                        fontWeight: 600,
                        marginBottom: '0.25rem',
                        letterSpacing: '-0.01em'
                    }}>
                        {highlightMatch(item.name, searchQuery)}
                    </div>

                    {/* 股票代码 */}
                    <div style={{
                        color: theme.colors.textTertiary,
                        fontSize: '0.8rem',
                        fontWeight: 400
                    }}>
                        {highlightMatch(item.code, searchQuery)}
                    </div>
                </div>
            ))}
        </div>
    );
};

export default SearchSuggestions;
