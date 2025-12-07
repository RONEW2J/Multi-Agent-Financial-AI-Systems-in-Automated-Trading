import React, { useState, useEffect } from 'react';
import {
  Brain,
  TrendingUp,
  TrendingDown,
  Target,
  Activity,
  Wallet,
  RefreshCw,
  Play,
  ChevronRight,
  AlertCircle,
  CheckCircle2,
  Clock,
  BarChart2,
} from 'lucide-react';
import { tradingApi, portfolioApi } from '../services/api';

interface Prediction {
  symbol: string;
  status?: string;
  current_price: number;
  predicted_price: number;
  predicted_change_percent: number;
  direction?: string;
  confidence: number;
  rsi?: number;  // Legacy field
  technical_indicators?: {
    RSI?: number;
    MACD?: number;
    BB_Position?: number;
    Distance_MA20?: number;
  };
  timestamp?: string;
}

interface Decision {
  symbol: string;
  decision: 'BUY' | 'SELL' | 'HOLD';
  confidence: number;
  reasons?: string[];
  predicted_change?: number;
  method?: string;
  shares?: number;
  timestamp?: string;
}

interface Execution {
  symbol: string;
  action: string;
  shares?: number;
  price: number;
  total?: number;
  status: string;  // "EXECUTED", "FAILED", etc.
  action_taken?: string;  // "buy", "sell", "none"
  reason?: string;
  message?: string;
  confidence?: number;
  timestamp: string;
}

interface AgentFlowResult {
  status?: string;
  timestamp?: string;
  symbols: string[];
  predictions: Prediction[];
  decisions: Decision[];
  executions: Execution[];
  feedback?: any[];
  summary: {
    duration_seconds: number;
    stocks_analyzed: number;
    predictions_made: number;
    decisions: {
      buy: number;
      sell: number;
      hold: number;
    };
    trades_executed: number;
    feedback_items_processed?: number;
  };
}

const AgentStep = ({
  step,
  title,
  icon: Icon,
  status,
  children,
}: {
  step: number;
  title: string;
  icon: any;
  status: 'pending' | 'active' | 'completed' | 'error';
  children: React.ReactNode;
}) => {
  const statusColors = {
    pending: 'bg-slate-700 text-slate-400',
    active: 'bg-blue-600 text-white animate-pulse',
    completed: 'bg-green-600 text-white',
    error: 'bg-red-600 text-white',
  };

  return (
    <div className="relative">
      <div className="flex items-start gap-4">
        <div className={`flex-shrink-0 w-10 h-10 rounded-full flex items-center justify-center ${statusColors[status]}`}>
          {status === 'completed' ? (
            <CheckCircle2 className="w-5 h-5" />
          ) : status === 'active' ? (
            <Clock className="w-5 h-5" />
          ) : (
            <Icon className="w-5 h-5" />
          )}
        </div>
        <div className="flex-1">
          <div className="flex items-center gap-2 mb-2">
            <span className="text-xs text-slate-500">Step {step}</span>
            <h3 className="text-lg font-semibold text-white">{title}</h3>
          </div>
          <div className="bg-slate-800 rounded-lg p-4 border border-slate-700">
            {children}
          </div>
        </div>
      </div>
      {step < 4 && (
        <div className="absolute left-5 top-12 bottom-0 w-0.5 bg-slate-700 -translate-x-1/2" style={{ height: '24px' }} />
      )}
    </div>
  );
};

