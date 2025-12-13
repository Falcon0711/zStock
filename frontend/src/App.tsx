import React, { useState, useRef, useEffect, useCallback } from 'react';
import { ThemeProvider, useTheme } from './ThemeContext';
import Dashboard from './components/Dashboard';
import MarketTicker from './components/MarketTicker';
import StockGroups from './components/StockGroups';
import SearchSuggestions from './components/SearchSuggestions';
import { fetchStockFull, fetchIndexHistory, searchStocks, addUserStock } from './services/api';
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


const AppContent: React.FC = () => {
  const { theme, toggleTheme } = useTheme();


  const [searchInput, setSearchInput] = useState<string>('');
  const [analysis, setAnalysis] = useState<AnalysisResult | null>(null);
  const [history, setHistory] = useState<ChartData[]>([]);
  const [loading, setLoading] = useState<boolean>(false);
  const [indexName, setIndexName] = useState<string>(''); // 🆕 用于显示指数名称
  const [stockName, setStockName] = useState<string>(''); // 🆕 用于显示股票名称

  // 搜索建议状态
  const [suggestions, setSuggestions] = useState<StockSuggestion[]>([]);
  const [showSuggestions, setShowSuggestions] = useState<boolean>(false);
  const searchTimeoutRef = useRef<number | null>(null);

  // 🆕 添加股票按钮状态
  const [showAddMenu, setShowAddMenu] = useState<boolean>(false);
  const [addingToGroup, setAddingToGroup] = useState<boolean>(false);

  // 🆕 自选股数据状态 - 提升到App层保持持久化
  const [stockGroups, setStockGroups] = useState<StockGroupsData>({
    favorites: [],
    holdings: [],
    watching: []
  });
  const [stockGroupsLoading, setStockGroupsLoading] = useState(true);
  const stockGroupsLoaded = useRef(false);

  // 🆕 加载自选股数据（只在首次加载）
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

  // 🆕 首次加载自选股
  useEffect(() => {
    fetchStockGroups();
    // 定时刷新（仅在主页时）
    const interval = setInterval(() => {
      if (!analysis) {
        fetchStockGroups(true);
      }
    }, 30000); // 30秒刷新一次
    return () => clearInterval(interval);
  }, [fetchStockGroups, analysis]);




  const handleAnalyze = async (code: string, name?: string) => {
    if (!code || code.length !== 6) {
      alert('请输入正确的6位股票代码');
      return;
    }

    setLoading(true);
    setSearchInput(code);

    // 🆕 尝试从 suggestions 或参数中获取股票名称
    if (name) {
      setStockName(name);
    } else {
      // 尝试从当前 suggestions 中查找
      const found = suggestions.find(s => s.code === code);
      if (found) {
        setStockName(found.name);
      } else {
        // 如果找不到，尝试通过搜索 API 获取
        try {
          const results = await searchStocks(code, 1);
          if (results.length > 0 && results[0].code === code) {
            setStockName(results[0].name);
          } else {
            setStockName(''); // 找不到则清空
          }
        } catch {
          setStockName('');
        }
      }
    }

    try {
      // 🆕 使用合并端点，一次请求获取分析和历史数据
      const { analysis, history } = await fetchStockFull(code);
      setAnalysis(analysis);
      setHistory(history);
    } catch (error) {
      console.error('Analysis failed', error);
      alert('分析失败，请检查代码或网络');
    } finally {
      setLoading(false);
    }
  };

  // 🆕 处理点击指数 - 获取K线历史数据
  const handleIndexClick = async (code: string, name: string) => {
    setLoading(true);
    setIndexName(name);
    setSearchInput(code);
    setAnalysis(null); // 清除个股分析数据

    try {
      const historyData = await fetchIndexHistory(code);
      setHistory(historyData);
    } catch (error) {
      console.error('获取指数历史失败:', error);
      alert('获取指数历史数据失败');
      setHistory([]);
    } finally {
      setLoading(false);
    }
  };

  const handleBack = () => {
    setAnalysis(null);
    setHistory([]);
    setSearchInput('');
    setIndexName(''); // 🆕 清除指数名称
    setStockName(''); // 🆕 清除股票名称
    setSuggestions([]);
    setShowSuggestions(false);
  };

  // 处理搜索输入（带debounce）
  const handleSearchInput = (value: string) => {
    setSearchInput(value);

    // 清除之前的定时器
    if (searchTimeoutRef.current) {
      clearTimeout(searchTimeoutRef.current);
    }

    // 如果输入小于2个字符，不显示建议
    if (value.length < 2) {
      setSuggestions([]);
      setShowSuggestions(false);
      return;
    }

    // 300ms debounce
    searchTimeoutRef.current = window.setTimeout(async () => {
      try {
        const results = await searchStocks(value, 10);
        setSuggestions(results);
        setShowSuggestions(results.length > 0);
      } catch (error) {
        console.error('搜索失败:', error);
        setSuggestions([]);
        setShowSuggestions(false);
      }
    }, 300);
  };

  // 处理选择建议
  const handleSelectSuggestion = (suggestion: StockSuggestion) => {
    setSearchInput(suggestion.code);
    setStockName(suggestion.name); // 🆕 保存股票名称
    setShowSuggestions(false);
    setSuggestions([]);
    handleAnalyze(suggestion.code, suggestion.name);
  };


  return (
    <div style={{
      minHeight: '100vh',
      background: theme.colors.bgPrimary,
      color: theme.colors.textPrimary,
      transition: 'background-color 0.3s ease, color 0.3s ease',
      fontFamily: '-apple-system, BlinkMacSystemFont, "SF Pro Text", "Helvetica Neue", sans-serif'
    }}>
      <div>
        {/* Market Ticker - 行情横条 */}
        <MarketTicker onSelectIndex={handleIndexClick} />

        {/* Header */}
        <div style={{
          padding: '1rem 2rem',
          background: theme.mode === 'dark' ? 'rgba(28, 28, 30, 0.8)' : 'rgba(255, 255, 255, 0.8)',
          backdropFilter: 'blur(20px)',
          WebkitBackdropFilter: 'blur(20px)',
          borderBottom: `1px solid ${theme.colors.border} `,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          position: 'sticky',
          top: 0,
          zIndex: 100,
          transition: 'all 0.3s ease'
        }}>
          <div style={{ display: 'flex', gap: '1rem', alignItems: 'center', flex: 1 }}>
            {/* 返回按钮 - 仅在有分析结果或指数详情时显示 */}
            {(analysis || (history.length > 0 && indexName)) && (
              <button
                onClick={handleBack}
                style={{
                  padding: '0.5rem 1rem',
                  borderRadius: '8px',
                  border: 'none',
                  background: theme.colors.bgTertiary,
                  color: theme.colors.textPrimary,
                  fontSize: '0.9rem',
                  fontWeight: 500,
                  cursor: 'pointer',
                  transition: 'all 0.2s ease',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '0.4rem'
                }}
                onMouseEnter={(e) => e.currentTarget.style.background = theme.mode === 'dark' ? '#3A3A3C' : '#D1D1D6'}
                onMouseLeave={(e) => e.currentTarget.style.background = theme.colors.bgTertiary}
              >
                <span>←</span>
                <span>返回</span>
              </button>
            )}

            <div style={{ position: 'relative', width: '280px', flexShrink: 0 }}>
              <input
                type="text"
                placeholder="搜索股票 (如: 平安、000001)"
                value={searchInput}
                onChange={e => handleSearchInput(e.target.value)}
                onKeyPress={e => e.key === 'Enter' && handleAnalyze(searchInput)}
                onFocus={(e) => {
                  e.target.style.background = theme.mode === 'dark' ? '#3A3A3C' : '#E5E5EA';
                  // 如果有建议就显示
                  if (suggestions.length > 0) {
                    setShowSuggestions(true);
                  }
                }}
                onBlur={(e) => {
                  e.target.style.background = theme.colors.bgTertiary;
                  // 延迟关闭，以便点击建议
                  setTimeout(() => setShowSuggestions(false), 200);
                }}
                style={{
                  padding: '0.6rem 1rem 0.6rem 2.2rem',
                  borderRadius: '10px',
                  border: 'none',
                  background: theme.colors.bgTertiary,
                  color: theme.colors.textPrimary,
                  fontSize: '0.9rem',
                  width: '100%',
                  boxSizing: 'border-box',
                  outline: 'none',
                  transition: 'all 0.2s ease',
                }}
              />
              <span style={{
                position: 'absolute',
                left: '0.8rem',
                top: '50%',
                transform: 'translateY(-50%)',
                color: theme.colors.textTertiary,
                fontSize: '0.9rem'
              }}>🔍</span>

              {/* 搜索建议组件 */}
              <SearchSuggestions
                suggestions={suggestions}
                onSelect={handleSelectSuggestion}
                visible={showSuggestions}
                searchQuery={searchInput}
              />
            </div>

            <button
              onClick={() => handleAnalyze(searchInput)}
              disabled={loading}
              style={{
                padding: '0.6rem 1.2rem',
                borderRadius: '20px',
                border: 'none',
                background: loading ? theme.colors.bgTertiary : theme.colors.accent,
                color: '#fff',
                fontSize: '0.9rem',
                fontWeight: 500,
                cursor: loading ? 'not-allowed' : 'pointer',
                transition: 'all 0.2s ease',
                opacity: loading ? 0.7 : 1
              }}
              onMouseEnter={(e) => {
                if (!loading) e.currentTarget.style.background = theme.colors.accentHover;
              }}
              onMouseLeave={(e) => {
                if (!loading) e.currentTarget.style.background = theme.colors.accent;
              }}
            >
              {loading ? '分析中...' : '分析'}
            </button>

            {/* 🆕 添加到分组按钮 (仅当有搜索内容时显示) */}
            {searchInput && (
              <div style={{ position: 'relative' }}>
                <button
                  onClick={() => setShowAddMenu(!showAddMenu)}
                  style={{
                    padding: '0.6rem 1rem',
                    borderRadius: '20px',
                    border: `1px solid ${theme.colors.border}`,
                    background: theme.colors.bgTertiary,
                    color: theme.colors.textPrimary,
                    fontSize: '0.9rem',
                    fontWeight: 500,
                    cursor: 'pointer',
                    transition: 'all 0.2s ease',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '0.4rem'
                  }}
                  title="添加到分组"
                >
                  <span>+</span>
                  <span>添加</span>
                </button>

                {showAddMenu && (
                  <>
                    <div
                      style={{ position: 'fixed', inset: 0, zIndex: 101 }}
                      onClick={() => setShowAddMenu(false)}
                    />
                    <div style={{
                      position: 'absolute',
                      top: '120%',
                      right: 0,
                      width: '120px',
                      background: theme.colors.bgSecondary,
                      borderRadius: '12px',
                      boxShadow: '0 4px 20px rgba(0,0,0,0.15)',
                      border: `1px solid ${theme.colors.border}`,
                      padding: '0.5rem',
                      zIndex: 102,
                      display: 'flex',
                      flexDirection: 'column',
                      gap: '0.25rem'
                    }}>
                      {[
                        { id: 'favorites', label: '⭐ 自选股' },
                        { id: 'holdings', label: '💼 持有股' },
                        { id: 'watching', label: '👀 观测股' }
                      ].map(group => (
                        <button
                          key={group.id}
                          onClick={async () => {
                            if (addingToGroup) return;
                            setAddingToGroup(true);
                            try {
                              await addUserStock(group.id, searchInput);
                              await fetchStockGroups(true);
                              setShowAddMenu(false);
                              alert(`已添加到${group.label.split(' ')[1]}`);
                            } catch (error) {
                              console.error(error);
                              alert('添加失败，请重试');
                            } finally {
                              setAddingToGroup(false);
                            }
                          }}
                          style={{
                            padding: '0.6rem 0.8rem',
                            borderRadius: '8px',
                            border: 'none',
                            background: 'transparent',
                            color: theme.colors.textPrimary,
                            fontSize: '0.85rem',
                            textAlign: 'left',
                            cursor: 'pointer',
                            display: 'flex',
                            alignItems: 'center',
                            gap: '0.5rem',
                            transition: 'all 0.2s ease'
                          }}
                          onMouseEnter={(e) => e.currentTarget.style.background = theme.colors.bgTertiary}
                          onMouseLeave={(e) => e.currentTarget.style.background = 'transparent'}
                        >
                          {group.label}
                        </button>
                      ))}
                    </div>
                  </>
                )}
              </div>
            )}
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '1.5rem' }}>
            <div style={{
              color: theme.colors.textSecondary,
              fontSize: '0.85rem',
              fontWeight: 500,
              letterSpacing: '-0.01em'
            }}>
              A股智能分析系统 v2.0
            </div>

            {/* Theme Toggle */}
            <button
              onClick={toggleTheme}
              style={{
                padding: '0.5rem',
                borderRadius: '50%',
                border: 'none',
                background: theme.colors.bgTertiary,
                color: theme.colors.textPrimary,
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                width: '32px',
                height: '32px',
                fontSize: '1rem',
                transition: 'all 0.2s ease'
              }}
              onMouseEnter={(e) => e.currentTarget.style.background = theme.mode === 'dark' ? '#3A3A3C' : '#D1D1D6'}
              onMouseLeave={(e) => e.currentTarget.style.background = theme.colors.bgTertiary}
              title={`切换到${theme.mode === 'dark' ? '亮色' : '暗色'} 模式`}
            >
              {theme.mode === 'dark' ? '☀️' : '🌙'}
            </button>
          </div>
        </div>

        {/* Content */}
        <div style={{ overflow: 'initial' }}>
          {analysis ? (
            <Dashboard analysis={analysis} history={history} loading={loading} stockCode={searchInput} stockName={stockName} />
          ) : history.length > 0 && indexName ? (
            /* 🆕 显示指数K线图 - 委托给 Dashboard 渲染以保持一致性 */
            <Dashboard
              analysis={null as any}
              history={history}
              loading={loading}
              stockName={indexName} // 传入指数名称作为股票名称
              stockCode={searchInput} // 传入指数代码
            />
          ) : (
            <div style={{
              display: 'flex',
              flexDirection: 'column',
              gap: '1rem',
              paddingTop: '2rem'
            }}>
              <div style={{
                textAlign: 'center',
                color: theme.colors.textSecondary,
                fontSize: '1.1rem',
                fontWeight: 500,
                marginBottom: '1rem'
              }}>
                请输入股票代码开始分析，或管理您的股票分组
              </div>

              <StockGroups
                onSelectStock={handleAnalyze}
                groups={stockGroups}
                loading={stockGroupsLoading}
                onRefresh={() => fetchStockGroups(true)}
              />
            </div>
          )}
        </div>
      </div>
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
