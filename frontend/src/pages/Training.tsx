import React, { useState, useEffect } from 'react';
import {
  Container,
  Typography,
  Paper,
  Box,
  Button,
  CircularProgress,
  Alert,
  LinearProgress,
  Card,
  CardContent,
  Grid,
  Chip,
} from '@mui/material';
import { Settings, CheckCircle, TrendingUp } from '@mui/icons-material';
import { tradingApi, marketApi } from '../services/api';

const Training: React.FC = () => {
  const [loading, setLoading] = useState(false);
  const [availableSymbols, setAvailableSymbols] = useState<string[]>([]);
  const [trainingResult, setTrainingResult] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);
  const [systemStatus, setSystemStatus] = useState<any>(null);

  useEffect(() => {
    loadSymbols();
    loadSystemStatus();
  }, []);

  const loadSymbols = async () => {
    try {
      const data = await marketApi.getAvailableCsvSymbols();
      setAvailableSymbols(data.symbols);
    } catch (err) {
      console.error('Error loading symbols:', err);
    }
  };

  const loadSystemStatus = async () => {
    try {
      const status = await tradingApi.getSystemStatus();
      setSystemStatus(status);
    } catch (err) {
      console.error('Error loading status:', err);
    }
  };

  const handleTrainAllStocks = async () => {
    try {
      setLoading(true);
      setError(null);
      setTrainingResult(null);

      // Train on ALL available stocks - backend will load from dataset
      const result = await tradingApi.trainAgents({
        use_sample: false  // Full dataset
      });

      setTrainingResult(result);
      
      // Reload system status
      await loadSystemStatus();
      
    } catch (err: any) {
      setError(err.message || 'Training failed');
    } finally {
      setLoading(false);
    }
  };

  const handleTrainSample = async () => {
    try {
      setLoading(true);
      setError(null);
      setTrainingResult(null);

      // Train on sample (first 100 stocks)
      const result = await tradingApi.trainAgents({
        use_sample: true  // Sample only
      });

      setTrainingResult(result);
      await loadSystemStatus();
      
    } catch (err: any) {
      setError(err.message || 'Training failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <Container maxWidth="xl">
      <Box sx={{ py: 4 }}>
        <Typography variant="h4" gutterBottom sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <Settings /> Model Training
        </Typography>

        {error && (
          <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>
            {error}
          </Alert>
        )}

        {/* Dataset Info */}
        <Paper elevation={3} sx={{ p: 3, mb: 3 }}>
          <Typography variant="h6" gutterBottom>
            NASDAQ Dataset
          </Typography>
          <Grid container spacing={2}>
            <Grid item xs={12} md={4}>
              <Card variant="outlined">
                <CardContent>
                  <Typography color="textSecondary" gutterBottom>
                    Total Stocks
                  </Typography>
                  <Typography variant="h4">
                    {availableSymbols.length.toLocaleString()}
                  </Typography>
                  <Typography variant="caption" color="textSecondary">
                    NASDAQ stocks available
                  </Typography>
                </CardContent>
              </Card>
            </Grid>
            <Grid item xs={12} md={4}>
              <Card variant="outlined">
                <CardContent>
                  <Typography color="textSecondary" gutterBottom>
                    Date Range
                  </Typography>
                  <Typography variant="h6">
                    1962 - 2025
                  </Typography>
                  <Typography variant="caption" color="textSecondary">
                    63 years of historical data
                  </Typography>
                </CardContent>
              </Card>
            </Grid>
            <Grid item xs={12} md={4}>
              <Card variant="outlined">
                <CardContent>
                  <Typography color="textSecondary" gutterBottom>
                    Model Storage
                  </Typography>
                  <Typography variant="h6">
                    ./models/
                  </Typography>
                  <Typography variant="caption" color="textSecondary">
                    Trained models saved locally
                  </Typography>
                </CardContent>
              </Card>
            </Grid>
          </Grid>
        </Paper>

        {/* Current Status */}
        {systemStatus && (
          <Paper elevation={3} sx={{ p: 3, mb: 3 }}>
            <Typography variant="h6" gutterBottom>
              Current Model Status
            </Typography>
            <Grid container spacing={2}>
              <Grid item xs={12} md={6}>
                <Box sx={{ mb: 2 }}>
                  <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
                    <Typography variant="body2">Market Monitor</Typography>
                    {systemStatus.details?.market_monitor?.is_trained ? (
                      <Chip label="Trained" color="success" size="small" icon={<CheckCircle />} />
                    ) : (
                      <Chip label="Not Trained" color="warning" size="small" />
                    )}
                  </Box>
                  {systemStatus.details?.market_monitor?.model_exists && (
                    <Typography variant="caption" color="textSecondary">
                      Model file exists in ./models/
                    </Typography>
                  )}
                </Box>
              </Grid>
              <Grid item xs={12} md={6}>
                <Box sx={{ mb: 2 }}>
                  <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
                    <Typography variant="body2">Decision Maker</Typography>
                    {systemStatus.details?.decision_maker?.is_trained ? (
                      <Chip label="Trained" color="success" size="small" icon={<CheckCircle />} />
                    ) : (
                      <Chip label="Not Trained" color="warning" size="small" />
                    )}
                  </Box>
                  <Typography variant="caption" color="textSecondary">
                    Risk Tolerance: {systemStatus.details?.decision_maker?.risk_tolerance || 0.5}
                  </Typography>
                </Box>
              </Grid>
            </Grid>
          </Paper>
        )}

        {/* Training Controls */}
        <Paper elevation={3} sx={{ p: 3, mb: 3 }}>
          <Typography variant="h6" gutterBottom>
            Train Models
          </Typography>
          <Typography variant="body2" color="textSecondary" paragraph>
            Train AI models on historical stock data. Models will be saved to ./models/ directory.
          </Typography>

          <Box sx={{ display: 'flex', gap: 2, flexWrap: 'wrap' }}>
            <Button
              variant="contained"
              size="large"
              startIcon={loading ? <CircularProgress size={20} /> : <TrendingUp />}
              onClick={handleTrainAllStocks}
              disabled={loading || availableSymbols.length === 0}
            >
              Train on All Stocks ({availableSymbols.length.toLocaleString()})
            </Button>

            <Button
              variant="outlined"
              size="large"
              onClick={handleTrainSample}
              disabled={loading || availableSymbols.length === 0}
            >
              Train on Sample (200 stocks)
            </Button>
          </Box>

          {loading && (
            <Box sx={{ mt: 3 }}>
              <Typography variant="body2" color="textSecondary" gutterBottom>
                Training in progress... This may take several minutes.
              </Typography>
              <LinearProgress />
            </Box>
          )}
        </Paper>

        {/* Training Results */}
        {trainingResult && (
          <Paper elevation={3} sx={{ p: 3 }}>
            <Typography variant="h6" gutterBottom>
              Training Results
            </Typography>

            {trainingResult.results?.market_monitor && (
              <Box sx={{ mb: 3 }}>
                <Typography variant="subtitle1" gutterBottom sx={{ fontWeight: 'bold' }}>
                  Market Monitor (Random Forest)
                </Typography>
                <Grid container spacing={2}>
                  <Grid item xs={6} md={3}>
                    <Typography variant="caption" color="textSecondary">
                      Stocks Processed
                    </Typography>
                    <Typography variant="h6">
                      {trainingResult.results.market_monitor.training_stats?.stocks_processed || 0}
                    </Typography>
                  </Grid>
                  <Grid item xs={6} md={3}>
                    <Typography variant="caption" color="textSecondary">
                      Total Samples
                    </Typography>
                    <Typography variant="h6">
                      {trainingResult.results.market_monitor.training_stats?.total_samples?.toLocaleString() || 0}
                    </Typography>
                  </Grid>
                  <Grid item xs={6} md={3}>
                    <Typography variant="caption" color="textSecondary">
                      RMSE
                    </Typography>
                    <Typography variant="h6">
                      {trainingResult.results.market_monitor.training_stats?.rmse?.toFixed(4) || 'N/A'}%
                    </Typography>
                  </Grid>
                  <Grid item xs={6} md={3}>
                    <Typography variant="caption" color="textSecondary">
                      MAE
                    </Typography>
                    <Typography variant="h6">
                      {trainingResult.results.market_monitor.training_stats?.mae?.toFixed(4) || 'N/A'}%
                    </Typography>
                  </Grid>
                </Grid>

                {trainingResult.results.market_monitor.training_stats?.feature_importance && (
                  <Box sx={{ mt: 2 }}>
                    <Typography variant="caption" color="textSecondary" gutterBottom>
                      Top Features:
                    </Typography>
                    <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap', mt: 1 }}>
                      {Object.entries(trainingResult.results.market_monitor.training_stats.feature_importance)
                        .slice(0, 5)
                        .map(([feature, importance]: [string, any]) => (
                          <Chip
                            key={feature}
                            label={`${feature}: ${(importance * 100).toFixed(1)}%`}
                            size="small"
                            variant="outlined"
                          />
                        ))}
                    </Box>
                  </Box>
                )}
              </Box>
            )}

            <Alert severity="success" sx={{ mt: 2 }}>
              Models trained successfully and saved to ./models/ directory!
            </Alert>
          </Paper>
        )}
      </Box>
    </Container>
  );
};

export default Training;
