import React, { useEffect, useState } from 'react';
import { tradingApi, SystemStatus, Portfolio, Performance } from '../services/api';
import { Activity, TrendingUp, DollarSign, Target, Brain, Zap, AlertCircle } from 'lucide-react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';

export default function Dashboard() {
  const [status, setStatus] = useState<SystemStatus | null>(null);
  const [portfolio, setPortfolio] = useState<Portfolio | null>(null);
  const [performance, setPerformance] = useState<Performance | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadDashboardData();
    const interval = setInterval(loadDashboardData, 10000); // Refresh every 10s
    return () => clearInterval(interval);
  }, []);

  const loadDashboardData = async () => {
    try {
      setError(null);
      const [statusData, portfolioData, performanceData] = await Promise.all([
        tradingApi.getSystemStatus(),
        tradingApi.getPortfolio(),
        tradingApi.getPerformance(),
      ]);
      setStatus(statusData);
      setPortfolio(portfolioData);
      setPerformance(performanceData);
    } catch (err: any) {
      setError(err.message || 'Failed to load dashboard data');
    } finally {
      setLoading(false);
    }
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
        <div className="flex items-center gap-3 text-red-400">
          <AlertCircle className="w-6 h-6" />
          <div>
            <h3 className="font-semibold">Error Loading Dashboard</h3>
            <p className="text-sm">{error}</p>
          </div>
        </div>
      </div>
    );
  }

  const formatCurrency = (value: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
    }).format(value);
  };

  const formatPercent = (value: number) => {
    return `${value >= 0 ? '+' : ''}${value.toFixed(2)}%`;
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold text-white mb-2">Dashboard</h1>
        <p className="text-slate-400">Overview of your AI trading system</p>
      </div>

      {/* Key Metrics */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <div className="card">
          <div className="flex items-center justify-between mb-2">
            <p className="text-slate-400 text-sm">Portfolio Value</p>
            <DollarSign className="w-5 h-5 text-blue-500" />
          </div>
          <p className="text-2xl font-bold text-white">{formatCurrency(portfolio?.total_value || 0)}</p>
          <p className={`text-sm mt-1 ${(portfolio?.profit_loss_percent || 0) >= 0 ? 'text-green-400' : 'text-red-400'}`}>
            {formatPercent(portfolio?.profit_loss_percent || 0)}
          </p>
        </div>

        <div className="card">
          <div className="flex items-center justify-between mb-2">
            <p className="text-slate-400 text-sm">Total Trades</p>
            <Activity className="w-5 h-5 text-purple-500" />
          </div>
          <p className="text-2xl font-bold text-white">{performance?.total_trades || 0}</p>
          <p className="text-sm text-slate-400 mt-1">
            {performance?.winning_trades || 0}W / {performance?.losing_trades || 0}L
          </p>
        </div>

        <div className="card">
          <div className="flex items-center justify-between mb-2">
            <p className="text-slate-400 text-sm">Win Rate</p>
            <Target className="w-5 h-5 text-green-500" />
          </div>
          <p className="text-2xl font-bold text-white">{(performance?.win_rate || 0).toFixed(1)}%</p>
          <p className="text-sm text-slate-400 mt-1">
            {performance?.winning_trades || 0} wins
          </p>
        </div>

        <div className="card">
          <div className="flex items-center justify-between mb-2">
            <p className="text-slate-400 text-sm">Active Positions</p>
            <TrendingUp className="w-5 h-5 text-yellow-500" />
          </div>
          <p className="text-2xl font-bold text-white">{portfolio?.positions_count || 0}</p>
          <p className="text-sm text-slate-400 mt-1">
            {formatCurrency(portfolio?.positions_value || 0)}
          </p>
        </div>
      </div>

      {/* System Status */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Market Monitor */}
        <div className="card">
          <div className="flex items-center gap-3 mb-4">
            <div className="p-2 bg-blue-900/30 rounded-lg">
              <Brain className="w-6 h-6 text-blue-400" />
            </div>
            <div>
              <h3 className="text-white font-semibold">Market Monitor</h3>
              <p className="text-xs text-slate-400">AI Predictions</p>
            </div>
          </div>
          <div className="space-y-2">
            <div className="flex justify-between items-center">
              <span className="text-sm text-slate-400">Status</span>
              <span className={`badge ${status?.details.market_monitor.is_trained ? 'badge-success' : 'badge-warning'}`}>
                {status?.details.market_monitor.is_trained ? 'Trained' : 'Not Trained'}
              </span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-sm text-slate-400">Model</span>
              <span className="text-sm text-white">
                {status?.details.market_monitor.model_exists ? 'Loaded' : 'None'}
              </span>
            </div>
          </div>
        </div>

        {/* Decision Maker */}
        <div className="card">
          <div className="flex items-center gap-3 mb-4">
            <div className="p-2 bg-purple-900/30 rounded-lg">
              <Zap className="w-6 h-6 text-purple-400" />
            </div>
            <div>
              <h3 className="text-white font-semibold">Decision Maker</h3>
              <p className="text-xs text-slate-400">Trading Decisions</p>
            </div>
          </div>
          <div className="space-y-2">
            <div className="flex justify-between items-center">
              <span className="text-sm text-slate-400">Status</span>
              <span className={`badge ${status?.details.decision_maker.is_trained ? 'badge-success' : 'badge-warning'}`}>
                {status?.details.decision_maker.is_trained ? 'Trained' : 'Rule-Based'}
              </span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-sm text-slate-400">Risk Tolerance</span>
              <span className="text-sm text-white">
                {((status?.details.decision_maker.risk_tolerance || 0) * 100).toFixed(0)}%
              </span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-sm text-slate-400">Feedback Data</span>
              <span className="text-sm text-white">
                {status?.details.decision_maker.feedback_data_size || 0} samples
              </span>
            </div>
          </div>
        </div>

        {/* Execution Agent */}
        <div className="card">
          <div className="flex items-center gap-3 mb-4">
            <div className="p-2 bg-green-900/30 rounded-lg">
              <Activity className="w-6 h-6 text-green-400" />
            </div>
            <div>
              <h3 className="text-white font-semibold">Execution Agent</h3>
              <p className="text-xs text-slate-400">Trade Execution</p>
            </div>
          </div>
          <div className="space-y-2">
            <div className="flex justify-between items-center">
              <span className="text-sm text-slate-400">Capital</span>
              <span className="text-sm text-white">
                {formatCurrency(status?.details.execution_agent.capital || 0)}
              </span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-sm text-slate-400">Positions</span>
              <span className="text-sm text-white">
                {status?.details.execution_agent.positions_count || 0}
              </span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-sm text-slate-400">Win Rate</span>
              <span className="text-sm text-white">
                {(status?.details.execution_agent.win_rate || 0).toFixed(1)}%
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* Recent Activity */}
      <div className="card">
        <h3 className="text-xl font-semibold text-white mb-4">System Health</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div>
            <p className="text-sm text-slate-400 mb-2">Trading Sessions</p>
            <p className="text-3xl font-bold text-white">
              {status?.details.total_trading_sessions || 0}
            </p>
          </div>
          <div>
            <p className="text-sm text-slate-400 mb-2">System Status</p>
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 rounded-full bg-green-500 animate-pulse"></div>
              <span className="text-lg font-semibold text-white">Operational</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
