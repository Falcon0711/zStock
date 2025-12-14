import React, { useState, useRef, useEffect, useCallback } from 'react';
import { ThemeProvider, useTheme } from './ThemeContext';
import Dashboard from './components/Dashboard';
import Sidebar from './components/Sidebar';
import AIAnalysisPanel from './components/AIAnalysisPanel';
import MarketIndexCard from './components/MarketIndexCard';
import StockListItem from './components/StockListItem';
import SearchSuggestions from './components/SearchSuggestions';
import { fetchStockFull, fetchIndexHistory, searchStocks, addUserStock, fetchMarketTicker } from './services/api';
import { Search, Sun, Moon, Plus, Sparkles } from 'lucide-react';
import type { AnalysisResult, ChartData, StockSuggestion } from './services/api';

// 股票分组数据类型
interface StockQuote {
  code: string;
  name: string;
  price: number;
  change_pct: number;
}

interface StockGroupsData {
  favorites: StockQuote[];
  holdings: StockQuote[];
  watching: StockQuote[];
}

// 市场指数数据类型 (用于 MarketIndexCard)
interface MarketIndexDisplay {
  code: string;
  name: string;
  value: number;
  change: number;
  changePercent: number;
}

const AppContent: React.FC = () => {
  const { theme, toggleTheme } = useTheme();

  // 视图状态
  const [activeView, setActiveView] = useState<'dashboard' | 'list' | 'notifications'>('dashboard');
  const [activeTab, setActiveTab] = useState<'favorites' | 'holdings' | 'watching'>('favorites');

  // 搜索状态
  const [searchInput, setSearchInput] = useState<string>('');
  const [suggestions, setSuggestions] = useState<StockSuggestion[]>([]);
  const [showSuggestions, setShowSuggestions] = useState<boolean>(false);
  const searchTimeoutRef = useRef<number | null>(null);

  // 股票数据状态
  const [selectedStock, setSelectedStock] = useState<{ code: string; name: string } | null>(null);
  const [analysis, setAnalysis] = useState<AnalysisResult | null>(null);
  const [history, setHistory] = useState<ChartData[]>([]);
  const [loading, setLoading] = useState<boolean>(false);

  // 添加按钮状态
  const [showAddMenu, setShowAddMenu] = useState<boolean>(false);
  const [addingToGroup, setAddingToGroup] = useState<boolean>(false);
  const [mobileSearchOpen, setMobileSearchOpen] = useState<boolean>(false);

  // 自选股数据状态
  const [stockGroups, setStockGroups] = useState<StockGroupsData>({
    favorites: [],
    holdings: [],
    watching: []
  });
  const [stockGroupsLoading, setStockGroupsLoading] = useState(true);
  const stockGroupsLoaded = useRef(false);

  // 市场指数状态
  const [marketIndices, setMarketIndices] = useState<MarketIndexDisplay[]>([]);
  const [indicesLoading, setIndicesLoading] = useState(true);

  // 加载自选股数据
  const fetchStockGroups = useCallback(async (force = false) => {
    if (stockGroupsLoaded.current && !force) return;

    try {
      const response = await fetch('http://localhost:8000/api/user/stocks');
      if (response.ok) {
        const data = await response.json();
        setStockGroups(data);
        stockGroupsLoaded.current = true;
      }
    } catch (error) {
      console.error('Error fetching user stocks:', error);
    } finally {
      setStockGroupsLoading(false);
    }
  }, []);

  // 首次加载自选股
  useEffect(() => {
    fetchStockGroups();
    const interval = setInterval(() => {
      if (!analysis) {
        fetchStockGroups(true);
      }
    }, 30000);
    return () => clearInterval(interval);
  }, [fetchStockGroups, analysis]);

  // 加载市场指数数据（含港股美股）
  useEffect(() => {
    const loadMarketTicker = async () => {
      try {
        setIndicesLoading(true);
        const response = await fetchMarketTicker();
        // 转换 API 返回格式为组件需要的格式
        const formatted: MarketIndexDisplay[] = response.data.map(item => ({
          code: item.code,
          name: item.name,
          value: item.price,
          change: item.change,
          changePercent: item.change_pct
        }));
        setMarketIndices(formatted);
      } catch (error) {
        console.error('获取市场行情失败:', error);
      } finally {
        setIndicesLoading(false);
      }
    };
    loadMarketTicker();
    // 每30秒刷新一次
    const interval = setInterval(loadMarketTicker, 30000);
    return () => clearInterval(interval);
  }, []);

  // 分析股票
  const handleAnalyze = async (code: string, name?: string) => {
    if (!code || code.length !== 6) {
      return;
    }

    setLoading(true);
    setSearchInput(code);

    const stockName = name || suggestions.find(s => s.code === code)?.name || '';
    setSelectedStock({ code, name: stockName });

    try {
      const { analysis, history } = await fetchStockFull(code);
      setAnalysis(analysis);
      setHistory(history);
    } catch (error) {
      console.error('Analysis failed', error);
    } finally {
      setLoading(false);
    }
  };

  // 刷新分析
  const handleRefreshAnalysis = () => {
    if (selectedStock) {
      handleAnalyze(selectedStock.code, selectedStock.name);
    }
  };

  // 处理点击指数
  const handleIndexClick = async (code: string, name: string) => {
    setLoading(true);
    setSelectedStock({ code, name });
    setAnalysis(null);

    try {
      const historyData = await fetchIndexHistory(code);
      setHistory(historyData);
    } catch (error) {
      console.error('获取指数历史失败:', error);
      setHistory([]);
    } finally {
      setLoading(false);
    }
  };

  // 返回主页
  const handleBack = () => {
    setAnalysis(null);
    setHistory([]);
    setSearchInput('');
    setSelectedStock(null);
    setSuggestions([]);
    setShowSuggestions(false);
  };

  // 处理搜索输入
  const handleSearchInput = (value: string) => {
    setSearchInput(value);

    if (searchTimeoutRef.current) {
      clearTimeout(searchTimeoutRef.current);
    }

    if (value.length < 2) {
      setSuggestions([]);
      setShowSuggestions(false);
      return;
    }

    searchTimeoutRef.current = window.setTimeout(async () => {
      try {
        const results = await searchStocks(value, 10);
        setSuggestions(results);
        setShowSuggestions(results.length > 0);
      } catch (error) {
        console.error('搜索失败:', error);
      }
    }, 300);
  };

  // 处理选择建议
  const handleSelectSuggestion = (suggestion: StockSuggestion) => {
    setShowSuggestions(false);
    setSuggestions([]);
    handleAnalyze(suggestion.code, suggestion.name);
  };

  // 添加到分组
  const handleAddToGroup = async (groupId: string) => {
    if (addingToGroup || !searchInput) return;
    setAddingToGroup(true);
    try {
      await addUserStock(groupId, searchInput);
      await fetchStockGroups(true);
      setShowAddMenu(false);
    } catch (error) {
      console.error(error);
    } finally {
      setAddingToGroup(false);
    }
  };

  // 获取当前显示的股票列表
  const getCurrentStockList = (): StockQuote[] => {
    switch (activeTab) {
      case 'favorites': return stockGroups.favorites;
      case 'holdings': return stockGroups.holdings;
      case 'watching': return stockGroups.watching;
      default: return [];
    }
  };

  // 暗色模式处理
  useEffect(() => {
    if (theme.mode === 'dark') {
      document.documentElement.classList.add('dark');
    } else {
      document.documentElement.classList.remove('dark');
    }
  }, [theme.mode]);

  return (
    <div className="min-h-screen flex flex-col md:flex-row overflow-hidden transition-colors duration-300\"
      style={{ backgroundColor: 'var(--color-bg-primary)', color: 'var(--color-text-primary)' }}>
      {/* Sidebar */}
      <Sidebar activeView={activeView} onViewChange={setActiveView} />

      {/* Main Content Area */}
      <main className="flex-1 flex flex-col h-screen overflow-hidden">
        {/* Header */}
        <header className="bg-white/80 dark:bg-slate-900/80 backdrop-blur-md border-b border-slate-200 dark:border-slate-800 p-4 md:px-8 flex justify-between items-center z-10">
          <div className="flex items-center space-x-4">
            {/* Back Button */}
            {(analysis || (history.length > 0 && selectedStock)) && (
              <button
                onClick={handleBack}
                className="px-4 py-2 rounded-lg bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300 hover:bg-slate-200 dark:hover:bg-slate-700 transition-colors flex items-center gap-2"
              >
                <span>←</span>
                <span>返回</span>
              </button>
            )}

            {/* App Title */}
            <h1 className="text-xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-slate-900 to-slate-600 dark:from-slate-100 dark:to-slate-400">
              A股智能分析
              <span className="text-xs font-normal text-slate-400 dark:text-slate-500 ml-2 border border-slate-200 dark:border-slate-700 px-1.5 py-0.5 rounded">V3.0</span>
            </h1>
          </div>

          {/* Search */}
          <div className="flex-1 max-w-lg mx-8 relative hidden md:block">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" size={18} />
            <input
              type="text"
              placeholder="搜索股票代码 / 名称 (e.g. 600519)..."
              value={searchInput}
              onChange={e => handleSearchInput(e.target.value)}
              onKeyPress={e => e.key === 'Enter' && handleAnalyze(searchInput)}
              onFocus={() => suggestions.length > 0 && setShowSuggestions(true)}
              onBlur={() => setTimeout(() => setShowSuggestions(false), 200)}
              className="w-full pl-10 pr-4 py-2 bg-slate-100 dark:bg-slate-800 border-none rounded-full focus:ring-2 focus:ring-indigo-500 focus:bg-white dark:focus:bg-slate-700 transition-all text-sm outline-none"
            />
            <SearchSuggestions
              suggestions={suggestions}
              onSelect={handleSelectSuggestion}
              visible={showSuggestions}
              searchQuery={searchInput}
            />
          </div>

          {/* Right Actions */}
          <div className="flex items-center space-x-4">
            {/* Add Button */}
            {searchInput && (
              <div className="relative">
                <button
                  onClick={() => setShowAddMenu(!showAddMenu)}
                  className="p-2 rounded-full bg-indigo-50 dark:bg-indigo-900/30 text-indigo-600 dark:text-indigo-400 hover:bg-indigo-100 dark:hover:bg-indigo-900/50 transition-colors"
                >
                  <Plus size={18} />
                </button>
                {showAddMenu && (
                  <>
                    <div className="fixed inset-0 z-10" onClick={() => setShowAddMenu(false)} />
                    <div className="absolute top-full right-0 mt-2 w-32 bg-white dark:bg-slate-800 rounded-xl shadow-lg border border-slate-200 dark:border-slate-700 py-2 z-20">
                      {[
                        { id: 'favorites', label: '⭐ 自选股' },
                        { id: 'holdings', label: '💼 持有股' },
                        { id: 'watching', label: '👀 观测股' }
                      ].map(group => (
                        <button
                          key={group.id}
                          onClick={() => handleAddToGroup(group.id)}
                          className="w-full px-3 py-2 text-left text-sm hover:bg-slate-50 dark:hover:bg-slate-700 transition-colors"
                        >
                          {group.label}
                        </button>
                      ))}
                    </div>
                  </>
                )}
              </div>
            )}

            {/* Time Display */}
            <span className="text-xs text-slate-500 dark:text-slate-400 hidden sm:inline-block">
              北京时间 {new Date().toLocaleTimeString('zh-CN')}
            </span>

            {/* Theme Toggle */}
            <button
              onClick={toggleTheme}
              className="p-2 rounded-full bg-slate-100 dark:bg-slate-800 text-slate-500 dark:text-slate-400 hover:bg-slate-200 dark:hover:bg-slate-700 transition-colors"
            >
              {theme.mode === 'dark' ? <Sun size={18} /> : <Moon size={18} />}
            </button>
          </div>
        </header>

        {/* Dashboard Content */}
        <div className="flex-1 overflow-hidden flex flex-col md:flex-row relative">
          {/* Left/Main Column */}
          <div className="flex-1 overflow-y-auto p-4 md:p-8 custom-scrollbar">
            {/* Market Overview Cards */}
            {!selectedStock && (
              <div className="flex overflow-x-auto gap-4 mb-8 pb-4 animate-fade-in custom-slider-scrollbar">
                {indicesLoading ? (
                  <div className="flex-1 text-center py-8 text-slate-400">加载中...</div>
                ) : marketIndices.length > 0 ? (
                  marketIndices.map((idx: MarketIndexDisplay) => (
                    <div key={idx.code} className="flex-shrink-0 w-48">
                      <MarketIndexCard data={idx} onClick={handleIndexClick} />
                    </div>
                  ))
                ) : (
                  <div className="flex-1 text-center py-8 text-slate-400">暂无市场数据</div>
                )}
              </div>
            )}

            {/* Main Content */}
            {selectedStock ? (
              <div className="animate-fade-in">
                <Dashboard
                  analysis={analysis}
                  history={history}
                  loading={loading}
                  stockCode={selectedStock.code}
                  stockName={selectedStock.name}
                />
              </div>
            ) : (
              <div className="flex flex-col xl:flex-row gap-6">
                {/* Stock List Section */}
                <div className="flex-1">
                  {/* Tabs */}
                  <div className="flex items-center space-x-6 border-b border-slate-200 dark:border-slate-800 mb-4 pb-2">
                    {[
                      { id: 'favorites' as const, label: '自选股 (My Watchlist)' },
                      { id: 'holdings' as const, label: '持有 (Portfolio)' },
                      { id: 'watching' as const, label: '观测 (Watching)' }
                    ].map(tab => (
                      <button
                        key={tab.id}
                        onClick={() => setActiveTab(tab.id)}
                        className={`pb-2 font-medium text-sm transition-colors relative ${activeTab === tab.id
                          ? 'text-indigo-600 dark:text-indigo-400'
                          : 'text-slate-500 dark:text-slate-400 hover:text-slate-700 dark:hover:text-slate-300'
                          }`}
                      >
                        {tab.label}
                        {activeTab === tab.id && (
                          <div className="absolute bottom-0 left-0 w-full h-0.5 bg-indigo-600 dark:bg-indigo-400 rounded-t-full" />
                        )}
                      </button>
                    ))}
                  </div>

                  {/* Stock List */}
                  <div className="space-y-1">
                    {stockGroupsLoading ? (
                      <div className="text-center py-8 text-slate-400">加载中...</div>
                    ) : getCurrentStockList().length === 0 ? (
                      <div className="text-center py-8 text-slate-400">
                        暂无股票，请搜索添加
                      </div>
                    ) : (
                      getCurrentStockList().map(stock => (
                        <StockListItem
                          key={stock.code}
                          stock={stock}
                          onSelect={(code, name) => handleAnalyze(code, name)}
                          isSelected={false}
                        />
                      ))
                    )}
                  </div>
                </div>

                {/* AI Insight Card */}
                <div className="xl:w-1/2">
                  <div className="bg-gradient-to-br from-indigo-500 to-purple-600 rounded-xl p-6 text-white shadow-lg">
                    <div className="flex items-center gap-2 mb-2">
                      <Sparkles size={18} className="opacity-90" />
                      <h4 className="font-bold opacity-90">AI 市场洞察</h4>
                    </div>
                    <p className="text-sm opacity-80 leading-relaxed">
                      选择一支股票，AI 将为您进行深度技术面分析，包括 KDJ、MACD、BBI 等多维度指标评估，帮助您做出更明智的投资决策。
                    </p>
                    <button className="mt-4 text-xs bg-white/20 hover:bg-white/30 px-3 py-1.5 rounded-lg transition-colors">
                      了解更多
                    </button>
                  </div>
                </div>
              </div>
            )}
          </div>

          {/* Right Panel: AI Analysis */}
          <aside className={`
            fixed inset-y-0 right-0 w-full md:w-[320px] bg-white dark:bg-slate-900 transform transition-transform duration-300 ease-in-out z-30 shadow-2xl md:shadow-none md:static md:translate-x-0
            ${selectedStock ? 'translate-x-0' : 'translate-x-full md:translate-x-0'}
          `}>
            {/* Mobile Close Button */}
            <button
              className="md:hidden absolute top-4 right-4 z-40 p-2 bg-slate-100 dark:bg-slate-800 rounded-full"
              onClick={handleBack}
            >
              ✕
            </button>
            <AIAnalysisPanel
              stockName={selectedStock?.name || null}
              stockCode={selectedStock?.code || null}
              analysis={analysis}
              loading={loading}
              onRefresh={handleRefreshAnalysis}
            />
          </aside>
        </div>
      </main>

      {/* 移动端悬浮搜索按钮 */}
      {!mobileSearchOpen && !selectedStock && (
        <button
          onClick={() => setMobileSearchOpen(true)}
          className="md:hidden fixed bottom-6 right-6 w-14 h-14 bg-accent text-white rounded-full shadow-lg z-50 flex items-center justify-center hover:bg-accent-hover transition-colors"
          style={{ backgroundColor: 'var(--color-accent-current)' }}
        >
          <Search size={24} />
        </button>
      )}

      {/* 移动端搜索弹窗 */}
      {mobileSearchOpen && (
        <div className="md:hidden fixed inset-0 bg-bg-primary z-50 flex flex-col" style={{ backgroundColor: 'var(--color-bg-primary)' }}>
          {/* 搜索头部 */}
          <div className="flex items-center gap-3 p-4 border-b" style={{ borderColor: 'var(--color-border)' }}>
            <button
              onClick={() => setMobileSearchOpen(false)}
              className="p-2 rounded-full"
              style={{ backgroundColor: 'var(--color-bg-tertiary)' }}
            >
              ✕
            </button>
            <div className="flex-1 relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2" size={18} style={{ color: 'var(--color-text-tertiary)' }} />
              <input
                autoFocus
                type="text"
                placeholder="搜索股票代码 / 名称..."
                value={searchInput}
                onChange={e => handleSearchInput(e.target.value)}
                onKeyPress={e => {
                  if (e.key === 'Enter') {
                    handleAnalyze(searchInput);
                    setMobileSearchOpen(false);
                  }
                }}
                className="w-full pl-10 pr-4 py-3 rounded-full text-sm outline-none"
                style={{
                  backgroundColor: 'var(--color-bg-tertiary)',
                  color: 'var(--color-text-primary)'
                }}
              />
            </div>
          </div>

          {/* 搜索结果 */}
          <div className="flex-1 overflow-y-auto p-4">
            {suggestions.length > 0 ? (
              <div className="space-y-2">
                {suggestions.map(s => (
                  <button
                    key={s.code}
                    onClick={() => {
                      handleSelectSuggestion(s);
                      setMobileSearchOpen(false);
                    }}
                    className="w-full p-4 rounded-xl text-left transition-colors"
                    style={{ backgroundColor: 'var(--color-bg-secondary)' }}
                  >
                    <div className="font-medium" style={{ color: 'var(--color-text-primary)' }}>{s.name}</div>
                    <div className="text-sm" style={{ color: 'var(--color-text-tertiary)' }}>{s.code}</div>
                  </button>
                ))}
              </div>
            ) : searchInput.length > 0 ? (
              <div className="text-center py-8" style={{ color: 'var(--color-text-tertiary)' }}>
                输入更多字符搜索...
              </div>
            ) : (
              <div className="text-center py-8" style={{ color: 'var(--color-text-tertiary)' }}>
                输入股票代码或名称搜索
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};

const App: React.FC = () => {
  return (
    <ThemeProvider>
      <AppContent />
    </ThemeProvider>
  );
};

export default App;
