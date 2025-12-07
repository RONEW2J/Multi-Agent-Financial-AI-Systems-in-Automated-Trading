import React from 'react';
import { BrowserRouter as Router, Routes, Route, Link, useLocation, Navigate } from 'react-router-dom';
import { Activity, TrendingUp, DollarSign, BarChart3, Settings, Brain, Target, LogOut, User, LineChart, Workflow } from 'lucide-react';
import { AuthProvider, useAuth } from './contexts/AuthContext';
import ProtectedRoute from './components/ProtectedRoute';
import Dashboard from './pages/Dashboard';
import Trading from './pages/Trading';
import Portfolio from './pages/Portfolio';
import Performance from './pages/Performance';
import Training from './pages/Training';
import PortfolioAnalysis from './pages/PortfolioAnalysis';
import Stocks from './pages/Stocks';
import AgentFlow from './pages/AgentFlow';
import Login from './pages/Login';
import Register from './pages/Register';

function NavLink({ to, children, icon: Icon }: { to: string; children: React.ReactNode; icon: any }) {
  const location = useLocation();
  const isActive = location.pathname === to;

  return (
    <Link
      to={to}
      className={`flex items-center gap-3 px-4 py-3 rounded-lg transition-colors ${
        isActive
          ? 'bg-blue-600 text-white'
          : 'text-slate-300 hover:bg-slate-700 hover:text-white'
      }`}
    >
      <Icon className="w-5 h-5" />
      <span className="font-medium">{children}</span>
    </Link>
  );
}

function AppLayout() {
  const { user, logout } = useAuth();

  return (
    <div className="min-h-screen bg-slate-900">
      {/* Sidebar */}
      <aside className="fixed left-0 top-0 h-full w-64 bg-slate-800 border-r border-slate-700 p-6">
        <div className="mb-8">
          <div className="flex items-center gap-3 mb-2">
            <Brain className="w-8 h-8 text-blue-500" />
            <h1 className="text-xl font-bold text-white">AI Trading</h1>
          </div>
          <p className="text-xs text-slate-400">Multi-Agent System</p>
        </div>

        {/* User Info */}
        {user && (
          <div className="mb-6 p-3 bg-slate-700 rounded-lg">
            <div className="flex items-center gap-2 mb-2">
              <User className="w-4 h-4 text-blue-400" />
              <span className="text-sm text-white font-medium">{user.username}</span>
            </div>
            <p className="text-xs text-slate-400 truncate">{user.email}</p>
          </div>
        )}

        <nav className="space-y-2">
          <NavLink to="/dashboard" icon={Activity}>
            Dashboard
          </NavLink>
          <NavLink to="/stocks" icon={LineChart}>
            Stocks
          </NavLink>
          <NavLink to="/agents" icon={Workflow}>
            Agent Flow
          </NavLink>
          <NavLink to="/trading" icon={TrendingUp}>
            Trading
          </NavLink>
          <NavLink to="/portfolio" icon={DollarSign}>
            Portfolio
          </NavLink>
          <NavLink to="/analysis" icon={Target}>
            Analysis
          </NavLink>
          <NavLink to="/performance" icon={BarChart3}>
            Performance
          </NavLink>
          <NavLink to="/training" icon={Settings}>
            Training
          </NavLink>
        </nav>

        <div className="absolute bottom-6 left-6 right-6">
          {/* Logout Button */}
          <button
            onClick={logout}
            className="w-full flex items-center gap-3 px-4 py-3 rounded-lg transition-colors text-slate-300 hover:bg-red-600 hover:text-white mb-4"
          >
            <LogOut className="w-5 h-5" />
            <span className="font-medium">Logout</span>
          </button>

          {/* Status */}
          <div className="card p-4">
            <p className="text-xs text-slate-400 mb-1">System Status</p>
            <div className="flex items-center gap-2">
              <div className="w-2 h-2 rounded-full bg-green-500 animate-pulse"></div>
              <span className="text-sm text-white font-medium">Online</span>
            </div>
          </div>
        </div>
      </aside>

      {/* Main Content */}
      <main className="ml-64 p-8">
        <Routes>
          <Route path="/" element={<Navigate to="/dashboard" replace />} />
          <Route
            path="/dashboard"
            element={
              <ProtectedRoute>
                <Dashboard />
              </ProtectedRoute>
            }
          />
          <Route
            path="/trading"
            element={
              <ProtectedRoute>
                <Trading />
              </ProtectedRoute>
            }
          />
          <Route
            path="/stocks"
            element={
              <ProtectedRoute>
                <Stocks />
              </ProtectedRoute>
            }
          />
          <Route
            path="/agents"
            element={
              <ProtectedRoute>
                <AgentFlow />
              </ProtectedRoute>
            }
          />
          <Route
            path="/portfolio"
            element={
              <ProtectedRoute>
                <Portfolio />
              </ProtectedRoute>
            }
          />
          <Route
            path="/analysis"
            element={
              <ProtectedRoute>
                <PortfolioAnalysis />
              </ProtectedRoute>
            }
          />
          <Route
            path="/performance"
            element={
              <ProtectedRoute>
                <Performance />
              </ProtectedRoute>
            }
          />
          <Route
            path="/training"
            element={
              <ProtectedRoute>
                <Training />
              </ProtectedRoute>
            }
          />
        </Routes>
      </main>
    </div>
  );
}

function App() {
  return (
    <AuthProvider>
      <Router>
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route path="/register" element={<Register />} />
          <Route path="/*" element={<AppLayout />} />
        </Routes>
      </Router>
    </AuthProvider>
  );
}

export default App;
