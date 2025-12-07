# Multi-Agent Trading System - Frontend

React-based web interface for the Multi-Agent AI Trading System. Provides real-time monitoring, trading execution, portfolio management, and model training capabilities.

## Features

- **Dashboard**: System overview with key metrics and agent health
- **Trading**: Execute trading cycles with stock selection
- **Portfolio**: View holdings, positions, and P&L
- **Performance**: Analytics with charts and decision history
- **Training**: Train ML models on historical data

## Tech Stack

- **React 18** with TypeScript
- **Vite** for fast development and building
- **TailwindCSS** for styling
- **Recharts** for data visualization
- **Axios** for API communication
- **React Router** for navigation

## Prerequisites

- Node.js 18+ and npm
- Backend API running on `http://localhost:8000`

## Installation

1. Install dependencies:

```bash
npm install
```

2. Configure environment (optional):

```bash
cp .env.example .env
# Edit .env if backend runs on different port
```

## Development

Start the development server:

```bash
npm run dev
```

The app will be available at `http://localhost:3000`.

## Build

Create production build:

```bash
npm run build
```

Preview production build:

```bash
npm run preview
```

## Project Structure

```
frontend/
├── src/
│   ├── pages/           # Main application pages
│   │   ├── Dashboard.tsx
│   │   ├── Trading.tsx
│   │   ├── Portfolio.tsx
│   │   ├── Performance.tsx
│   │   └── Training.tsx
│   ├── services/        # API client
│   │   └── api.ts
│   ├── App.tsx          # Main app component
│   ├── main.tsx         # Entry point
│   └── index.css        # Global styles
├── public/              # Static assets
├── index.html           # HTML template
├── vite.config.ts       # Vite configuration
└── tailwind.config.js   # Tailwind configuration
```

## API Integration

The frontend connects to the backend API through a proxy configured in `vite.config.ts`. All requests to `/api/*` are forwarded to `http://localhost:8000`.

### Available API Endpoints

- `POST /api/trading/train` - Train ML models
- `POST /api/trading/run` - Execute trading cycle
- `GET /api/trading/status` - Get system status
- `GET /api/trading/portfolio` - Get portfolio data
- `GET /api/trading/performance` - Get performance metrics
- `GET /api/trading/decisions` - Get decision history
- `GET /api/market/stock/{symbol}` - Get stock data

See `src/services/api.ts` for full TypeScript API client.

## Usage

### 1. Train Models

Navigate to **Training** page:
- Select stocks to train on
- Click "Start Training"
- Wait for training to complete (~5-30 seconds)

### 2. Run Trading Cycle

Navigate to **Trading** page:
- Select target stocks
- Toggle CSV data usage if needed
- Click "Run Trading Cycle"
- View decisions and execution results

### 3. Monitor Portfolio

Navigate to **Portfolio** page:
- View total value, cash, and positions
- See active positions with P&L
- Check allocation breakdown

### 4. Analyze Performance

Navigate to **Performance** page:
- Review win rate, total trades, profit
- See win/loss distribution chart
- Analyze decision history

## Configuration

### Environment Variables

- `VITE_API_URL`: Backend API URL (default: `http://localhost:8000`)

### Proxy Configuration

Edit `vite.config.ts` to change backend URL:

```typescript
server: {
  proxy: {
    '/api': {
      target: 'http://localhost:8000',
      changeOrigin: true,
    },
  },
}
```

## Development Tips

- API calls automatically refresh data every 10-30 seconds on most pages
- Use browser DevTools to monitor API requests
- Backend must be running for frontend to work properly
- Check backend logs if API calls fail

## Troubleshooting

### Connection Issues

If frontend can't connect to backend:

1. Verify backend is running: `http://localhost:8000/docs`
2. Check proxy configuration in `vite.config.ts`
3. Ensure no firewall blocking port 8000
4. Check browser console for CORS errors

### Build Issues

If build fails:

```bash
# Clear node_modules and reinstall
rm -rf node_modules package-lock.json
npm install

# Clear Vite cache
rm -rf node_modules/.vite
```

## License

MIT
