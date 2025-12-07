import React, { useState, useEffect, useCallback } from 'react';
import {
  Container,
  Typography,
  Paper,
  Box,
  TextField,
  InputAdornment,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  TablePagination,
  TableSortLabel,
  Chip,
  CircularProgress,
  Alert,
  Card,
  CardContent,
  Slider,
  Button,
  IconButton,
  Collapse,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
} from '@mui/material';
import {
  Search,
  TrendingUp,
  TrendingDown,
  FilterList,
  Close,
  ShowChart,
  Refresh,
} from '@mui/icons-material';
import {
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  AreaChart,
  Area,
} from 'recharts';
import { marketApi, StockData, StockDetailResponse } from '../services/api';

type SortOrder = 'asc' | 'desc';

const Stocks: React.FC = () => {
  const [stocks, setStocks] = useState<StockData[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  
  // Pagination
  const [page, setPage] = useState(0);
  const [rowsPerPage, setRowsPerPage] = useState(50);
  const [totalStocks, setTotalStocks] = useState(0);
  
  // Search and filters
  const [search, setSearch] = useState('');
  const [searchDebounced, setSearchDebounced] = useState('');
  const [showFilters, setShowFilters] = useState(false);
  const [priceRange, setPriceRange] = useState<[number, number]>([0, 10000]);
  const [changeRange, setChangeRange] = useState<[number, number]>([-100, 100]);
  
  // Sorting
  const [sortBy, setSortBy] = useState<string>('symbol');
  const [sortOrder, setSortOrder] = useState<SortOrder>('asc');
  
  // Stock detail dialog
  const [selectedStock, setSelectedStock] = useState<string | null>(null);
  const [stockDetail, setStockDetail] = useState<StockDetailResponse | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);

  // Debounce search
  useEffect(() => {
    const timer = setTimeout(() => {
      setSearchDebounced(search);
      setPage(0);
    }, 300);
    return () => clearTimeout(timer);
  }, [search]);

  const loadStocks = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      
      const data = await marketApi.getAllStocksData({
        page: page + 1,
        per_page: rowsPerPage,
        search: searchDebounced || undefined,
        sort_by: sortBy,
        sort_order: sortOrder,
        min_price: priceRange[0] > 0 ? priceRange[0] : undefined,
        max_price: priceRange[1] < 10000 ? priceRange[1] : undefined,
        min_change_pct: changeRange[0] > -100 ? changeRange[0] : undefined,
        max_change_pct: changeRange[1] < 100 ? changeRange[1] : undefined,
      });
      
      setStocks(data.stocks);
      setTotalStocks(data.pagination.total);
    } catch (err: any) {
      setError(err.message || 'Failed to load stocks');
    } finally {
      setLoading(false);
    }
  }, [page, rowsPerPage, searchDebounced, sortBy, sortOrder, priceRange, changeRange]);

  useEffect(() => {
    loadStocks();
  }, [loadStocks]);

  const handleSort = (property: string) => {
    const isAsc = sortBy === property && sortOrder === 'asc';
    setSortOrder(isAsc ? 'desc' : 'asc');
    setSortBy(property);
  };

  const handleRowClick = async (symbol: string) => {
    setSelectedStock(symbol);
    setDetailLoading(true);
    try {
      const data = await marketApi.getStockCsvData(symbol, 365);
      setStockDetail(data);
    } catch (err) {
      console.error('Failed to load stock detail:', err);
    } finally {
      setDetailLoading(false);
    }
  };

  const handleCloseDetail = () => {
    setSelectedStock(null);
    setStockDetail(null);
  };

  const formatNumber = (num: number): string => {
    if (num >= 1e9) return (num / 1e9).toFixed(2) + 'B';
    if (num >= 1e6) return (num / 1e6).toFixed(2) + 'M';
    if (num >= 1e3) return (num / 1e3).toFixed(2) + 'K';
    return num.toLocaleString();
  };

  const formatPrice = (price: number): string => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    }).format(price);
  };

  return (
    <Container maxWidth="xl">
      <Box sx={{ py: 4 }}>
        <Typography variant="h4" gutterBottom sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <ShowChart /> All Stocks ({totalStocks.toLocaleString()})
        </Typography>

        {error && (
          <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>
            {error}
          </Alert>
        )}

        {/* Search and Filters */}
        <Paper elevation={3} sx={{ p: 2, mb: 3 }}>
          <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 2, alignItems: 'center' }}>
            <Box sx={{ flex: '1 1 300px' }}>
              <TextField
                fullWidth
                placeholder="Search by symbol..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                InputProps={{
                  startAdornment: (
                    <InputAdornment position="start">
                      <Search />
                    </InputAdornment>
                  ),
                }}
              />
            </Box>
            <Box sx={{ display: 'flex', gap: 1 }}>
              <Button
                variant="outlined"
                startIcon={<FilterList />}
                onClick={() => setShowFilters(!showFilters)}
              >
                Filters
              </Button>
              <IconButton onClick={loadStocks} disabled={loading}>
                <Refresh />
              </IconButton>
            </Box>
          </Box>

          <Collapse in={showFilters}>
            <Box sx={{ mt: 3, display: 'flex', flexWrap: 'wrap', gap: 4 }}>
              <Box sx={{ flex: '1 1 300px' }}>
                <Typography gutterBottom>Price Range: ${priceRange[0]} - ${priceRange[1]}</Typography>
                <Slider
                  value={priceRange}
                  onChange={(_, value) => setPriceRange(value as [number, number])}
                  valueLabelDisplay="auto"
                  min={0}
                  max={10000}
                  step={10}
                />
              </Box>
              <Box sx={{ flex: '1 1 300px' }}>
                <Typography gutterBottom>Change %: {changeRange[0]}% - {changeRange[1]}%</Typography>
                <Slider
                  value={changeRange}
                  onChange={(_, value) => setChangeRange(value as [number, number])}
                  valueLabelDisplay="auto"
                  min={-100}
                  max={100}
                  step={1}
                />
              </Box>
            </Box>
          </Collapse>
        </Paper>

        {/* Summary Cards */}
        <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 2, mb: 3 }}>
          <Box sx={{ flex: '1 1 200px', minWidth: '150px' }}>
            <Card>
              <CardContent>
                <Typography color="textSecondary" variant="caption">
                  Total Stocks
                </Typography>
                <Typography variant="h5">{totalStocks.toLocaleString()}</Typography>
              </CardContent>
            </Card>
          </Box>
          <Box sx={{ flex: '1 1 200px', minWidth: '150px' }}>
            <Card>
              <CardContent>
                <Typography color="textSecondary" variant="caption">
                  Gainers
                </Typography>
                <Typography variant="h5" color="success.main">
                  {stocks.filter(s => s.change_pct > 0).length}
                </Typography>
              </CardContent>
            </Card>
          </Box>
          <Box sx={{ flex: '1 1 200px', minWidth: '150px' }}>
            <Card>
              <CardContent>
                <Typography color="textSecondary" variant="caption">
                  Losers
                </Typography>
                <Typography variant="h5" color="error.main">
                  {stocks.filter(s => s.change_pct < 0).length}
                </Typography>
              </CardContent>
            </Card>
          </Box>
          <Box sx={{ flex: '1 1 200px', minWidth: '150px' }}>
            <Card>
              <CardContent>
                <Typography color="textSecondary" variant="caption">
                  Unchanged
                </Typography>
                <Typography variant="h5">
                  {stocks.filter(s => s.change_pct === 0).length}
                </Typography>
              </CardContent>
            </Card>
          </Box>
        </Box>

        {/* Stocks Table */}
        <Paper elevation={3}>
          <TableContainer sx={{ maxHeight: 600 }}>
            {loading ? (
              <Box sx={{ display: 'flex', justifyContent: 'center', p: 4 }}>
                <CircularProgress />
              </Box>
            ) : (
              <Table stickyHeader size="small">
                <TableHead>
                  <TableRow>
                    <TableCell>
                      <TableSortLabel
                        active={sortBy === 'symbol'}
                        direction={sortBy === 'symbol' ? sortOrder : 'asc'}
                        onClick={() => handleSort('symbol')}
                      >
                        Symbol
                      </TableSortLabel>
                    </TableCell>
                    <TableCell align="right">
                      <TableSortLabel
                        active={sortBy === 'close'}
                        direction={sortBy === 'close' ? sortOrder : 'asc'}
                        onClick={() => handleSort('close')}
                      >
                        Price
                      </TableSortLabel>
                    </TableCell>
                    <TableCell align="right">
                      <TableSortLabel
                        active={sortBy === 'change_pct'}
                        direction={sortBy === 'change_pct' ? sortOrder : 'asc'}
                        onClick={() => handleSort('change_pct')}
                      >
                        Change %
                      </TableSortLabel>
                    </TableCell>
                    <TableCell align="right">Change</TableCell>
                    <TableCell align="right">
                      <TableSortLabel
                        active={sortBy === 'volume'}
                        direction={sortBy === 'volume' ? sortOrder : 'asc'}
                        onClick={() => handleSort('volume')}
                      >
                        Volume
                      </TableSortLabel>
                    </TableCell>
                    <TableCell align="right">52W High</TableCell>
                    <TableCell align="right">52W Low</TableCell>
                    <TableCell align="right">Data Range</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {stocks.map((stock) => (
                    <TableRow
                      key={stock.symbol}
                      hover
                      sx={{ cursor: 'pointer' }}
                      onClick={() => handleRowClick(stock.symbol)}
                    >
                      <TableCell>
                        <Typography variant="body2" fontWeight="bold">
                          {stock.symbol}
                        </Typography>
                      </TableCell>
                      <TableCell align="right">
                        {formatPrice(stock.close)}
                      </TableCell>
                      <TableCell align="right">
                        <Chip
                          size="small"
                          icon={stock.change_pct >= 0 ? <TrendingUp /> : <TrendingDown />}
                          label={`${stock.change_pct >= 0 ? '+' : ''}${stock.change_pct.toFixed(2)}%`}
                          color={stock.change_pct >= 0 ? 'success' : 'error'}
                          variant="outlined"
                        />
                      </TableCell>
                      <TableCell align="right">
                        <Typography
                          color={stock.change >= 0 ? 'success.main' : 'error.main'}
                        >
                          {stock.change >= 0 ? '+' : ''}{formatPrice(stock.change)}
                        </Typography>
                      </TableCell>
                      <TableCell align="right">
                        {formatNumber(stock.volume)}
                      </TableCell>
                      <TableCell align="right">
                        {formatPrice(stock.week_52_high)}
                      </TableCell>
                      <TableCell align="right">
                        {formatPrice(stock.week_52_low)}
                      </TableCell>
                      <TableCell align="right">
                        <Typography variant="caption" color="textSecondary">
                          {stock.first_date?.split(' ')[0]} - {stock.last_date?.split(' ')[0]}
                        </Typography>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            )}
          </TableContainer>
          <TablePagination
            component="div"
            count={totalStocks}
            page={page}
            onPageChange={(_, newPage) => setPage(newPage)}
            rowsPerPage={rowsPerPage}
            onRowsPerPageChange={(e) => {
              setRowsPerPage(parseInt(e.target.value, 10));
              setPage(0);
            }}
            rowsPerPageOptions={[25, 50, 100, 200]}
          />
        </Paper>

        {/* Stock Detail Dialog */}
        <Dialog
          open={!!selectedStock}
          onClose={handleCloseDetail}
          maxWidth="lg"
          fullWidth
        >
          <DialogTitle>
            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <Typography variant="h6">
                {selectedStock} - Stock Details
              </Typography>
              <IconButton onClick={handleCloseDetail}>
                <Close />
              </IconButton>
            </Box>
          </DialogTitle>
          <DialogContent>
            {detailLoading ? (
              <Box sx={{ display: 'flex', justifyContent: 'center', p: 4 }}>
                <CircularProgress />
              </Box>
            ) : stockDetail ? (
              <Box>
                {/* Price Summary */}
                <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 2, mb: 3 }}>
                  <Box sx={{ flex: '1 1 200px', minWidth: '150px' }}>
                    <Card variant="outlined">
                      <CardContent>
                        <Typography color="textSecondary" variant="caption">
                          Current Price
                        </Typography>
                        <Typography variant="h5">
                          {formatPrice(stockDetail.current_price)}
                        </Typography>
                      </CardContent>
                    </Card>
                  </Box>
                  <Box sx={{ flex: '1 1 200px', minWidth: '150px' }}>
                    <Card variant="outlined">
                      <CardContent>
                        <Typography color="textSecondary" variant="caption">
                          Change
                        </Typography>
                        <Typography
                          variant="h5"
                          color={stockDetail.change >= 0 ? 'success.main' : 'error.main'}
                        >
                          {stockDetail.change >= 0 ? '+' : ''}{formatPrice(stockDetail.change)}
                        </Typography>
                      </CardContent>
                    </Card>
                  </Box>
                  <Box sx={{ flex: '1 1 200px', minWidth: '150px' }}>
                    <Card variant="outlined">
                      <CardContent>
                        <Typography color="textSecondary" variant="caption">
                          Change %
                        </Typography>
                        <Typography
                          variant="h5"
                          color={stockDetail.change_pct >= 0 ? 'success.main' : 'error.main'}
                        >
                          {stockDetail.change_pct >= 0 ? '+' : ''}{stockDetail.change_pct.toFixed(2)}%
                        </Typography>
                      </CardContent>
                    </Card>
                  </Box>
                  <Box sx={{ flex: '1 1 200px', minWidth: '150px' }}>
                    <Card variant="outlined">
                      <CardContent>
                        <Typography color="textSecondary" variant="caption">
                          Total Records
                        </Typography>
                        <Typography variant="h5">
                          {stockDetail.total_records.toLocaleString()}
                        </Typography>
                      </CardContent>
                    </Card>
                  </Box>
                </Box>

                {/* Price Chart */}
                <Typography variant="h6" gutterBottom>
                  Price History (1 Year)
                </Typography>
                <Box sx={{ height: 400 }}>
                  <ResponsiveContainer width="100%" height="100%">
                    <AreaChart data={stockDetail.history.slice(-365)}>
                      <defs>
                        <linearGradient id="colorPrice" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="5%" stopColor="#1976d2" stopOpacity={0.3}/>
                          <stop offset="95%" stopColor="#1976d2" stopOpacity={0}/>
                        </linearGradient>
                      </defs>
                      <CartesianGrid strokeDasharray="3 3" />
                      <XAxis
                        dataKey="date"
                        tickFormatter={(value) => {
                          const date = new Date(value);
                          return `${date.getMonth() + 1}/${date.getDate()}`;
                        }}
                        interval="preserveStartEnd"
                      />
                      <YAxis
                        domain={['auto', 'auto']}
                        tickFormatter={(value) => `$${value.toFixed(0)}`}
                      />
                      <Tooltip
                        formatter={(value: number) => [formatPrice(value), 'Price']}
                        labelFormatter={(label) => `Date: ${label}`}
                      />
                      <Area
                        type="monotone"
                        dataKey="close"
                        stroke="#1976d2"
                        fillOpacity={1}
                        fill="url(#colorPrice)"
                      />
                    </AreaChart>
                  </ResponsiveContainer>
                </Box>

                {/* Volume Chart */}
                <Typography variant="h6" gutterBottom sx={{ mt: 3 }}>
                  Volume
                </Typography>
                <Box sx={{ height: 200 }}>
                  <ResponsiveContainer width="100%" height="100%">
                    <AreaChart data={stockDetail.history.slice(-365)}>
                      <CartesianGrid strokeDasharray="3 3" />
                      <XAxis
                        dataKey="date"
                        tickFormatter={(value) => {
                          const date = new Date(value);
                          return `${date.getMonth() + 1}/${date.getDate()}`;
                        }}
                        interval="preserveStartEnd"
                      />
                      <YAxis tickFormatter={(value) => formatNumber(value)} />
                      <Tooltip
                        formatter={(value: number) => [formatNumber(value), 'Volume']}
                      />
                      <Area
                        type="monotone"
                        dataKey="volume"
                        stroke="#82ca9d"
                        fill="#82ca9d"
                        fillOpacity={0.3}
                      />
                    </AreaChart>
                  </ResponsiveContainer>
                </Box>
              </Box>
            ) : (
              <Alert severity="error">Failed to load stock details</Alert>
            )}
          </DialogContent>
          <DialogActions>
            <Button onClick={handleCloseDetail}>Close</Button>
          </DialogActions>
        </Dialog>
      </Box>
    </Container>
  );
};

export default Stocks;
