import React, { createContext, useContext, useState, useEffect } from 'react';

export type ThemeMode = 'dark' | 'light';

export interface ThemeColors {
    // Background colors
    bgPrimary: string;
    bgSecondary: string;
    bgTertiary: string;

    // Text colors
    textPrimary: string;
    textSecondary: string;
    textTertiary: string;

    // Accent colors
    accent: string;
    accentHover: string;

    // Status colors
    success: string;
    error: string;
    warning: string;

    // Border colors
    border: string;
    borderHover: string;
}

export interface Theme {
    mode: ThemeMode;
    colors: ThemeColors;
}

// ThemeContextType for the context provider

interface ThemeContextType {
    theme: Theme;
    toggleTheme: () => void;
}

const darkTheme: Theme = {
    mode: 'dark',
    colors: {
        bgPrimary: '#000000', // True black for OLED feel
        bgSecondary: '#1C1C1E', // Apple dark gray for cards
        bgTertiary: '#2C2C2E', // Slightly lighter for inputs/hover

        textPrimary: '#F5F5F7',
        textSecondary: '#86868B', // Apple gray text
        textTertiary: '#6E6E73',

        accent: '#0A84FF', // Apple Dark Mode Blue
        accentHover: '#409CFF',

        success: '#30D158', // Apple Green
        error: '#FF453A', // Apple Red
        warning: '#FF9F0A', // Apple Orange

        border: 'rgba(255, 255, 255, 0.1)',
        borderHover: 'rgba(255, 255, 255, 0.2)',
    },
};

const lightTheme: Theme = {
    mode: 'light',
    colors: {
        bgPrimary: '#F5F5F7', // Apple light gray background
        bgSecondary: '#FFFFFF', // Pure white for cards
        bgTertiary: '#E5E5EA', // System gray 6 for inputs

        textPrimary: '#1D1D1F', // Apple near-black
        textSecondary: '#86868B',
        textTertiary: '#AEAEB2',

        accent: '#007AFF', // Apple Blue
        accentHover: '#0071E3',

        success: '#34C759',
        error: '#FF3B30',
        warning: '#FF9500',

        border: 'rgba(0, 0, 0, 0.05)', // Very subtle border
        borderHover: 'rgba(0, 0, 0, 0.1)',
    },
};

const ThemeContext = createContext<ThemeContextType | undefined>(undefined);

export const ThemeProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
    const [mode, setMode] = useState<ThemeMode>(() => {
        const saved = localStorage.getItem('theme');
        return (saved === 'light' || saved === 'dark') ? saved : 'dark';
    });

    const theme = mode === 'dark' ? darkTheme : lightTheme;

    useEffect(() => {
        localStorage.setItem('theme', mode);
        // Set data-theme attribute for CSS variable switching
        document.documentElement.setAttribute('data-theme', mode);
        document.body.style.backgroundColor = theme.colors.bgPrimary;
        document.body.style.color = theme.colors.textPrimary;
        document.body.style.transition = 'background-color 0.3s ease, color 0.3s ease';
    }, [mode, theme]);

    const toggleTheme = () => {
        setMode(prev => prev === 'dark' ? 'light' : 'dark');
    };

    return (
        <ThemeContext.Provider value={{ theme, toggleTheme }}>
            {children}
        </ThemeContext.Provider>
    );
};

export const useTheme = () => {
    const context = useContext(ThemeContext);
    if (!context) {
        throw new Error('useTheme must be used within ThemeProvider');
    }
    return context;
};