const PredictionCard = ({ prediction }: { prediction: Prediction }) => {
  const changePercent = prediction.predicted_change_percent ?? 0;
  const isPositive = changePercent > 0;
  const rsi = prediction.technical_indicators?.RSI ?? prediction.rsi ?? 50;
  
  return (
    <div className="bg-slate-900 rounded-lg p-3 border border-slate-600">
      <div className="flex items-center justify-between mb-2">
        <span className="font-bold text-white">{prediction.symbol}</span>
        <div className={`flex items-center gap-1 ${isPositive ? 'text-green-400' : 'text-red-400'}`}>
          {isPositive ? <TrendingUp className="w-4 h-4" /> : <TrendingDown className="w-4 h-4" />}
          <span className="font-semibold">{isPositive ? '+' : ''}{changePercent.toFixed(2)}%</span>
        </div>
      </div>
      <div className="grid grid-cols-2 gap-2 text-xs">
        <div>
          <span className="text-slate-400">Current: </span>
          <span className="text-white">${prediction.current_price?.toFixed(2) ?? 'N/A'}</span>
        </div>
        <div>
          <span className="text-slate-400">Predicted: </span>
          <span className="text-white">${prediction.predicted_price?.toFixed(2) ?? 'N/A'}</span>
        </div>
        <div>
          <span className="text-slate-400">Confidence: </span>
          <span className="text-blue-400">{((prediction.confidence ?? 0) * 100).toFixed(0)}%</span>
        </div>
        <div>
          <span className="text-slate-400">RSI: </span>
          <span className={rsi > 70 ? 'text-red-400' : rsi < 30 ? 'text-green-400' : 'text-white'}>
            {rsi.toFixed(0)}
          </span>
        </div>
      </div>
    </div>
  );
};

