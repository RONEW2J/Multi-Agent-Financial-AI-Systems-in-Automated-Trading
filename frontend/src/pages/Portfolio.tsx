import { useEffect, useState } from 'react';
import { userApi, tradingApi, portfolioApi } from '../services/api';
import { DollarSign, TrendingUp, TrendingDown, Package, RefreshCw, ShoppingCart, Brain, Target, Activity, Loader2 } from 'lucide-react';
import { useAuth } from '../contexts/AuthContext';

interface Position {
  symbol: string;
  shares: number;
  avg_price: number;
  current_price: number;
  cost_basis: number;
  current_value: number;
  profit_loss: number;
  profit_loss_pct: number;
  days_held: number;
  buy_date: string;
}

interface AgentPrediction {
  symbol: string;
  predicted_change_percent: number;
  confidence: number;
  current_price: number;
  predicted_price: number;
  rsi: number;
  volume_trend: string;
}

interface AgentDecision {
  symbol: string;
  decision: 'BUY' | 'SELL' | 'HOLD';
  confidence: number;
  reasons: string[];
  predicted_change: number;
  method: string;
}

interface PositionWithAI extends Position {
  prediction?: AgentPrediction;
  agentDecision?: AgentDecision;
}

interface UserPortfolio {
  user_id: number;
  cash: number;
  total_value: number;
  positions: Position[];
  positions_count: number;
  invested_value: number;
  current_positions_value: number;
  total_return: number;
  total_return_pct: number;
  created_at: string;
  updated_at: string;
}

interface Transaction {
  type: 'BUY' | 'SELL';
  symbol: string;
  shares: number;
  price: number;
  total: number;
  timestamp: string;
}

