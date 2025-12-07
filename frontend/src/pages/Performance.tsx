import React, { useEffect, useState } from 'react';
import { tradingApi, Performance as PerformanceType, Decision } from '../services/api';
import { BarChart3, TrendingUp, Target, Activity, RefreshCw } from 'lucide-react';
import { PieChart, Pie, Cell, ResponsiveContainer, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend } from 'recharts';

export default function Performance() {
  const [performance, setPerformance] = useState<PerformanceType | null>(null);
  const [decisions, setDecisions] = useState<Decision[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadPerformance();
  }, []);

  const loadPerformance = async () => {
    try {
      setLoading(true);
      setError(null);
      const [perfData, decisionsData] = await Promise.all([
        tradingApi.getPerformance(),
        tradingApi.getDecisionHistory(50),
      ]);
      setPerformance(perfData);
      setDecisions(decisionsData.decisions);
    } catch (err: any) {
      setError(err.message || 'Failed to load performance data');
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
        <p className="text-red-400">{error}</p>
      </div>
    );
  }

  const formatCurrency = (value: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
    }).format(value);
  };

  // Decision distribution data
  const decisionCounts = {
    BUY: decisions.filter((d) => d.decision === 'BUY').length,
    SELL: decisions.filter((d) => d.decision === 'SELL').length,
    HOLD: decisions.filter((d) => d.decision === 'HOLD').length,
  };

  const decisionChartData = [
    { name: 'BUY', value: decisionCounts.BUY, color: '#10b981' },
    { name: 'SELL', value: decisionCounts.SELL, color: '#ef4444' },
    { name: 'HOLD', value: decisionCounts.HOLD, color: '#6b7280' },
  ];

  // Win/Loss data
  const winLossData = [
    { name: 'Wins', value: performance?.winning_trades || 0, color: '#10b981' },
    { name: 'Losses', value: performance?.losing_trades || 0, color: '#ef4444' },
  ];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-white mb-2">Performance</h1>
          <p className="text-slate-400">Trading metrics and analytics</p>
        </div>
        <button onClick={loadPerformance} className="btn-secondary flex items-center gap-2">
          <RefreshCw className="w-4 h-4" />
          Refresh
        </button>
      </div>

      {/* Key Metrics */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <div className="card">
          <div className="flex items-center justify-between mb-2">
            <p className="text-slate-400 text-sm">Total Trades</p>
            <Activity className="w-5 h-5 text-blue-500" />
          </div>
          <p className="text-2xl font-bold text-white">{performance?.total_trades || 0}</p>
          <p className="text-sm text-slate-400 mt-1">
            {performance?.winning_trades}W / {performance?.losing_trades}L
          </p>
        </div>

        <div className="card">
          <div className="flex items-center justify-between mb-2">
            <p className="text-slate-400 text-sm">Win Rate</p>
            <Target className="w-5 h-5 text-green-500" />
          </div>
          <p className="text-2xl font-bold text-white">
            {(performance?.win_rate || 0).toFixed(1)}%
          </p>
          <p className="text-sm text-slate-400 mt-1">
            {performance?.winning_trades || 0} winning trades
          </p>
        </div>

        <div className="card">
          <div className="flex items-center justify-between mb-2">
            <p className="text-slate-400 text-sm">Total P&L</p>
            <TrendingUp className="w-5 h-5 text-purple-500" />
          </div>
          <p
            className={`text-2xl font-bold ${
              (performance?.total_profit_loss || 0) >= 0 ? 'text-green-400' : 'text-red-400'
            }`}
          >
            {formatCurrency(performance?.total_profit_loss || 0)}
          </p>
        </div>

        <div className="card">
          <div className="flex items-center justify-between mb-2">
            <p className="text-slate-400 text-sm">Feedback Collected</p>
            <BarChart3 className="w-5 h-5 text-yellow-500" />
          </div>
          <p className="text-2xl font-bold text-white">
            {performance?.completed_feedback_count || 0}
          </p>
          <p className="text-sm text-slate-400 mt-1">
            {performance?.pending_feedback_count || 0} pending
          </p>
        </div>
      </div>

      {/* Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Win/Loss Chart */}
        <div className="card">
          <h3 className="text-lg font-semibold text-white mb-4">Win/Loss Distribution</h3>
          <ResponsiveContainer width="100%" height={300}>
            <PieChart>
              <Pie
                data={winLossData}
                cx="50%"
                cy="50%"
                labelLine={false}
                label={(entry) => `${entry.name}: ${entry.value}`}
                outerRadius={100}
                fill="#8884d8"
                dataKey="value"
              >
                {winLossData.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={entry.color} />
                ))}
              </Pie>
              <Tooltip
                contentStyle={{
                  backgroundColor: '#1e293b',
                  border: '1px solid #334155',
                  borderRadius: '8px',
                }}
              />
            </PieChart>
          </ResponsiveContainer>
        </div>

        {/* Decision Distribution Chart */}
        <div className="card">
          <h3 className="text-lg font-semibold text-white mb-4">Decision Distribution</h3>
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={decisionChartData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
              <XAxis dataKey="name" stroke="#94a3b8" />
              <YAxis stroke="#94a3b8" />
              <Tooltip
                contentStyle={{
                  backgroundColor: '#1e293b',
                  border: '1px solid #334155',
                  borderRadius: '8px',
                }}
              />
              <Bar dataKey="value" fill="#3b82f6" radius={[8, 8, 0, 0]}>
                {decisionChartData.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={entry.color} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Recent Decisions */}
      <div className="card">
        <h3 className="text-lg font-semibold text-white mb-4">Recent Decisions</h3>
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="border-b border-slate-700">
                <th className="text-left py-3 px-4 text-slate-400 font-medium">Time</th>
                <th className="text-left py-3 px-4 text-slate-400 font-medium">Symbol</th>
                <th className="text-center py-3 px-4 text-slate-400 font-medium">Decision</th>
                <th className="text-right py-3 px-4 text-slate-400 font-medium">Confidence</th>
                <th className="text-right py-3 px-4 text-slate-400 font-medium">
                  Predicted Change
                </th>
                <th className="text-left py-3 px-4 text-slate-400 font-medium">Method</th>
              </tr>
            </thead>
            <tbody>
              {decisions.slice(0, 20).map((decision, index) => (
                <tr key={index} className="border-b border-slate-700/50">
                  <td className="py-3 px-4 text-slate-400 text-sm">
                    {new Date(decision.timestamp).toLocaleString()}
                  </td>
                  <td className="py-3 px-4 text-white font-semibold">{decision.symbol}</td>
                  <td className="py-3 px-4 text-center">
                    <span
                      className={`badge ${
                        decision.decision === 'BUY'
                          ? 'badge-success'
                          : decision.decision === 'SELL'
                          ? 'badge-danger'
                          : 'badge-info'
                      }`}
                    >
                      {decision.decision}
                    </span>
                  </td>
                  <td className="py-3 px-4 text-right text-white">
                    {(decision.confidence * 100).toFixed(0)}%
                  </td>
                  <td
                    className={`py-3 px-4 text-right ${
                      (decision.predicted_change || 0) >= 0 ? 'text-green-400' : 'text-red-400'
                    }`}
                  >
                    {decision.predicted_change !== undefined
                      ? `${decision.predicted_change >= 0 ? '+' : ''}${decision.predicted_change.toFixed(2)}%`
                      : 'N/A'}
                  </td>
                  <td className="py-3 px-4 text-slate-400 text-sm">
                    {decision.method === 'ml_model' ? (
                      <span className="badge badge-success">ML</span>
                    ) : (
                      <span className="badge badge-info">Rules</span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Statistics */}
      <div className="card">
        <h3 className="text-lg font-semibold text-white mb-4">Portfolio Statistics</h3>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-6">
          <div>
            <p className="text-sm text-slate-400 mb-1">Portfolio Value</p>
            <p className="text-xl font-bold text-white">
              {formatCurrency(performance?.portfolio.total_value || 0)}
            </p>
          </div>
          <div>
            <p className="text-sm text-slate-400 mb-1">Cash Balance</p>
            <p className="text-xl font-bold text-white">
              {formatCurrency(performance?.portfolio.cash || 0)}
            </p>
          </div>
          <div>
            <p className="text-sm text-slate-400 mb-1">Positions Value</p>
            <p className="text-xl font-bold text-white">
              {formatCurrency(performance?.portfolio.positions_value || 0)}
            </p>
          </div>
          <div>
            <p className="text-sm text-slate-400 mb-1">Active Positions</p>
            <p className="text-xl font-bold text-white">
              {performance?.portfolio.positions_count || 0}
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