const DecisionCard = ({ decision }: { decision: Decision }) => {
  const decisionColors = {
    BUY: 'border-green-500 bg-green-900/20',
    SELL: 'border-red-500 bg-red-900/20',
    HOLD: 'border-yellow-500 bg-yellow-900/20',
  };

  const decisionIcons = {
    BUY: <TrendingUp className="w-5 h-5 text-green-400" />,
    SELL: <TrendingDown className="w-5 h-5 text-red-400" />,
    HOLD: <Target className="w-5 h-5 text-yellow-400" />,
  };

  return (
    <div className={`rounded-lg p-3 border-2 ${decisionColors[decision.decision]}`}>
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          {decisionIcons[decision.decision]}
          <span className="font-bold text-white">{decision.symbol}</span>
        </div>
        <span className={`px-2 py-1 rounded text-xs font-bold ${
          decision.decision === 'BUY' ? 'bg-green-600' :
          decision.decision === 'SELL' ? 'bg-red-600' : 'bg-yellow-600'
        } text-white`}>
          {decision.decision}
        </span>
      </div>
      <div className="space-y-1 text-xs">
        <div>
          <span className="text-slate-400">Predicted Change: </span>
          <span className={(decision.predicted_change || 0) > 0 ? 'text-green-400' : 'text-red-400'}>
            {(decision.predicted_change || 0) > 0 ? '+' : ''}{decision.predicted_change?.toFixed(2) || '0.00'}%
          </span>
        </div>
        <div>
          <span className="text-slate-400">Confidence: </span>
          <span className="text-blue-400">{(decision.confidence * 100).toFixed(0)}%</span>
        </div>
        <div>
          <span className="text-slate-400">Method: </span>
          <span className="text-slate-300">{decision.method}</span>
        </div>
        {decision.shares && decision.shares > 0 && (
          <div>
            <span className="text-slate-400">Recommended Shares: </span>
            <span className="text-white font-semibold">{decision.shares}</span>
          </div>
        )}
      </div>
      {decision.reasons && decision.reasons.length > 0 && (
        <div className="mt-2 pt-2 border-t border-slate-600">
          <p className="text-xs text-slate-400 mb-1">Reasons:</p>
          <ul className="text-xs text-slate-300 space-y-0.5">
            {decision.reasons.map((reason, idx) => (
              <li key={idx} className="flex items-start gap-1">
                <ChevronRight className="w-3 h-3 mt-0.5 text-slate-500" />
                {reason}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
};

const ExecutionCard = ({ execution }: { execution: Execution }) => {
  const isSuccess = execution.status === 'EXECUTED';
  const isHold = execution.action === 'HOLD';
  const hasShares = execution.shares && execution.shares > 0;
  
  // Determine card styling based on action type
  const getCardStyle = () => {
    if (isHold) return 'border-slate-500 bg-slate-800/40';
    if (!isSuccess) return 'border-red-500 bg-red-900/20';
    if (execution.action === 'BUY') return 'border-green-500 bg-green-900/20';
    if (execution.action === 'SELL') return 'border-orange-500 bg-orange-900/20';
    return 'border-slate-500 bg-slate-800/40';
  };
  
  const getActionBadgeStyle = () => {
    if (execution.action === 'BUY') return 'bg-green-600';
    if (execution.action === 'SELL') return 'bg-red-600';
    return 'bg-slate-600';
  };

  return (
    <div className={`rounded-lg p-3 border ${getCardStyle()}`}>
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          {isHold ? (
            <Clock className="w-4 h-4 text-slate-400" />
          ) : isSuccess ? (
            <CheckCircle2 className="w-4 h-4 text-green-400" />
          ) : (
            <AlertCircle className="w-4 h-4 text-red-400" />
          )}
          <span className="font-bold text-white">{execution.symbol}</span>
        </div>
        <span className={`px-2 py-1 rounded text-xs font-bold ${getActionBadgeStyle()} text-white`}>
          {execution.action}
        </span>
      </div>
      
      {isHold ? (
        // HOLD display - simplified
        <div className="text-xs">
          <div className="flex justify-between mb-1">
            <span className="text-slate-400">Price: </span>
            <span className="text-white">${execution.price?.toFixed(2)}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-slate-400">Status: </span>
            <span className="text-slate-300">No action needed</span>
          </div>
        </div>
      ) : (
        // BUY/SELL display - full details
        <div className="grid grid-cols-2 gap-2 text-xs">
          {hasShares && (
            <div>
              <span className="text-slate-400">Shares: </span>
              <span className="text-white">{execution.shares}</span>
            </div>
          )}
          <div>
            <span className="text-slate-400">Price: </span>
            <span className="text-white">${execution.price?.toFixed(2)}</span>
          </div>
          {execution.total && (
            <div>
              <span className="text-slate-400">Total: </span>
              <span className="text-white font-semibold">${execution.total?.toFixed(2)}</span>
            </div>
          )}
          <div>
            <span className="text-slate-400">Status: </span>
            <span className={isSuccess ? 'text-green-400' : 'text-red-400'}>
              {isSuccess ? 'Executed' : 'Failed'}
            </span>
          </div>
        </div>
      )}
      
      {(execution.reason || execution.message) && (
        <p className="mt-2 text-xs text-slate-400 italic">
          {execution.reason || execution.message}
        </p>
      )}
    </div>
  );
};

export default function AgentFlow() {
  const [symbols, setSymbols] = useState('AAPL, GOOGL, MSFT');
  const [loading, setLoading] = useState(false);
  const [currentStep, setCurrentStep] = useState<number>(0);
  const [result, setResult] = useState<AgentFlowResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [portfolio, setPortfolio] = useState<any>(null);
  const [riskTolerance, setRiskTolerance] = useState<number>(0.7);
  const [riskSettings, setRiskSettings] = useState<any>(null);

  useEffect(() => {
    loadPortfolio();
    loadRiskSettings();
  }, []);

  const loadPortfolio = async () => {
    try {
      const data = await portfolioApi.getCurrentPortfolio();
      setPortfolio(data);
    } catch (err) {
      console.error('Failed to load portfolio:', err);
    }
  };

  const loadRiskSettings = async () => {
    try {
      const data = await tradingApi.getRiskSettings();
      setRiskSettings(data.settings);
      setRiskTolerance(data.settings.risk_tolerance);
    } catch (err) {
      console.error('Failed to load risk settings:', err);
    }
  };

  const runTradingCycle = async () => {
    if (!symbols.trim()) {
      setError('Please enter at least one stock symbol');
      return;
    }

    setLoading(true);
    setError(null);
    setResult(null);
    setCurrentStep(1);

    try {
      // Simulate step progression for better UX
      const symbolList = symbols.split(',').map(s => s.trim().toUpperCase()).filter(Boolean);
      
      // Step 1: Market Monitor (predictions)
      setCurrentStep(1);
      await new Promise(resolve => setTimeout(resolve, 500));
      
      // Step 2: Decision Maker
      setCurrentStep(2);
      await new Promise(resolve => setTimeout(resolve, 500));
      
      // Step 3: Execution Agent
      setCurrentStep(3);
      
      // Run the actual trading cycle with risk tolerance
      const cycleResult = await tradingApi.runTradingCycle({
        symbols: symbolList,
        use_csv: true,
        risk_tolerance: riskTolerance,
      });

      // Step 4: Complete
      setCurrentStep(4);
      setResult(cycleResult);
      
      // Reload portfolio and risk settings after trading
      await loadPortfolio();
      await loadRiskSettings();
      
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || 'Trading cycle failed');
      setCurrentStep(0);
    } finally {
      setLoading(false);
    }
  };

  const getStepStatus = (step: number): 'pending' | 'active' | 'completed' | 'error' => {
    if (error && currentStep === step) return 'error';
    if (currentStep === step && loading) return 'active';
    if (currentStep > step || (result && step <= 4)) return 'completed';
    return 'pending';
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-white mb-2">Agent Trading Flow</h1>
          <p className="text-slate-400">Watch the multi-agent system analyze, decide, and execute trades</p>
        </div>
      </div>

      {/* Portfolio Summary */}
      {portfolio && (
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <div className="card">
            <div className="flex items-center gap-2 mb-1">
              <Wallet className="w-4 h-4 text-blue-400" />
              <span className="text-sm text-slate-400">Total Value</span>
            </div>
            <p className="text-xl font-bold text-white">${portfolio.total_value?.toFixed(2) || '0.00'}</p>
          </div>
          <div className="card">
            <div className="flex items-center gap-2 mb-1">
              <Activity className="w-4 h-4 text-green-400" />
              <span className="text-sm text-slate-400">Cash Available</span>
            </div>
            <p className="text-xl font-bold text-white">${portfolio.cash?.toFixed(2) || '0.00'}</p>
          </div>
          <div className="card">
            <div className="flex items-center gap-2 mb-1">
              <BarChart2 className="w-4 h-4 text-purple-400" />
              <span className="text-sm text-slate-400">Positions</span>
            </div>
            <p className="text-xl font-bold text-white">{portfolio.positions?.length || 0}</p>
          </div>
          <div className="card">
            <div className="flex items-center gap-2 mb-1">
              <TrendingUp className="w-4 h-4 text-yellow-400" />
              <span className="text-sm text-slate-400">Total Return</span>
            </div>
            <p className={`text-xl font-bold ${portfolio.total_return_pct >= 0 ? 'text-green-400' : 'text-red-400'}`}>
              {portfolio.total_return_pct >= 0 ? '+' : ''}{portfolio.total_return_pct?.toFixed(2) || '0.00'}%
            </p>
          </div>
        </div>
      )}

      {/* Risk Settings */}
      <div className="card">
        <h2 className="text-lg font-semibold text-white mb-4">Risk Settings</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div>
            <div className="flex items-center justify-between mb-2">
              <label className="text-sm text-slate-400">Risk Tolerance</label>
              <span className={`text-sm font-semibold ${
                riskTolerance <= 0.3 ? 'text-green-400' : 
                riskTolerance <= 0.7 ? 'text-yellow-400' : 'text-red-400'
              }`}>
                {riskTolerance <= 0.3 ? 'Conservative' : riskTolerance <= 0.7 ? 'Moderate' : 'Aggressive'}
                ({(riskTolerance * 100).toFixed(0)}%)
              </span>
            </div>
            <input
              type="range"
              min="0"
              max="1"
              step="0.1"
              value={riskTolerance}
              onChange={(e) => setRiskTolerance(parseFloat(e.target.value))}
              className="w-full h-2 bg-slate-700 rounded-lg appearance-none cursor-pointer accent-blue-500"
              disabled={loading}
            />
            <div className="flex justify-between text-xs text-slate-500 mt-1">
              <span>Conservative</span>
              <span>Moderate</span>
              <span>Aggressive</span>
            </div>
          </div>
          
          {riskSettings && (
            <div className="bg-slate-800 rounded-lg p-4">
              <p className="text-xs text-slate-400 mb-2">Current Thresholds</p>
              <div className="grid grid-cols-3 gap-2 text-xs">
                <div>
                  <p className="text-slate-500">BUY if &gt;</p>
                  <p className="text-green-400 font-semibold">{riskSettings.buy_threshold_percent?.toFixed(2)}%</p>
                </div>
                <div>
                  <p className="text-slate-500">SELL if &lt;</p>
                  <p className="text-red-400 font-semibold">{riskSettings.sell_threshold_percent?.toFixed(2)}%</p>
                </div>
                <div>
                  <p className="text-slate-500">Min Conf.</p>
                  <p className="text-blue-400 font-semibold">{(riskSettings.min_confidence * 100)?.toFixed(0)}%</p>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Input Section */}
      <div className="card">
        <h2 className="text-lg font-semibold text-white mb-4">Run Trading Cycle</h2>
        <div className="flex gap-4">
          <input
            type="text"
            value={symbols}
            onChange={(e) => setSymbols(e.target.value)}
            placeholder="Enter symbols (e.g., AAPL, GOOGL, MSFT)"
            className="flex-1 px-4 py-3 bg-slate-800 border border-slate-600 rounded-lg text-white placeholder-slate-400 focus:outline-none focus:border-blue-500"
            disabled={loading}
          />
          <button
            onClick={runTradingCycle}
            disabled={loading}
            className="btn-primary flex items-center gap-2 px-6"
          >
            {loading ? (
              <>
                <RefreshCw className="w-4 h-4 animate-spin" />
                Processing...
              </>
            ) : (
              <>
                <Play className="w-4 h-4" />
                Run Cycle
              </>
            )}
          </button>
        </div>
        {error && (
          <div className="mt-4 p-3 bg-red-900/30 border border-red-700 rounded-lg text-red-400 flex items-center gap-2">
            <AlertCircle className="w-4 h-4" />
            {error}
          </div>
        )}
      </div>

      {/* Agent Flow Steps */}
      <div className="card">
        <h2 className="text-lg font-semibold text-white mb-6">Trading Pipeline</h2>
        
        <div className="space-y-6">
          {/* Step 1: Market Monitor */}
          <AgentStep
            step={1}
            title="Market Monitor - Price Prediction"
            icon={Brain}
            status={getStepStatus(1)}
          >
            {result?.predictions && result.predictions.length > 0 ? (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
                {result.predictions.map((pred, idx) => (
                  <PredictionCard key={idx} prediction={pred} />
                ))}
              </div>
            ) : (
              <div className="text-slate-400 text-sm">
                {loading && currentStep >= 1 ? (
                  <div className="flex items-center gap-2">
                    <RefreshCw className="w-4 h-4 animate-spin" />
                    Analyzing market data and predicting price movements...
                  </div>
                ) : (
                  <p>The Market Monitor agent uses a trained Random Forest model to predict stock price changes based on technical indicators (RSI, Moving Averages, Volume trends).</p>
                )}
              </div>
            )}
          </AgentStep>

          {/* Step 2: Decision Maker */}
          <AgentStep
            step={2}
            title="Decision Maker - Trading Decisions"
            icon={Target}
            status={getStepStatus(2)}
          >
            {result?.decisions && result.decisions.length > 0 ? (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
                {result.decisions.map((dec, idx) => (
                  <DecisionCard key={idx} decision={dec} />
                ))}
              </div>
            ) : (
              <div className="text-slate-400 text-sm">
                {loading && currentStep >= 2 ? (
                  <div className="flex items-center gap-2">
                    <RefreshCw className="w-4 h-4 animate-spin" />
                    Evaluating predictions and making BUY/SELL/HOLD decisions...
                  </div>
                ) : (
                  <p>The Decision Maker applies risk-based rules to predictions. It considers RSI levels (overbought/oversold), prediction confidence, and portfolio constraints to make trading decisions.</p>
                )}
              </div>
            )}
            {result?.summary && (
              <div className="mt-3 pt-3 border-t border-slate-600 flex gap-4 text-sm">
                <span className="text-green-400">
                  BUY: {result.summary.decisions?.buy || 0}
                </span>
                <span className="text-red-400">
                  SELL: {result.summary.decisions?.sell || 0}
                </span>
                <span className="text-yellow-400">
                  HOLD: {result.summary.decisions?.hold || 0}
                </span>
              </div>
            )}
          </AgentStep>

          {/* Step 3: Execution Agent */}
          <AgentStep
            step={3}
            title="Execution Agent - Trade Execution"
            icon={Activity}
            status={getStepStatus(3)}
          >
            {result?.executions && result.executions.length > 0 ? (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
                {result.executions.map((exec, idx) => (
                  <ExecutionCard key={idx} execution={exec} />
                ))}
              </div>
            ) : result ? (
              <div className="text-slate-400 text-sm">
                <p>No trades were executed. This happens when:</p>
                <ul className="list-disc list-inside mt-2">
                  <li>All decisions were HOLD</li>
                  <li>Insufficient cash for BUY orders</li>
                  <li>No positions to SELL</li>
                </ul>
              </div>
            ) : (
              <div className="text-slate-400 text-sm">
                {loading && currentStep >= 3 ? (
                  <div className="flex items-center gap-2">
                    <RefreshCw className="w-4 h-4 animate-spin" />
                    Executing trades in your portfolio...
                  </div>
                ) : (
                  <p>The Execution Agent executes approved trades in your portfolio, managing position sizes and ensuring sufficient funds are available.</p>
                )}
              </div>
            )}
            {result?.summary && (
              <div className="mt-3 pt-3 border-t border-slate-600 text-sm">
                <span className="text-blue-400">
                  Trades Executed: {result.summary.trades_executed || 0}
                </span>
              </div>
            )}
          </AgentStep>

          {/* Step 4: Summary */}
          <AgentStep
            step={4}
            title="Cycle Complete - Summary"
            icon={CheckCircle2}
            status={getStepStatus(4)}
          >
            {result?.summary ? (
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <div className="text-center p-3 bg-slate-900 rounded-lg">
                  <p className="text-2xl font-bold text-white">{result.summary.stocks_analyzed || 0}</p>
                  <p className="text-xs text-slate-400">Stocks Analyzed</p>
                </div>
                <div className="text-center p-3 bg-slate-900 rounded-lg">
                  <p className="text-2xl font-bold text-white">{result.summary.predictions_made || 0}</p>
                  <p className="text-xs text-slate-400">Predictions Made</p>
                </div>
                <div className="text-center p-3 bg-slate-900 rounded-lg">
                  <p className="text-2xl font-bold text-white">{result.summary.trades_executed || 0}</p>
                  <p className="text-xs text-slate-400">Trades Executed</p>
                </div>
                <div className="text-center p-3 bg-slate-900 rounded-lg">
                  <p className="text-2xl font-bold text-white">{result.summary.duration_seconds?.toFixed(1) || 0}s</p>
                  <p className="text-xs text-slate-400">Duration</p>
                </div>
              </div>
            ) : (
              <div className="text-slate-400 text-sm">
                {loading ? (
                  <div className="flex items-center gap-2">
                    <RefreshCw className="w-4 h-4 animate-spin" />
                    Finalizing cycle and recording feedback...
                  </div>
                ) : (
                  <p>Cycle summary will appear here after completion, showing overall performance and feedback for learning.</p>
                )}
              </div>
            )}
          </AgentStep>
        </div>
      </div>
    </div>
  );
}
