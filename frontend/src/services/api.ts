import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 30 * 60 * 1000, // 30 minutes for long operations like training
});

// Add request interceptor to automatically include auth token
apiClient.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Types
export interface StockSymbol {
  symbol: string;
  name?: string;
}

export interface TrainingRequest {
  symbols?: string[];  // Optional - if not provided, trains on all available
  use_sample?: boolean;  // If true, train on sample (1000 stocks)
}

export interface TradingCycleRequest {
  symbols: string[];
  use_csv: boolean;
  risk_tolerance?: number;  // 0.0 (conservative) to 1.0 (aggressive)
}

export interface RiskSettings {
  risk_tolerance: number;
  buy_threshold_percent: number;
  sell_threshold_percent: number;
  min_confidence: number;
}

export interface SystemStatus {
  status: string;
  details: {
    is_running: boolean;
    total_trading_sessions: number;
    market_monitor: {
      is_trained: boolean;
      model_exists: boolean;
    };
    decision_maker: {
      is_trained: boolean;
      risk_tolerance: number;
      decision_history_size: number;
      feedback_data_size: number;
    };
    execution_agent: {
      capital: number;
      positions_count: number;
      total_trades: number;
      win_rate: number;
    };
  };
}

export interface Portfolio {
  cash: number;
  positions_value: number;
  total_value: number;
  profit_loss: number;
  profit_loss_percent: number;
  positions_count: number;
  positions: Record<string, any>;
}

export interface Performance {
  total_trades: number;
  winning_trades: number;
  losing_trades: number;
  win_rate: number;
  total_profit_loss: number;
  portfolio: Portfolio;
  pending_feedback_count: number;
  completed_feedback_count: number;
}

export interface Decision {
  symbol: string;
  decision: 'BUY' | 'SELL' | 'HOLD';
  confidence: number;
  predicted_change?: number;
  reasons?: string[];
  method?: string;
  timestamp: string;
}

export interface TradingSession {
  timestamp: string;
  symbols: string[];
  predictions: any[];
  decisions: Decision[];
  executions: any[];
  feedback: any[];
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
    feedback_items_processed: number;
    portfolio: Portfolio;
    performance: Performance;
  };
}

// API Methods
export const tradingApi = {
  // Train agents
  trainAgents: async (data: TrainingRequest = {}) => {
    const response = await apiClient.post('/api/trading/train', data);
    return response.data;
  },

  // Run trading cycle
  runTradingCycle: async (data: TradingCycleRequest) => {
    const response = await apiClient.post<TradingSession>('/api/trading/cycle/run', data);
    return response.data;
  },

  // Get system status
  getSystemStatus: async () => {
    const response = await apiClient.get<SystemStatus>('/api/trading/status');
    return response.data;
  },

  // Get trading sessions
  getTradingSessions: async (limit: number = 10) => {
    const response = await apiClient.get<{ total_sessions: number; sessions: TradingSession[] }>(
      `/api/trading/sessions?limit=${limit}`
    );
    return response.data;
  },

  // Get portfolio
  getPortfolio: async () => {
    const response = await apiClient.get<Portfolio>('/api/trading/portfolio');
    return response.data;
  },

  // Get performance
  getPerformance: async () => {
    const response = await apiClient.get<Performance>('/api/trading/performance');
    return response.data;
  },

  // Get risk settings
  getRiskSettings: async () => {
    const response = await apiClient.get<{ status: string; settings: RiskSettings }>('/api/trading/risk-settings');
    return response.data;
  },

  // Set risk settings
  setRiskSettings: async (riskTolerance: number) => {
    const response = await apiClient.post<{ status: string; settings: RiskSettings }>(
      '/api/trading/risk-settings',
      { risk_tolerance: riskTolerance }
    );
    return response.data;
  },

  // Get decision history
  getDecisionHistory: async (limit: number = 20) => {
    const response = await apiClient.get<{ total_decisions: number; decisions: Decision[] }>(
      `/api/trading/decisions/history?limit=${limit}`
    );
    return response.data;
  },

  // Get pending feedback
  getPendingFeedback: async () => {
    const response = await apiClient.get('/api/trading/feedback/pending');
    return response.data;
  },
};

// Market Data API
export const marketApi = {
  // Get latest stock data
  getLatestStock: async (symbol: string) => {
    const response = await apiClient.get(`/api/market/stocks/${symbol}/latest`);
    return response.data;
  },

  // Get stock history
  getStockHistory: async (symbol: string, days: number = 30) => {
    const response = await apiClient.get(`/api/market/stocks/${symbol}/history?days=${days}`);
    return response.data;
  },

  // Get all stocks
  getAllStocks: async () => {
    const response = await apiClient.get('/api/market/stocks');
    return response.data;
  },

  // Manual fetch
  manualFetch: async (symbol: string) => {
    const response = await apiClient.post(`/api/market/stocks/${symbol}/fetch`);
    return response.data;
  },

  // Get available CSV symbols
  getAvailableCsvSymbols: async () => {
    const response = await apiClient.get<{ count: number; symbols: string[] }>(
      '/api/market/stock/csv/available'
    );
    return response.data;
  },

  // Get all stocks with pagination and filters
  getAllStocksData: async (params: {
    page?: number;
    per_page?: number;
    search?: string;
    sort_by?: string;
    sort_order?: 'asc' | 'desc';
    min_price?: number;
    max_price?: number;
    min_change_pct?: number;
    max_change_pct?: number;
  } = {}) => {
    const queryParams = new URLSearchParams();
    if (params.page) queryParams.append('page', params.page.toString());
    if (params.per_page) queryParams.append('per_page', params.per_page.toString());
    if (params.search) queryParams.append('search', params.search);
    if (params.sort_by) queryParams.append('sort_by', params.sort_by);
    if (params.sort_order) queryParams.append('sort_order', params.sort_order);
    if (params.min_price !== undefined) queryParams.append('min_price', params.min_price.toString());
    if (params.max_price !== undefined) queryParams.append('max_price', params.max_price.toString());
    if (params.min_change_pct !== undefined) queryParams.append('min_change_pct', params.min_change_pct.toString());
    if (params.max_change_pct !== undefined) queryParams.append('max_change_pct', params.max_change_pct.toString());
    
    const response = await apiClient.get<StocksListResponse>(
      `/api/market/stocks/all?${queryParams.toString()}`
    );
    return response.data;
  },

  // Get single stock CSV data with history
  getStockCsvData: async (symbol: string, days: number = 365) => {
    const response = await apiClient.get<StockDetailResponse>(
      `/api/market/stock/csv/${symbol}?days=${days}`
    );
    return response.data;
  },
};

