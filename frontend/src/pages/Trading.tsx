import React, { useState, useEffect } from 'react';
import { tradingApi, marketApi, TradingSession } from '../services/api';
import { Play, Loader, CheckCircle, XCircle, TrendingUp, TrendingDown, Minus, RefreshCw } from 'lucide-react';

const POPULAR_STOCKS = [
  'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'META', 'TSLA', 'NVDA', 'JPM', 'V', 'WMT'
];

export default function Trading() {
  const [selectedSymbols, setSelectedSymbols] = useState<string[]>(['AAPL', 'MSFT', 'GOOGL']);
  const [customSymbol, setCustomSymbol] = useState('');
  const [useCsv, setUseCsv] = useState(true);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<TradingSession | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [availableSymbols, setAvailableSymbols] = useState<string[]>([]);
  const [loadingSymbols, setLoadingSymbols] = useState(false);

  // Load available CSV symbols on mount
  useEffect(() => {
    loadAvailableSymbols();
  }, []);

  const loadAvailableSymbols = async () => {
    setLoadingSymbols(true);
    try {
      const data = await marketApi.getAvailableCsvSymbols();
      setAvailableSymbols(data.symbols);
    } catch (err) {
      console.error('Failed to load available symbols:', err);
    } finally {
      setLoadingSymbols(false);
    }
  };

  const toggleSymbol = (symbol: string) => {
    setSelectedSymbols((prev) =>
      prev.includes(symbol)
        ? prev.filter((s) => s !== symbol)
        : [...prev, symbol]
    );
  };

  const addCustomSymbol = () => {
    const symbol = customSymbol.trim().toUpperCase();
    if (symbol && !selectedSymbols.includes(symbol)) {
      setSelectedSymbols([...selectedSymbols, symbol]);
      setCustomSymbol('');
    }
  };

  const runTradingCycle = async () => {
    if (selectedSymbols.length === 0) {
      setError('Please select at least one stock symbol');
      return;
    }

    setLoading(true);
    setError(null);
    setResult(null);

    try {
      const data = await tradingApi.runTradingCycle({
        symbols: selectedSymbols,
        use_csv: useCsv,
      });
      setResult(data);
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || 'Failed to run trading cycle');
    } finally {
      setLoading(false);
    }
  };

  const getDecisionIcon = (decision: string) => {
    switch (decision) {
      case 'BUY':
        return <TrendingUp className="w-5 h-5 text-green-400" />;
      case 'SELL':
        return <TrendingDown className="w-5 h-5 text-red-400" />;
      default:
        return <Minus className="w-5 h-5 text-gray-400" />;
    }
  };

  const getDecisionColor = (decision: string) => {
    switch (decision) {
      case 'BUY':
        return 'text-green-400';
      case 'SELL':
        return 'text-red-400';
      default:
        return 'text-gray-400';
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold text-white mb-2">Trading Control</h1>
        <p className="text-slate-400">Run trading cycles and view results</p>
      </div>

      {/* Trading Form */}
      <div className="card">
        <h2 className="text-xl font-semibold text-white mb-4">Configure Trading Cycle</h2>

        {/* Stock Selection */}
        <div className="mb-6">
          <div className="flex items-center justify-between mb-3">
            <label className="text-sm font-medium text-slate-300">
              Select Stocks ({selectedSymbols.length} selected)
            </label>
            <div className="flex items-center gap-2 text-sm text-slate-400">
              {loadingSymbols ? (
                <Loader className="w-4 h-4 animate-spin" />
              ) : (
                <>
                  <span>{availableSymbols.length} available in dataset</span>
                  <button
                    onClick={loadAvailableSymbols}
                    className="text-blue-400 hover:text-blue-300"
                    title="Refresh"
                  >
                    <RefreshCw className="w-4 h-4" />
                  </button>
                </>
              )}
            </div>
          </div>
          <div className="flex flex-wrap gap-2 mb-4">
            {POPULAR_STOCKS.map((symbol) => (
              <button
                key={symbol}
                onClick={() => toggleSymbol(symbol)}
                className={`px-4 py-2 rounded-lg font-medium transition-colors ${
                  selectedSymbols.includes(symbol)
                    ? 'bg-blue-600 text-white'
                    : 'bg-slate-700 text-slate-300 hover:bg-slate-600'
                }`}
              >
                {symbol}
              </button>
            ))}
          </div>

          {/* Custom Symbol */}
          <div className="space-y-2">
            <div className="flex gap-2">
              <input
                type="text"
                value={customSymbol}
                onChange={(e) => setCustomSymbol(e.target.value.toUpperCase())}
                onKeyPress={(e) => e.key === 'Enter' && addCustomSymbol()}
                placeholder="Search or type symbol..."
                className="input-field flex-1"
                list="available-symbols"
              />
              <button onClick={addCustomSymbol} className="btn-secondary">
                Add
              </button>
            </div>
            
            {/* Datalist for autocomplete */}
            <datalist id="available-symbols">
              {availableSymbols
                .filter((s) => !selectedSymbols.includes(s))
                .map((symbol) => (
                  <option key={symbol} value={symbol} />
                ))}
            </datalist>
            
            {/* Show filtered suggestions when typing */}
            {customSymbol && availableSymbols.length > 0 && (
              <div className="max-h-40 overflow-y-auto bg-slate-800 rounded border border-slate-700">
                {availableSymbols
                  .filter(
                    (s) =>
                      s.includes(customSymbol) &&
                      !selectedSymbols.includes(s)
                  )
                  .slice(0, 10)
                  .map((symbol) => (
                    <button
                      key={symbol}
                      onClick={() => {
                        setSelectedSymbols([...selectedSymbols, symbol]);
                        setCustomSymbol('');
                      }}
                      className="w-full text-left px-3 py-2 hover:bg-slate-700 text-slate-300 text-sm"
                    >
                      {symbol}
                    </button>
                  ))}
              </div>
            )}
          </div>

          {/* Selected Symbols */}
          {selectedSymbols.length > 0 && (
            <div className="mt-3 flex flex-wrap gap-2">
              {selectedSymbols.map((symbol) => (
                <span
                  key={symbol}
                  className="inline-flex items-center gap-2 bg-blue-900/30 text-blue-300 px-3 py-1 rounded-lg"
                >
                  {symbol}
                  <button
                    onClick={() => toggleSymbol(symbol)}
                    className="text-blue-400 hover:text-blue-200"
                  >
                    ×
                  </button>
                </span>
              ))}
            </div>
          )}
        </div>

        {/* Options */}
        <div className="mb-6">
          <label className="flex items-center gap-3 cursor-pointer">
            <input
              type="checkbox"
              checked={useCsv}
              onChange={(e) => setUseCsv(e.target.checked)}
              className="w-5 h-5 rounded border-slate-600 bg-slate-700 text-blue-600 focus:ring-2 focus:ring-blue-500"
            />
            <div>
              <span className="text-white font-medium">Use CSV Data</span>
              <p className="text-sm text-slate-400">Use historical CSV data instead of database</p>
            </div>
          </label>
        </div>

        {/* Actions */}
        <div className="flex gap-3">
          <button
            onClick={runTradingCycle}
            disabled={loading || selectedSymbols.length === 0}
            className="btn-primary flex items-center gap-2"
          >
            {loading ? (
              <>
                <Loader className="w-5 h-5 animate-spin" />
                Running...
              </>
            ) : (
              <>
                <Play className="w-5 h-5" />
                Run Trading Cycle
              </>
            )}
          </button>
        </div>
      </div>

      {/* Error */}
      {error && (
        <div className="card bg-red-900/20 border-red-800">
          <div className="flex items-center gap-3 text-red-400">
            <XCircle className="w-6 h-6" />
            <div>
              <h3 className="font-semibold">Error</h3>
              <p className="text-sm">{error}</p>
            </div>
          </div>
        </div>
      )}

      {/* Results */}
      {result && (
        <div className="space-y-6">
          {/* Summary */}
          <div className="card">
            <div className="flex items-center gap-3 mb-4">
              <CheckCircle className="w-6 h-6 text-green-500" />
              <h2 className="text-xl font-semibold text-white">Cycle Complete</h2>
            </div>

            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div>
                <p className="text-sm text-slate-400">Duration</p>
                <p className="text-lg font-semibold text-white">
                  {result.summary.duration_seconds.toFixed(1)}s
                </p>
              </div>
              <div>
                <p className="text-sm text-slate-400">Stocks Analyzed</p>
                <p className="text-lg font-semibold text-white">
                  {result.summary.stocks_analyzed}
                </p>
              </div>
              <div>
                <p className="text-sm text-slate-400">Predictions</p>
                <p className="text-lg font-semibold text-white">
                  {result.summary.predictions_made}
                </p>
              </div>
              <div>
                <p className="text-sm text-slate-400">Trades Executed</p>
                <p className="text-lg font-semibold text-white">
                  {result.summary.trades_executed}
                </p>
              </div>
            </div>
          </div>

          {/* Decisions */}
          <div className="card">
            <h3 className="text-lg font-semibold text-white mb-4">Decisions</h3>
            <div className="grid grid-cols-3 gap-4 mb-6">
              <div className="text-center p-4 bg-green-900/20 rounded-lg border border-green-800">
                <p className="text-3xl font-bold text-green-400">{result.summary.decisions.buy}</p>
                <p className="text-sm text-slate-400">BUY</p>
              </div>
              <div className="text-center p-4 bg-red-900/20 rounded-lg border border-red-800">
                <p className="text-3xl font-bold text-red-400">{result.summary.decisions.sell}</p>
                <p className="text-sm text-slate-400">SELL</p>
              </div>
              <div className="text-center p-4 bg-gray-900/20 rounded-lg border border-gray-800">
                <p className="text-3xl font-bold text-gray-400">{result.summary.decisions.hold}</p>
                <p className="text-sm text-slate-400">HOLD</p>
              </div>
            </div>

            {/* Decision Details */}
            <div className="space-y-3">
              {result.decisions.map((decision, index) => (
                <div key={index} className="bg-slate-700/30 rounded-lg p-4">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      {getDecisionIcon(decision.decision)}
                      <div>
                        <p className="font-semibold text-white">{decision.symbol}</p>
                        <p className="text-sm text-slate-400">
                          Confidence: {(decision.confidence * 100).toFixed(0)}%
                        </p>
                      </div>
                    </div>
                    <div className="text-right">
                      <p className={`text-lg font-bold ${getDecisionColor(decision.decision)}`}>
                        {decision.decision}
                      </p>
                      {decision.predicted_change !== undefined && (
                        <p className="text-sm text-slate-400">
                          {decision.predicted_change >= 0 ? '+' : ''}
                          {decision.predicted_change.toFixed(2)}%
                        </p>
                      )}
                    </div>
                  </div>
                  {decision.reasons && decision.reasons.length > 0 && (
                    <div className="mt-2 text-sm text-slate-400">
                      {decision.reasons.map((reason, i) => (
                        <p key={i}>• {reason}</p>
                      ))}
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>

          {/* Portfolio Update */}
          <div className="card">
            <h3 className="text-lg font-semibold text-white mb-4">Portfolio Update</h3>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div>
                <p className="text-sm text-slate-400">Total Value</p>
                <p className="text-lg font-semibold text-white">
                  ${result.summary.portfolio.total_value.toLocaleString()}
                </p>
              </div>
              <div>
                <p className="text-sm text-slate-400">P&L</p>
                <p
                  className={`text-lg font-semibold ${
                    result.summary.portfolio.profit_loss >= 0 ? 'text-green-400' : 'text-red-400'
                  }`}
                >
                  ${result.summary.portfolio.profit_loss.toFixed(2)} (
                  {result.summary.portfolio.profit_loss_percent.toFixed(2)}%)
                </p>
              </div>
              <div>
                <p className="text-sm text-slate-400">Cash</p>
                <p className="text-lg font-semibold text-white">
                  ${result.summary.portfolio.cash.toLocaleString()}
                </p>
              </div>
              <div>
                <p className="text-sm text-slate-400">Positions</p>
                <p className="text-lg font-semibold text-white">
                  {result.summary.portfolio.positions_count}
                </p>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
