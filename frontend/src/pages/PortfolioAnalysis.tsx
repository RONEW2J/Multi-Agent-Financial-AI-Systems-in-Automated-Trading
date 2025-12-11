import React, { useState, useEffect } from 'react';
import {
  Container,
  Typography,
  Paper,
  Box,
  Button,
  CircularProgress,
  Alert,
  Grid,
  Card,
  CardContent,
  Chip,
  Divider,
  LinearProgress,
} from '@mui/material';
import {
  TrendingUp,
  TrendingDown,
  Remove,
  Timeline,
  Assessment,
  Explore,
} from '@mui/icons-material';
import { portfolioApi, tradingApi, PortfolioPosition } from '../services/api';

const PortfolioAnalysis: React.FC = () => {
  const [loading, setLoading] = useState(false);
  const [portfolio, setPortfolio] = useState<any>(null);
  const [analysis, setAnalysis] = useState<any>(null);
  const [similarStocks, setSimilarStocks] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadPortfolio();
  }, []);

  const loadPortfolio = async () => {
    try {
      setLoading(true);
      setError(null);
      
      // Get current portfolio
      const data = await portfolioApi.getCurrentPortfolio();
      setPortfolio(data);
      
    } catch (err: any) {
      setError(err.message || 'Failed to load portfolio');
    } finally {
      setLoading(false);
    }
  };

  const analyzePortfolio = async () => {
    if (!portfolio || !portfolio.positions || portfolio.positions.length === 0) return;
    
    try {
      setLoading(true);
      setError(null);
      
      // Convert portfolio positions array to object format expected by API
      const positions: Record<string, any> = {};
      portfolio.positions.forEach((pos: any) => {
        positions[pos.symbol] = {
          shares: pos.shares,
          avg_price: pos.avg_price,
          buy_date: pos.buy_date,
        };
      });
      
      const analysisData = await portfolioApi.analyzePortfolio({
        portfolio: {
          user_id: String(portfolio.user_id || 'global'),
          cash: portfolio.cash,
          positions,
        },
        analyze_new_opportunities: true,
      });
      
      setAnalysis(analysisData);
      
    } catch (err: any) {
      setError(err.message || 'Failed to analyze portfolio');
    } finally {
      setLoading(false);
    }
  };

  const discoverSimilar = async () => {
    if (!portfolio || !portfolio.positions || portfolio.positions.length === 0) return;
    
    try {
      setLoading(true);
      setError(null);
      
      const symbols = portfolio.positions.map((p: any) => p.symbol);
      const data = await portfolioApi.discoverSimilarStocks(symbols, 10);
      
      setSimilarStocks(data);
      
    } catch (err: any) {
      setError(err.message || 'Failed to discover similar stocks');
    } finally {
      setLoading(false);
    }
  };

  const getActionColor = (action: string) => {
    switch (action) {
      case 'BUY':
        return 'success';
      case 'SELL':
        return 'error';
      default:
        return 'default';
    }
  };

  const getActionIcon = (action: string) => {
    switch (action) {
      case 'BUY':
        return <TrendingUp />;
      case 'SELL':
        return <TrendingDown />;
      default:
        return <Remove />;
    }
  };

  return (
    <Container maxWidth="xl">
      <Box sx={{ py: 4 }}>
        <Typography variant="h4" gutterBottom sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <Assessment /> Portfolio Analysis & Recommendations
        </Typography>

        {error && (
          <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>
            {error}
          </Alert>
        )}

        {/* Portfolio Overview */}
        {portfolio && (
          <Paper elevation={3} sx={{ p: 3, mb: 3 }}>
            <Typography variant="h6" gutterBottom>
              Current Portfolio
            </Typography>
            <Grid container spacing={2} sx={{ mb: 2 }}>
              <Grid item xs={12} md={3}>
                <Card variant="outlined">
                  <CardContent>
                    <Typography color="textSecondary" gutterBottom>
                      Total Value
                    </Typography>
                    <Typography variant="h5">
                      ${portfolio.total_value?.toFixed(2) || '0.00'}
                    </Typography>
                  </CardContent>
                </Card>
              </Grid>
              <Grid item xs={12} md={3}>
                <Card variant="outlined">
                  <CardContent>
                    <Typography color="textSecondary" gutterBottom>
                      Cash
                    </Typography>
                    <Typography variant="h5">
                      ${portfolio.cash?.toFixed(2) || '0.00'}
                    </Typography>
                  </CardContent>
                </Card>
              </Grid>
              <Grid item xs={12} md={3}>
                <Card variant="outlined">
                  <CardContent>
                    <Typography color="textSecondary" gutterBottom>
                      Positions Value
                    </Typography>
                    <Typography variant="h5">
                      ${portfolio.current_positions_value?.toFixed(2) || '0.00'}
                    </Typography>
                  </CardContent>
                </Card>
              </Grid>
              <Grid item xs={12} md={3}>
                <Card variant="outlined">
                  <CardContent>
                    <Typography color="textSecondary" gutterBottom>
                      Positions
                    </Typography>
                    <Typography variant="h5">
                      {portfolio.positions?.length || 0}
                    </Typography>
                  </CardContent>
                </Card>
              </Grid>
            </Grid>

            <Box sx={{ display: 'flex', gap: 2 }}>
              <Button
                variant="contained"
                startIcon={<Timeline />}
                onClick={analyzePortfolio}
                disabled={loading || !portfolio.positions || portfolio.positions.length === 0}
              >
                Analyze Portfolio
              </Button>
              <Button
                variant="outlined"
                startIcon={<Explore />}
                onClick={discoverSimilar}
                disabled={loading || !portfolio.positions || portfolio.positions.length === 0}
              >
                Discover Similar Stocks
              </Button>
            </Box>
          </Paper>
        )}

        {loading && (
          <Box sx={{ display: 'flex', justifyContent: 'center', my: 4 }}>
            <CircularProgress />
          </Box>
        )}

        {/* Portfolio Health */}
        {analysis && analysis.portfolio_health && (
          <Paper elevation={3} sx={{ p: 3, mb: 3 }}>
            <Typography variant="h6" gutterBottom>
              Portfolio Health
            </Typography>
            <Grid container spacing={2}>
              <Grid item xs={12} md={6}>
                <Typography variant="subtitle2" color="textSecondary">
                  Status
                </Typography>
                <Chip
                  label={analysis.portfolio_health.status}
                  color={analysis.portfolio_health.status === 'healthy' ? 'success' : 'warning'}
                  sx={{ mb: 2 }}
                />
                
                <Typography variant="subtitle2" color="textSecondary" gutterBottom>
                  Diversification Score
                </Typography>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
                  <LinearProgress
                    variant="determinate"
                    value={analysis.portfolio_health.diversification_score * 100}
                    sx={{ flexGrow: 1, height: 8, borderRadius: 4 }}
                  />
                  <Typography variant="body2">
                    {(analysis.portfolio_health.diversification_score * 100).toFixed(0)}%
                  </Typography>
                </Box>
              </Grid>
              
              <Grid item xs={12} md={6}>
                <Typography variant="subtitle2" color="textSecondary" gutterBottom>
                  Sector Distribution
                </Typography>
                {Object.entries(analysis.portfolio_health.sector_distribution || {}).map(
                  ([sector, percentage]: [string, any]) => (
                    <Box key={sector} sx={{ mb: 1 }}>
                      <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 0.5 }}>
                        <Typography variant="body2">{sector}</Typography>
                        <Typography variant="body2">{percentage.toFixed(1)}%</Typography>
                      </Box>
                      <LinearProgress
                        variant="determinate"
                        value={percentage}
                        sx={{ height: 6, borderRadius: 3 }}
                      />
                    </Box>
                  )
                )}
              </Grid>
            </Grid>
          </Paper>
        )}

        {/* Position Recommendations */}
        {analysis && analysis.position_recommendations && analysis.position_recommendations.length > 0 && (
          <Paper elevation={3} sx={{ p: 3, mb: 3 }}>
            <Typography variant="h6" gutterBottom>
              Position Recommendations
            </Typography>
            <Grid container spacing={2}>
              {analysis.position_recommendations.map((rec: any, index: number) => (
                <Grid item xs={12} md={6} key={index}>
                  <Card variant="outlined">
                    <CardContent>
                      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', mb: 2 }}>
                        <Typography variant="h6">{rec.symbol}</Typography>
                        <Chip
                          icon={getActionIcon(rec.action)}
                          label={rec.action}
                          color={getActionColor(rec.action)}
                          size="small"
                        />
                      </Box>
                      
                      <Typography variant="body2" color="textSecondary" paragraph>
                        {rec.reason}
                      </Typography>
                      
                      <Divider sx={{ my: 1 }} />
                      
                      <Grid container spacing={1}>
                        {rec.current_return !== undefined && (
                          <Grid item xs={6}>
                            <Typography variant="caption" color="textSecondary">
                              Return
                            </Typography>
                            <Typography
                              variant="body2"
                              color={rec.current_return >= 0 ? 'success.main' : 'error.main'}
                            >
                              {rec.current_return >= 0 ? '+' : ''}{rec.current_return.toFixed(2)}%
                            </Typography>
                          </Grid>
                        )}
                        <Grid item xs={6}>
                          <Typography variant="caption" color="textSecondary">
                            Confidence
                          </Typography>
                          <Typography variant="body2">
                            {(rec.confidence * 100).toFixed(0)}%
                          </Typography>
                        </Grid>
                        {rec.predicted_change !== undefined && (
                          <Grid item xs={6}>
                            <Typography variant="caption" color="textSecondary">
                              Predicted
                            </Typography>
                            <Typography
                              variant="body2"
                              color={rec.predicted_change >= 0 ? 'success.main' : 'error.main'}
                            >
                              {rec.predicted_change >= 0 ? '+' : ''}{rec.predicted_change.toFixed(2)}%
                            </Typography>
                          </Grid>
                        )}
                        {rec.direction && (
                          <Grid item xs={6}>
                            <Typography variant="caption" color="textSecondary">
                              Direction
                            </Typography>
                            <Chip 
                              label={rec.direction} 
                              size="small"
                              color={rec.direction === 'UP' ? 'success' : rec.direction === 'DOWN' ? 'error' : 'default'}
                            />
                          </Grid>
                        )}
                        {rec.current_price !== undefined && (
                          <Grid item xs={6}>
                            <Typography variant="caption" color="textSecondary">
                              Current Price
                            </Typography>
                            <Typography variant="body2">
                              ${rec.current_price.toFixed(2)}
                            </Typography>
                          </Grid>
                        )}
                        {rec.predicted_price !== undefined && (
                          <Grid item xs={6}>
                            <Typography variant="caption" color="textSecondary">
                              Predicted Price
                            </Typography>
                            <Typography variant="body2">
                              ${rec.predicted_price.toFixed(2)}
                            </Typography>
                          </Grid>
                        )}
                        {rec.position_shares && (
                          <Grid item xs={6}>
                            <Typography variant="caption" color="textSecondary">
                              Shares Held
                            </Typography>
                            <Typography variant="body2">{rec.position_shares.toLocaleString()}</Typography>
                          </Grid>
                        )}
                        {rec.position_value && (
                          <Grid item xs={6}>
                            <Typography variant="caption" color="textSecondary">
                              Position Value
                            </Typography>
                            <Typography variant="body2">
                              ${rec.position_value.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                            </Typography>
                          </Grid>
                        )}
                        {rec.technical_indicators && Object.keys(rec.technical_indicators).length > 0 && (
                          <Grid item xs={12}>
                            <Typography variant="caption" color="textSecondary">
                              Technical Indicators
                            </Typography>
                            <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5, mt: 0.5 }}>
                              {rec.technical_indicators.RSI !== undefined && (
                                <Chip 
                                  label={`RSI: ${rec.technical_indicators.RSI.toFixed(1)}`} 
                                  size="small" 
                                  variant="outlined"
                                  color={rec.technical_indicators.RSI > 70 ? 'error' : rec.technical_indicators.RSI < 30 ? 'success' : 'default'}
                                />
                              )}
                              {rec.technical_indicators.MACD !== undefined && (
                                <Chip 
                                  label={`MACD: ${rec.technical_indicators.MACD.toFixed(2)}`} 
                                  size="small" 
                                  variant="outlined"
                                  color={rec.technical_indicators.MACD > 0 ? 'success' : 'error'}
                                />
                              )}
                            </Box>
                          </Grid>
                        )}
                        {rec.data_source && (
                          <Grid item xs={12}>
                            <Chip 
                              label={`Source: ${rec.data_source}`} 
                              size="small" 
                              variant="outlined"
                              color="info"
                            />
                          </Grid>
                        )}
                      </Grid>
                    </CardContent>
                  </Card>
                </Grid>
              ))}
            </Grid>
          </Paper>
        )}

        {/* New Opportunities */}
        {analysis && analysis.new_opportunities && analysis.new_opportunities.length > 0 && (
          <Paper elevation={3} sx={{ p: 3, mb: 3 }}>
            <Typography variant="h6" gutterBottom>
              New Investment Opportunities
            </Typography>
            <Grid container spacing={2}>
              {analysis.new_opportunities.map((opp: any, index: number) => (
                <Grid item xs={12} md={4} key={index}>
                  <Card variant="outlined">
                    <CardContent>
                      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', mb: 1 }}>
                        <Typography variant="h6">{opp.symbol}</Typography>
                        {opp.direction && (
                          <Chip 
                            label={opp.direction} 
                            size="small"
                            color={opp.direction === 'UP' ? 'success' : opp.direction === 'DOWN' ? 'error' : 'default'}
                          />
                        )}
                      </Box>
                      <Typography variant="body2" color="textSecondary" paragraph>
                        {opp.reason}
                      </Typography>
                      <Divider sx={{ my: 1 }} />
                      <Grid container spacing={1}>
                        <Grid item xs={6}>
                          <Typography variant="caption" color="textSecondary">
                            Predicted Change
                          </Typography>
                          <Typography
                            variant="body2"
                            color={opp.predicted_change >= 0 ? 'success.main' : 'error.main'}
                          >
                            {opp.predicted_change >= 0 ? '+' : ''}{opp.predicted_change.toFixed(2)}%
                          </Typography>
                        </Grid>
                        <Grid item xs={6}>
                          <Typography variant="caption" color="textSecondary">
                            Confidence
                          </Typography>
                          <Typography variant="body2">
                            {(opp.confidence * 100).toFixed(0)}%
                          </Typography>
                        </Grid>
                        {opp.current_price > 0 && (
                          <Grid item xs={6}>
                            <Typography variant="caption" color="textSecondary">
                              Current Price
                            </Typography>
                            <Typography variant="body2">
                              ${opp.current_price.toFixed(2)}
                            </Typography>
                          </Grid>
                        )}
                        {opp.predicted_price > 0 && (
                          <Grid item xs={6}>
                            <Typography variant="caption" color="textSecondary">
                              Predicted Price
                            </Typography>
                            <Typography variant="body2">
                              ${opp.predicted_price.toFixed(2)}
                            </Typography>
                          </Grid>
                        )}
                        {opp.recommended_shares > 0 && (
                          <Grid item xs={12}>
                            <Typography variant="caption" color="textSecondary">
                              Recommended Shares
                            </Typography>
                            <Typography variant="body2">{opp.recommended_shares}</Typography>
                          </Grid>
                        )}
                        {opp.technical_indicators && Object.keys(opp.technical_indicators).length > 0 && (
                          <Grid item xs={12}>
                            <Typography variant="caption" color="textSecondary">
                              Technical Indicators
                            </Typography>
                            <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5, mt: 0.5 }}>
                              {opp.technical_indicators.RSI !== undefined && (
                                <Chip 
                                  label={`RSI: ${opp.technical_indicators.RSI.toFixed(1)}`} 
                                  size="small" 
                                  variant="outlined"
                                />
                              )}
                              {opp.technical_indicators.MACD !== undefined && (
                                <Chip 
                                  label={`MACD: ${opp.technical_indicators.MACD.toFixed(2)}`} 
                                  size="small" 
                                  variant="outlined"
                                />
                              )}
                            </Box>
                          </Grid>
                        )}
                        {opp.data_source && (
                          <Grid item xs={12}>
                            <Chip 
                              label={`Source: ${opp.data_source}`} 
                              size="small" 
                              variant="outlined"
                              color="info"
                            />
                          </Grid>
                        )}
                      </Grid>
                    </CardContent>
                  </Card>
                </Grid>
              ))}
            </Grid>
          </Paper>
        )}

        {/* Similar Stocks */}
        {similarStocks && similarStocks.recommendations && similarStocks.recommendations.length > 0 && (
          <Paper elevation={3} sx={{ p: 3 }}>
            <Typography variant="h6" gutterBottom>
              Similar Stocks to Your Portfolio
            </Typography>
            <Typography variant="body2" color="textSecondary" paragraph>
              Stocks with similar patterns to your successful positions
            </Typography>
            <Grid container spacing={2}>
              {similarStocks.recommendations.map((stock: any, index: number) => (
                <Grid item xs={12} md={4} key={index}>
                  <Card variant="outlined">
                    <CardContent>
                      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', mb: 1 }}>
                        <Typography variant="h6">{stock.symbol}</Typography>
                        <Chip
                          label={`${(stock.similarity_score * 100).toFixed(0)}% similar`}
                          size="small"
                          color="primary"
                          variant="outlined"
                        />
                      </Box>
                      
                      <Typography variant="caption" color="textSecondary">
                        Similar to: {stock.similar_to?.join(', ')}
                      </Typography>
                      
                      <Divider sx={{ my: 1 }} />
                      
                      <Grid container spacing={1}>
                        <Grid item xs={6}>
                          <Typography variant="caption" color="textSecondary">
                            Current Price
                          </Typography>
                          <Typography variant="body2">
                            ${stock.current_price.toFixed(2)}
                          </Typography>
                        </Grid>
                        <Grid item xs={6}>
                          <Typography variant="caption" color="textSecondary">
                            24h Change
                          </Typography>
                          <Typography
                            variant="body2"
                            color={stock.price_change_1d >= 0 ? 'success.main' : 'error.main'}
                          >
                            {stock.price_change_1d >= 0 ? '+' : ''}{stock.price_change_1d.toFixed(2)}%
                          </Typography>
                        </Grid>
                        {stock.predicted_change !== undefined && (
                          <>
                            <Grid item xs={6}>
                              <Typography variant="caption" color="textSecondary">
                                Predicted
                              </Typography>
                              <Typography
                                variant="body2"
                                color={stock.predicted_change >= 0 ? 'success.main' : 'error.main'}
                              >
                                {stock.predicted_change >= 0 ? '+' : ''}{stock.predicted_change.toFixed(2)}%
                              </Typography>
                            </Grid>
                            <Grid item xs={6}>
                              <Typography variant="caption" color="textSecondary">
                                Direction
                              </Typography>
                              <Typography variant="body2">{stock.direction}</Typography>
                            </Grid>
                          </>
                        )}
                      </Grid>
                    </CardContent>
                  </Card>
                </Grid>
              ))}
            </Grid>
          </Paper>
        )}
      </Box>
    </Container>
  );
};

export default PortfolioAnalysis;