// Stock types
export interface StockData {
  symbol: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
  change: number;
  change_pct: number;
  week_52_high: number;
  week_52_low: number;
  avg_volume: number;
  total_records: number;
  first_date: string;
  last_date: string;
}

export interface StocksListResponse {
  stocks: StockData[];
  pagination: {
    page: number;
    per_page: number;
    total: number;
    total_pages: number;
  };
}

export interface StockHistoryRecord {
  date: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

export interface StockDetailResponse {
  symbol: string;
  current_price: number;
  change: number;
  change_pct: number;
  total_records: number;
  history: StockHistoryRecord[];
}

// Portfolio API - NEW
export interface PortfolioPosition {
  symbol: string;
  shares: number;
  avg_price: number;
  current_price: number;
  return_pct: number;
  position_value: number;
  buy_date: string;
}

export interface PortfolioAnalysisRequest {
  portfolio: {
    user_id: string;
    cash: number;
    positions: Record<string, { shares: number; avg_price: number; buy_date: string }>;
  };
  analyze_new_opportunities: boolean;
}

export interface PositionRecommendation {
  symbol: string;
  action: 'BUY' | 'SELL' | 'HOLD';
  reason: string;
  confidence: number;
  shares?: number;
  current_return?: number;
  current_price?: number;
  position_value?: number;
}

export interface NewOpportunity {
  symbol: string;
  predicted_change: number;
  confidence: number;
  reason: string;
  recommended_shares: number;
}

export interface PortfolioHealth {
  status: string;
  total_value: number;
  cash_percentage: number;
  num_positions: number;
  diversification_score: number;
  sector_distribution: Record<string, number>;
  top_performers: Array<{ symbol: string; return: number }>;
  underperformers: Array<{ symbol: string; return: number }>;
}

export interface SimilarStock {
  symbol: string;
  similarity_score: number;
  current_price: number;
  price_change_1d: number;
  similar_to: string[];
  predicted_change?: number;
  prediction_confidence?: number;
  direction?: string;
}

export const portfolioApi = {
  // Analyze portfolio with recommendations
  analyzePortfolio: async (data: PortfolioAnalysisRequest) => {
    const response = await apiClient.post<{
      status: string;
      portfolio_health: PortfolioHealth;
      position_recommendations: PositionRecommendation[];
      new_opportunities: NewOpportunity[];
    }>('/api/portfolio/analyze', data);
    return response.data;
  },

  // Discover similar stocks
  discoverSimilarStocks: async (portfolio_symbols: string[], top_n: number = 10) => {
    const response = await apiClient.post<{
      status: string;
      recommendations: SimilarStock[];
    }>('/api/portfolio/discover', {
      portfolio_symbols,
      exclude_sectors: [],
      top_n,
    });
    return response.data;
  },

  // Get current portfolio
  getCurrentPortfolio: async () => {
    const response = await apiClient.get('/api/users/me/portfolio');
    // Response has structure: { status, portfolio: {...} }
    return response.data.portfolio || response.data;
  },
};

// User API - NEW
export interface UserRegisterRequest {
  username: string;
  email: string;
  password: string;
  initial_capital?: number;
}

export interface UserLoginRequest {
  username: string;
  password: string;
}

export interface UserInfo {
  id: number;
  username: string;
  email: string;
  created_at: string;
}

export interface LoginResponse {
  access_token: string;
  token_type: string;
  user: UserInfo;
}

export const userApi = {
  // Register new user
  register: async (data: UserRegisterRequest) => {
    const response = await apiClient.post<UserInfo>('/api/users/register', data);
    return response.data;
  },

  // Login user
  login: async (data: UserLoginRequest) => {
    const response = await apiClient.post<LoginResponse>('/api/users/login', data);
    return response.data;
  },

  // Get current user info
  getMe: async () => {
    const response = await apiClient.get<UserInfo>('/api/users/me');
    return response.data;
  },

  // Get user portfolio
  getMyPortfolio: async () => {
    const response = await apiClient.get('/api/users/me/portfolio');
    return response.data.portfolio; // Extract portfolio from {status, portfolio}
  },

  // Buy stock
  buyStock: async (symbol: string, shares: number) => {
    const response = await apiClient.post('/api/users/me/portfolio/buy', { 
      symbol, 
      shares,
      price: 0 // Price will be fetched by backend
    });
    return response.data;
  },

  // Sell stock
  sellStock: async (symbol: string, shares: number) => {
    const response = await apiClient.post('/api/users/me/portfolio/sell', { 
      symbol, 
      shares,
      price: 0 // Price will be fetched by backend
    });
    return response.data;
  },

  // Get transactions
  getMyTransactions: async (limit: number = 50) => {
    const response = await apiClient.get('/api/users/me/transactions', {
      params: { limit },
    });
    return response.data;
  },
};

export default apiClient;
