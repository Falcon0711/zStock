import React, { memo } from 'react';
import { LayoutGrid, List, Bell, Settings, TrendingUp } from 'lucide-react';

interface SidebarProps {
    activeView: 'dashboard' | 'list' | 'notifications';
    onViewChange: (view: 'dashboard' | 'list' | 'notifications') => void;
}

/**
 * Sidebar - 侧边导航栏组件
 * 参考 AlphaSight AI 设计风格
 */
const Sidebar: React.FC<SidebarProps> = memo(({ activeView, onViewChange }) => {
    const navItems = [
        { id: 'dashboard' as const, icon: LayoutGrid, label: '仪表板' },
        { id: 'list' as const, icon: List, label: '列表' },
        { id: 'notifications' as const, icon: Bell, label: '通知' },
    ];

    return (
        <nav className="hidden md:flex flex-col w-20 bg-white dark:bg-slate-900 border-r border-slate-200 dark:border-slate-800 items-center py-6 space-y-8 z-10">
            {/* Logo */}
            <div className="w-10 h-10 bg-gradient-to-br from-indigo-600 to-purple-600 rounded-xl flex items-center justify-center shadow-lg shadow-indigo-200 dark:shadow-indigo-900/30">
                <TrendingUp className="text-white" size={20} />
            </div>

            {/* Navigation Items */}
            <div className="flex-1 flex flex-col items-center space-y-4 w-full">
                {navItems.map((item) => (
                    <button
                        key={item.id}
                        onClick={() => onViewChange(item.id)}
                        className={`
              p-3 rounded-xl transition-all duration-200
              ${activeView === item.id
                                ? 'text-indigo-600 dark:text-indigo-400 bg-indigo-50 dark:bg-indigo-900/30'
                                : 'text-slate-400 hover:text-slate-600 dark:hover:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-800'
                            }
            `}
                        title={item.label}
                    >
                        <item.icon size={24} />
                    </button>
                ))}
            </div>

            {/* Settings */}
            <button
                className="p-3 text-slate-400 hover:text-slate-600 dark:hover:text-slate-300 rounded-xl transition-colors"
                title="设置"
            >
                <Settings size={24} />
            </button>
        </nav>
    );
});

Sidebar.displayName = 'Sidebar';

export default Sidebar;
