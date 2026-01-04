# 📈 Stock Analysis Web Dashboard

A modern, interactive web-based dashboard for visualizing and analyzing stock market data.

---

## Features

### 📊 Real-Time Statistics
- Total stocks in database
- Data coverage percentage
- Total price records
- Database size
- Latest data timestamp

### 🔍 Smart Search
- Search stocks by symbol
- Instant results
- Click to view detailed analysis

### 📈 Stock Lists
- **Watchlist**: Popular tech stocks (AAPL, MSFT, GOOGL, NVDA, etc.)
- **Top Gainers**: Best performing stocks
- **Top Losers**: Worst performing stocks

### 📉 Interactive Charts
- Candlestick charts for price visualization
- Last 6 months of data
- Zoom and pan capabilities
- Responsive design

### 🔗 External Resources
Each stock includes direct links to:
- **Yahoo Finance** - Comprehensive stock data
- **Finviz** - Visual stock screener
- **MarketWatch** - Financial news and analysis
- **Seeking Alpha** - Investment research
- **TradingView** - Advanced charting
- **Google Finance** - Quick stock overview

---

## Quick Start

### 1. Start the Dashboard

```bash
cd ~/Projects/strategy-z
source venv/bin/activate
python web_dashboard.py
```

### 2. Open in Browser

Visit: **http://localhost:8080**

Or access from other devices on your network:
- **http://192.168.2.236:8080** (your local IP)

---

## Usage Guide

### View Statistics
The top section shows overall database statistics:
- Number of stocks tracked
- Data coverage percentage
- Total historical records
- Database size

### Search for Stocks
1. Click the search box
2. Type stock symbol (e.g., "AAPL")
3. Click on a result to view details

### Browse Stock Lists
Use the tabs to switch between:
- **Watchlist** - Curated list of popular stocks
- **Top Gainers** - Best daily performers
- **Top Losers** - Worst daily performers

### View Stock Details
Click any stock symbol to see:
- Current price
- 1-day, 5-day, 1-month returns
- 52-week high/low
- Volume
- Interactive price chart
- Links to external analysis

### Access External Resources
Each stock detail view includes buttons to:
- View on Yahoo Finance (detailed financials)
- Check technical analysis on Finviz
- Read news on MarketWatch
- Research on Seeking Alpha
- Chart on TradingView
- Quick lookup on Google Finance

---

## Universal Stock Links

The dashboard automatically generates links for any stock using this pattern:

```
Yahoo Finance:    https://finance.yahoo.com/quote/{SYMBOL}
Finviz:          https://finviz.com/quote.ashx?t={SYMBOL}
MarketWatch:     https://www.marketwatch.com/investing/stock/{SYMBOL}
Seeking Alpha:   https://seekingalpha.com/symbol/{SYMBOL}
TradingView:     https://www.tradingview.com/symbols/{SYMBOL}/
Google Finance:  https://www.google.com/finance/quote/{SYMBOL}:NASDAQ
```

Just replace `{SYMBOL}` with any stock ticker (e.g., AAPL, MSFT).

---

## Technical Details

### Technology Stack
- **Backend**: Flask (Python web framework)
- **Frontend**: HTML5, CSS3, JavaScript
- **Charts**: Plotly.js (interactive visualizations)
- **Database**: PostgreSQL + TimescaleDB
- **Data Source**: yfinance API

### API Endpoints

The dashboard exposes REST API endpoints:

```
GET /api/stats           - Database statistics
GET /api/watchlist       - Popular stocks
GET /api/top_movers      - Top gainers and losers
GET /api/stock/{symbol}  - Detailed stock data
GET /api/search?q={query} - Search stocks
```

### Performance
- Lazy loading for fast initial page load
- Caching for frequently accessed data
- Responsive design for mobile/tablet/desktop
- Real-time data fetching

---

## Customization

### Add Stocks to Watchlist

Edit `web_dashboard.py` line 164:

```python
popular_stocks = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA', 'TSLA', 'META', 'NFLX']
# Add your favorites:
popular_stocks = ['AAPL', 'TSLA', 'YOUR_STOCK_HERE']
```

### Change Port

Edit `web_dashboard.py` line 240:

```python
app.run(debug=True, host='0.0.0.0', port=8080)
# Change to:
app.run(debug=True, host='0.0.0.0', port=YOUR_PORT)
```

### Modify Theme

Edit `templates/dashboard.html` CSS section (lines 14-250):

```css
/* Dark theme colors */
background: #0f1419;  /* Main background */
color: #e7e9ea;       /* Text color */

/* Accent color */
#1d9bf0               /* Twitter blue */
```

---

## Screenshots

### Main Dashboard
Shows real-time statistics, search, and stock lists with performance indicators.

### Stock Detail View
Interactive candlestick chart with comprehensive metrics and external resource links.

### Mobile Responsive
Optimized layout for smartphones and tablets.

---

## Troubleshooting

### Port Already in Use

If port 8080 is occupied:

```bash
# Check what's using the port
lsof -i :8080

# Kill the process
kill -9 <PID>

# Or use a different port (edit web_dashboard.py)
```

### Dashboard Not Loading

Check if PostgreSQL is running:

```bash
docker-compose ps
# Should show strategy-z-pg as "Up"

# If not, start it:
docker-compose up -d
```

### No Data Showing

Verify database has data:

```bash
source venv/bin/activate
python -c "
from config.database import config
from db.api import StockDB

config.switch_to_postgresql()
db = StockDB()
print(f'Stocks: {len(db.get_stock_list())}')
"
```

### Slow Performance

If the dashboard is slow:

1. **Reduce stock count** in top_movers (line 114):
   ```python
   for symbol in stocks[:200]:  # Reduce to 50 or 100
   ```

2. **Add caching** (future enhancement)

3. **Use production WSGI server** instead of Flask development server:
   ```bash
   pip install gunicorn
   gunicorn -w 4 -b 0.0.0.0:8080 web_dashboard:app
   ```

---

## Security Notes

### Development Mode
The dashboard runs in Flask development mode by default:
- ⚠️ **DO NOT expose to the internet**
- ✅ Safe for local network use
- ✅ Good for development and testing

### Production Deployment
For production use:

1. **Disable debug mode**:
   ```python
   app.run(debug=False, host='0.0.0.0', port=8080)
   ```

2. **Use production server**:
   ```bash
   gunicorn -w 4 web_dashboard:app
   ```

3. **Add authentication** (if needed)

4. **Use HTTPS** with nginx/Apache reverse proxy

---

## Future Enhancements

### Planned Features
- [ ] Real-time price updates (WebSocket)
- [ ] Custom watchlists (save/load)
- [ ] Price alerts
- [ ] Technical indicators overlay
- [ ] Comparison charts (multiple stocks)
- [ ] Export data (CSV, Excel)
- [ ] Portfolio tracking
- [ ] News feed integration
- [ ] Historical backtesting interface
- [ ] Strategy performance dashboard

### Contribution Ideas
- Add more chart types (line, area, volume)
- Integrate sentiment analysis
- Add earnings calendar
- Create mobile app (React Native)
- Add dark/light theme toggle

---

## External Resources Guide

### Yahoo Finance
**Best for**: Detailed financial statements, analyst ratings, company news
**Features**:
- Real-time quotes
- Financial statements (income, balance sheet, cash flow)
- Analyst estimates
- Historical data
- Options chain
- Company profile

### Finviz
**Best for**: Technical analysis, stock screener, heat maps
**Features**:
- Visual stock charts with indicators
- Sector heat maps
- Stock screener with 70+ filters
- Insider trading data
- News aggregation
- Comparison tools

### MarketWatch
**Best for**: Financial news, market analysis, economic calendar
**Features**:
- Breaking news
- Market commentary
- Economic calendar
- Earnings calendar
- IPO calendar
- Analyst upgrades/downgrades

### Seeking Alpha
**Best for**: Investment research, dividend analysis, earnings transcripts
**Features**:
- Investment ideas and analysis
- Earnings call transcripts
- Dividend data
- Valuation metrics
- Portfolio tracking
- Author ratings

### TradingView
**Best for**: Advanced charting, technical analysis, trading ideas
**Features**:
- Professional charting tools
- 100+ technical indicators
- Drawing tools
- Social trading ideas
- Alerts and notifications
- Paper trading

### Google Finance
**Best for**: Quick overview, simple charts, market news
**Features**:
- Clean, simple interface
- Basic charts
- Related companies
- Market news
- Portfolio tracking
- Currency conversion

---

## Tips for Stock Research

### 1. Start with Overview
- Check Yahoo Finance for basic info and news
- Look at Google Finance for quick price action

### 2. Technical Analysis
- Use TradingView for detailed charts
- Check Finviz for visual technical screening
- Look for support/resistance levels

### 3. Fundamental Analysis
- Review financial statements on Yahoo Finance
- Read analysis on Seeking Alpha
- Check analyst ratings and price targets

### 4. News and Sentiment
- MarketWatch for breaking news
- Seeking Alpha for detailed research
- Finviz for news aggregation

### 5. Timing Your Entry
- Watch for earnings dates (MarketWatch calendar)
- Check insider trading (Finviz)
- Monitor volume on the dashboard

---

## Keyboard Shortcuts

- `Ctrl/Cmd + F` - Focus search box
- `Esc` - Close stock detail modal
- `Tab` - Navigate between tabs
- Click outside modal - Close detail view

---

## Support

For issues or questions:
1. Check [DEPLOYMENT_SUMMARY.md](DEPLOYMENT_SUMMARY.md)
2. Review [MIGRATION_STATUS.md](MIGRATION_STATUS.md)
3. Check dashboard logs: `tail -f dashboard.log`

---

## License

Part of the StockItsMygo stock analysis system.

---

*Last updated: January 4, 2026*