export default function Portfolio() {
  const { user } = useAuth();
  const [portfolio, setPortfolio] = useState<UserPortfolio | null>(null);
  const [transactions, setTransactions] = useState<Transaction[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showBuyDialog, setShowBuyDialog] = useState(false);
  const [showSellDialog, setShowSellDialog] = useState(false);
  const [selectedSymbol, setSelectedSymbol] = useState('');
  const [quantity, setQuantity] = useState('');
  const [positionsWithAI, setPositionsWithAI] = useState<PositionWithAI[]>([]);
  const [loadingAI, setLoadingAI] = useState(false);
  const [aiError, setAIError] = useState<string | null>(null);

  useEffect(() => {
    loadPortfolio();
    loadTransactions();
  }, []);

  useEffect(() => {
    if (portfolio?.positions && portfolio.positions.length > 0) {
      loadAIAnalysis();
    }
  }, [portfolio?.positions?.length]);

  const loadPortfolio = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await userApi.getMyPortfolio();
      setPortfolio(data);
    } catch (err: any) {
      setError(err.message || 'Failed to load portfolio');
    } finally {
      setLoading(false);
    }
  };

  const loadAIAnalysis = async () => {
    if (!portfolio?.positions || portfolio.positions.length === 0) return;
    
    try {
      setLoadingAI(true);
      setAIError(null);
      
      // Get symbols from positions
      const symbols = portfolio.positions.map((p: any) => p.symbol);
      
      // Run trading cycle to get predictions and decisions
      const result = await tradingApi.runTradingCycle({
        symbols,
        use_csv: true,
      });
      
      // Merge predictions and decisions with positions
      const merged: PositionWithAI[] = portfolio.positions.map((pos: Position) => {
        const prediction = result.predictions?.find((p: any) => p.symbol === pos.symbol);
        const decision = result.decisions?.find((d: any) => d.symbol === pos.symbol);
        
        return {
          ...pos,
          prediction,
          agentDecision: decision,
        };
      });
      
      setPositionsWithAI(merged);
    } catch (err: any) {
      setAIError(err.message || 'Failed to load AI analysis');
      // Just use positions without AI data
      setPositionsWithAI(portfolio.positions.map((p: Position) => ({ ...p })));
    } finally {
      setLoadingAI(false);
    }
  };

  const loadTransactions = async () => {
    try {
      const data = await userApi.getMyTransactions();
      setTransactions(data.transactions.slice(0, 10)); // Last 10 transactions
    } catch (err) {
      console.error('Failed to load transactions:', err);
    }
  };

  const handleBuyStock = async () => {
    if (!selectedSymbol || !quantity) return;

    try {
      await userApi.buyStock(selectedSymbol, parseFloat(quantity));
      setShowBuyDialog(false);
      setSelectedSymbol('');
      setQuantity('');
      await loadPortfolio();
      await loadTransactions();
    } catch (err: any) {
      alert(`Failed to buy stock: ${err.message}`);
    }
  };

  const handleSellStock = async () => {
    if (!selectedSymbol || !quantity) return;

    try {
      await userApi.sellStock(selectedSymbol, parseFloat(quantity));
      setShowSellDialog(false);
      setSelectedSymbol('');
      setQuantity('');
      await loadPortfolio();
      await loadTransactions();
    } catch (err: any) {
      alert(`Failed to sell stock: ${err.message}`);
    }
  };

  const formatCurrency = (value: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
    }).format(value);
  };

  const formatPercent = (value: number) => {
    return `${value >= 0 ? '+' : ''}${value.toFixed(2)}%`;
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleString('en-US', {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500"></div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="card bg-red-900/20 border-red-800">
        <p className="text-red-400">{error}</p>
      </div>
    );
  }

  const positionsList = portfolio?.positions || [];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-white mb-2">My Portfolio</h1>
          <p className="text-slate-400">{user?.username}'s holdings and performance</p>
        </div>
        <div className="flex gap-2">
          <button 
            onClick={loadAIAnalysis} 
            disabled={loadingAI || !portfolio?.positions?.length}
            className="btn-secondary flex items-center gap-2"
          >
            {loadingAI ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <Brain className="w-4 h-4" />
            )}
            AI Analysis
          </button>
          <button onClick={() => setShowBuyDialog(true)} className="btn-primary flex items-center gap-2">
            <ShoppingCart className="w-4 h-4" />
            Buy Stock
          </button>
          <button onClick={loadPortfolio} className="btn-secondary flex items-center gap-2">
            <RefreshCw className="w-4 h-4" />
            Refresh
          </button>
        </div>
      </div>

      {/* AI Analysis Status */}
      {loadingAI && (
        <div className="card bg-blue-900/20 border-blue-700">
          <div className="flex items-center gap-3">
            <Loader2 className="w-5 h-5 text-blue-400 animate-spin" />
            <div>
              <p className="text-blue-400 font-medium">AI Agents analyzing your portfolio...</p>
              <p className="text-blue-300/70 text-sm">Getting predictions and trading recommendations</p>
            </div>
          </div>
        </div>
      )}
      
      {aiError && (
        <div className="card bg-yellow-900/20 border-yellow-700">
          <p className="text-yellow-400">AI Analysis: {aiError}</p>
        </div>
      )}

      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <div className="card">
          <div className="flex items-center justify-between mb-2">
            <p className="text-slate-400 text-sm">Total Value</p>
            <DollarSign className="w-5 h-5 text-blue-500" />
          </div>
          <p className="text-2xl font-bold text-white">
            {formatCurrency(portfolio?.total_value || 0)}
          </p>
        </div>

        <div className="card">
          <div className="flex items-center justify-between mb-2">
            <p className="text-slate-400 text-sm">Cash</p>
            <DollarSign className="w-5 h-5 text-green-500" />
          </div>
          <p className="text-2xl font-bold text-white">{formatCurrency(portfolio?.cash || 0)}</p>
        </div>

        <div className="card">
          <div className="flex items-center justify-between mb-2">
            <p className="text-slate-400 text-sm">Positions Value</p>
            <Package className="w-5 h-5 text-purple-500" />
          </div>
          <p className="text-2xl font-bold text-white">
            {formatCurrency(portfolio?.current_positions_value || 0)}
          </p>
        </div>

        <div className="card">
          <div className="flex items-center justify-between mb-2">
            <p className="text-slate-400 text-sm">Total P&L</p>
            {(portfolio?.total_return || 0) >= 0 ? (
              <TrendingUp className="w-5 h-5 text-green-500" />
            ) : (
              <TrendingDown className="w-5 h-5 text-red-500" />
            )}
          </div>
          <p
            className={`text-2xl font-bold ${
              (portfolio?.total_return || 0) >= 0 ? 'text-green-400' : 'text-red-400'
            }`}
          >
            {formatCurrency(portfolio?.total_return || 0)}
          </p>
          <p
            className={`text-sm mt-1 ${
              (portfolio?.total_return_pct || 0) >= 0 ? 'text-green-400' : 'text-red-400'
            }`}
          >
            {formatPercent(portfolio?.total_return_pct || 0)}
          </p>
        </div>
      </div>

      {/* Positions with AI Analysis */}
      <div className="card">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-xl font-semibold text-white">
            Active Positions ({portfolio?.positions_count || 0})
          </h2>
          {positionsWithAI.some(p => p.agentDecision) && (
            <div className="flex items-center gap-2 text-sm">
              <Brain className="w-4 h-4 text-blue-400" />
              <span className="text-blue-400">AI Analyzed</span>
            </div>
          )}
        </div>

        {positionsList.length === 0 ? (
          <div className="text-center py-12">
            <Package className="w-16 h-16 text-slate-600 mx-auto mb-4" />
            <p className="text-slate-400 text-lg">No active positions</p>
            <p className="text-slate-500 text-sm mt-2">
              Click "Buy Stock" to start building your portfolio
            </p>
          </div>
        ) : (
          <div className="space-y-4">
            {(positionsWithAI.length > 0 ? positionsWithAI : positionsList).map((position) => {
              const posWithAI = position as PositionWithAI;
              return (
                <div key={position.symbol} className="bg-slate-800/50 rounded-lg p-4 border border-slate-700">
                  <div className="flex flex-col lg:flex-row lg:items-center gap-4">
                    {/* Position Info */}
                    <div className="flex-1 grid grid-cols-2 md:grid-cols-4 gap-4">
                      <div>
                        <p className="text-xs text-slate-400 mb-1">Symbol</p>
                        <p className="font-bold text-white text-lg">{position.symbol}</p>
                        <p className="text-xs text-slate-500">{position.shares} shares</p>
                      </div>
                      <div>
                        <p className="text-xs text-slate-400 mb-1">Current Price</p>
                        <p className="text-white font-semibold">{formatCurrency(position.current_price)}</p>
                        <p className="text-xs text-slate-500">Avg: {formatCurrency(position.avg_price)}</p>
                      </div>
                      <div>
                        <p className="text-xs text-slate-400 mb-1">Market Value</p>
                        <p className="text-white font-semibold">{formatCurrency(position.current_value)}</p>
                      </div>
                      <div>
                        <p className="text-xs text-slate-400 mb-1">P&L</p>
                        <p className={`font-semibold ${position.profit_loss >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                          {formatCurrency(position.profit_loss)}
                        </p>
                        <p className={`text-xs ${position.profit_loss_pct >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                          {formatPercent(position.profit_loss_pct)}
                        </p>
                      </div>
                    </div>
                    
                    {/* AI Prediction & Decision */}
                    {posWithAI.prediction && (
                      <div className="flex-shrink-0 flex flex-col md:flex-row gap-3">
                        {/* Prediction */}
                        <div className="bg-slate-900 rounded-lg p-3 min-w-[160px]">
                          <div className="flex items-center gap-1 mb-2">
                            <Brain className="w-3 h-3 text-blue-400" />
                            <p className="text-xs text-slate-400">AI Prediction</p>
                          </div>
                          <div className="flex items-center gap-2">
                            {posWithAI.prediction.predicted_change_percent >= 0 ? (
                              <TrendingUp className="w-4 h-4 text-green-400" />
                            ) : (
                              <TrendingDown className="w-4 h-4 text-red-400" />
                            )}
                            <span className={`font-bold ${posWithAI.prediction.predicted_change_percent >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                              {posWithAI.prediction.predicted_change_percent >= 0 ? '+' : ''}
                              {posWithAI.prediction.predicted_change_percent?.toFixed(2)}%
                            </span>
                          </div>
                          <p className="text-xs text-slate-500 mt-1">
                            Confidence: {(posWithAI.prediction.confidence * 100).toFixed(0)}%
                          </p>
                        </div>
                        
                        {/* Decision */}
                        {posWithAI.agentDecision && (
                          <div className={`rounded-lg p-3 min-w-[140px] border-2 ${
                            posWithAI.agentDecision.decision === 'BUY' ? 'bg-green-900/30 border-green-600' :
                            posWithAI.agentDecision.decision === 'SELL' ? 'bg-red-900/30 border-red-600' :
                            'bg-yellow-900/30 border-yellow-600'
                          }`}>
                            <div className="flex items-center gap-1 mb-2">
                              <Target className="w-3 h-3 text-slate-400" />
                              <p className="text-xs text-slate-400">Decision</p>
                            </div>
                            <div className="flex items-center gap-2">
                              {posWithAI.agentDecision.decision === 'BUY' ? (
                                <TrendingUp className="w-5 h-5 text-green-400" />
                              ) : posWithAI.agentDecision.decision === 'SELL' ? (
                                <TrendingDown className="w-5 h-5 text-red-400" />
                              ) : (
                                <Activity className="w-5 h-5 text-yellow-400" />
                              )}
                              <span className={`font-bold text-lg ${
                                posWithAI.agentDecision.decision === 'BUY' ? 'text-green-400' :
                                posWithAI.agentDecision.decision === 'SELL' ? 'text-red-400' :
                                'text-yellow-400'
                              }`}>
                                {posWithAI.agentDecision.decision}
                              </span>
                            </div>
                            <p className="text-xs text-slate-500 mt-1">
                              {(posWithAI.agentDecision.confidence * 100).toFixed(0)}% confident
                            </p>
                          </div>
                        )}
                      </div>
                    )}
                    
                    {/* Actions */}
                    <div className="flex-shrink-0">
                      <button
                        onClick={() => {
                          setSelectedSymbol(position.symbol);
                          setShowSellDialog(true);
                        }}
                        className="text-sm px-4 py-2 bg-red-600 hover:bg-red-700 text-white rounded-lg transition-colors"
                      >
                        Sell
                      </button>
                    </div>
                  </div>
                  
                  {/* AI Reasons */}
                  {posWithAI.agentDecision?.reasons && posWithAI.agentDecision.reasons.length > 0 && (
                    <div className="mt-3 pt-3 border-t border-slate-700">
                      <p className="text-xs text-slate-400 mb-1">AI Reasoning:</p>
                      <div className="flex flex-wrap gap-2">
                        {posWithAI.agentDecision.reasons.map((reason, idx) => (
                          <span key={idx} className="text-xs bg-slate-700 text-slate-300 px-2 py-1 rounded">
                            {reason}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Recent Transactions */}
      {transactions.length > 0 && (
        <div className="card">
          <h2 className="text-xl font-semibold text-white mb-4">Recent Transactions</h2>
          <div className="space-y-3">
            {transactions.map((tx, index) => (
              <div key={index} className="flex items-center justify-between p-3 bg-slate-700/50 rounded">
                <div className="flex items-center gap-3">
                  <div className={`px-2 py-1 rounded text-xs font-semibold ${
                    tx.type === 'BUY' ? 'bg-green-600 text-white' : 'bg-red-600 text-white'
                  }`}>
                    {tx.type}
                  </div>
                  <div>
                    <div className="text-white font-medium">{tx.symbol}</div>
                    <div className="text-sm text-slate-400">{formatDate(tx.timestamp)}</div>
                  </div>
                </div>
                <div className="text-right">
                  <div className="text-white">{tx.shares} shares @ {formatCurrency(tx.price)}</div>
                  <div className="text-sm text-slate-400">Total: {formatCurrency(tx.total)}</div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Buy Dialog */}
      {showBuyDialog && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="card max-w-md w-full mx-4">
            <h3 className="text-xl font-bold text-white mb-4">Buy Stock</h3>
            <div className="space-y-4">
              <div>
                <label className="block text-sm text-slate-400 mb-2">Stock Symbol</label>
                <input
                  type="text"
                  value={selectedSymbol}
                  onChange={(e) => setSelectedSymbol(e.target.value.toUpperCase())}
                  placeholder="e.g., AAPL"
                  className="w-full px-4 py-2 bg-slate-700 border border-slate-600 rounded text-white"
                />
              </div>
              <div>
                <label className="block text-sm text-slate-400 mb-2">Quantity</label>
                <input
                  type="number"
                  value={quantity}
                  onChange={(e) => setQuantity(e.target.value)}
                  placeholder="Number of shares"
                  className="w-full px-4 py-2 bg-slate-700 border border-slate-600 rounded text-white"
                />
              </div>
              <div className="flex gap-2">
                <button onClick={handleBuyStock} className="flex-1 btn-primary">
                  Buy
                </button>
                <button
                  onClick={() => {
                    setShowBuyDialog(false);
                    setSelectedSymbol('');
                    setQuantity('');
                  }}
                  className="flex-1 btn-secondary"
                >
                  Cancel
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Sell Dialog */}
      {showSellDialog && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="card max-w-md w-full mx-4">
            <h3 className="text-xl font-bold text-white mb-4">Sell Stock</h3>
            <div className="space-y-4">
              <div>
                <label className="block text-sm text-slate-400 mb-2">Stock Symbol</label>
                <input
                  type="text"
                  value={selectedSymbol}
                  readOnly
                  className="w-full px-4 py-2 bg-slate-700 border border-slate-600 rounded text-white"
                />
              </div>
              <div>
                <label className="block text-sm text-slate-400 mb-2">Quantity</label>
                <input
                  type="number"
                  value={quantity}
                  onChange={(e) => setQuantity(e.target.value)}
                  placeholder="Number of shares"
                  max={
                    positionsList.find((p) => p.symbol === selectedSymbol)?.shares || 0
                  }
                  className="w-full px-4 py-2 bg-slate-700 border border-slate-600 rounded text-white"
                />
                {selectedSymbol && positionsList.find((p) => p.symbol === selectedSymbol) && (
                  <p className="text-sm text-slate-400 mt-1">
                    Available: {positionsList.find((p) => p.symbol === selectedSymbol)?.shares} shares
                  </p>
                )}
              </div>
              <div className="flex gap-2">
                <button onClick={handleSellStock} className="flex-1 btn-primary bg-red-600 hover:bg-red-700">
                  Sell
                </button>
                <button
                  onClick={() => {
                    setShowSellDialog(false);
                    setSelectedSymbol('');
                    setQuantity('');
                  }}
                  className="flex-1 btn-secondary"
                >
                  Cancel
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
