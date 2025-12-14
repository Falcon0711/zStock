import React from 'react';
import type { Theme } from '../../ThemeContext';
import type { TrendLine } from './types';

interface ChartToolbarProps {
    theme: Theme;
    showSignals: boolean;
    setShowSignals: (value: boolean) => void;
    isDrawingMode: boolean;
    setIsDrawingMode: (value: boolean) => void;
    trendLines: TrendLine[];
    clearTrendLines: () => void;
    takeScreenshot: () => void;
}

/**
 * Chart toolbar component with control buttons.
 */
export const ChartToolbar: React.FC<ChartToolbarProps> = ({
    theme,
    showSignals,
    setShowSignals,
    isDrawingMode,
    setIsDrawingMode,
    trendLines,
    clearTrendLines,
    takeScreenshot,
}) => {
    const buttonBaseStyle: React.CSSProperties = {
        padding: '0.4rem 0.8rem',
        borderRadius: '8px',
        border: 'none',
        cursor: 'pointer',
        fontSize: '0.8rem',
        transition: 'all 0.2s',
    };

    return (
        <div style={{ display: 'flex', gap: '0.5rem' }}>
            <button
                onClick={() => {
                    const newValue = !showSignals;
                    setShowSignals(newValue);
                    localStorage.setItem('showSignals', String(newValue));
                }}
                style={{
                    ...buttonBaseStyle,
                    background: showSignals ? theme.colors.accent : theme.colors.bgTertiary,
                    color: showSignals ? '#fff' : theme.colors.textPrimary,
                }}
            >
                📣 信号
            </button>
            <button
                onClick={() => setIsDrawingMode(!isDrawingMode)}
                style={{
                    ...buttonBaseStyle,
                    background: isDrawingMode ? theme.colors.accent : theme.colors.bgTertiary,
                    color: isDrawingMode ? '#fff' : theme.colors.textPrimary,
                }}
            >
                ✏️ 画线
            </button>
            {trendLines.length > 0 && (
                <button
                    onClick={clearTrendLines}
                    style={{
                        ...buttonBaseStyle,
                        background: theme.colors.bgTertiary,
                        color: theme.colors.error,
                    }}
                >
                    🗑️ 清除
                </button>
            )}
            <button
                onClick={takeScreenshot}
                style={{
                    ...buttonBaseStyle,
                    background: theme.colors.bgTertiary,
                    color: theme.colors.textPrimary,
                }}
            >
                📷 截图
            </button>
        </div>
    );
};
