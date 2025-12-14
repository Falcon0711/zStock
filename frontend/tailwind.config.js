/** @type {import('tailwindcss').Config} */
export default {
    content: [
        "./index.html",
        "./src/**/*.{js,ts,jsx,tsx}",
    ],
    darkMode: 'class',
    theme: {
        extend: {
            colors: {
                // 引用 CSS 变量，实现主题统一
                bg: {
                    primary: 'var(--color-bg-primary)',
                    secondary: 'var(--color-bg-secondary)',
                    tertiary: 'var(--color-bg-tertiary)',
                },
                text: {
                    primary: 'var(--color-text-primary)',
                    secondary: 'var(--color-text-secondary)',
                    tertiary: 'var(--color-text-tertiary)',
                },
                border: {
                    DEFAULT: 'var(--color-border)',
                    hover: 'var(--color-border-hover)',
                },
                accent: {
                    DEFAULT: 'var(--color-accent-current)',
                    hover: 'var(--color-accent-current-hover)',
                },
                // 股票颜色（红涨绿跌）
                up: 'var(--color-stock-up)',
                down: 'var(--color-stock-down)',
                // 图表颜色
                chart: {
                    bbi: 'var(--color-chart-bbi)',
                    trend: 'var(--color-chart-trend)',
                    multi: 'var(--color-chart-multi)',
                },
            },
            fontFamily: {
                sans: ['Inter', 'Noto Sans SC', '-apple-system', 'BlinkMacSystemFont', 'system-ui', 'sans-serif'],
                mono: ['SF Mono', 'Menlo', 'monospace'],
            },
            spacing: {
                // 引用 CSS 变量
                'xs': 'var(--spacing-xs)',
                'sm': 'var(--spacing-sm)',
                'md': 'var(--spacing-md)',
                'lg': 'var(--spacing-lg)',
                'xl': 'var(--spacing-xl)',
            },
            borderRadius: {
                'sm': 'var(--radius-sm)',
                'md': 'var(--radius-md)',
                'lg': 'var(--radius-lg)',
                'xl': 'var(--radius-xl)',
            },
            boxShadow: {
                'card': 'var(--shadow-card)',
                'card-hover': 'var(--shadow-card-hover)',
            },
            animation: {
                'fade-in': 'fadeIn 0.5s ease-out forwards',
                'slide-in-right': 'slideInRight 0.3s ease-out forwards',
            },
            keyframes: {
                fadeIn: {
                    '0%': { opacity: '0', transform: 'translateY(10px)' },
                    '100%': { opacity: '1', transform: 'translateY(0)' },
                },
                slideInRight: {
                    '0%': { opacity: '0', transform: 'translateX(100%)' },
                    '100%': { opacity: '1', transform: 'translateX(0)' },
                },
            },
        },
    },
    plugins: [],
}

