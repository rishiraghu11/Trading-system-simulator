# Quick Start Guide

Get the Trading System Simulator running in 5 minutes!

## Prerequisites

- Python 3.8 or higher
- MySQL 8.0 or higher
- pip (Python package manager)

## Installation Steps

### 1. Install MySQL

**Ubuntu/Debian:**
```bash
sudo apt-get update
sudo apt-get install mysql-server
sudo systemctl start mysql
```

**macOS:**
```bash
brew install mysql
brew services start mysql
```

**Windows:**
Download and install from [mysql.com](https://dev.mysql.com/downloads/mysql/)

### 2. Clone and Setup

```bash
# Clone the repository
git clone https://github.com/rishiraghu11/trading-system-simulator.git
cd trading-system-simulator

# Install Python dependencies
pip install -r requirements.txt
```

### 3. Configure Database

```bash
# Copy environment template
cp .env.example .env

# Edit .env with your MySQL credentials
nano .env  # or use your preferred editor
```

Update these lines in `.env`:
```
DB_USER=your_mysql_username
DB_PASSWORD=your_mysql_password
```

### 4. Initialize Database

```bash
python setup_database.py
```

You should see:
```
✓ Database setup completed successfully!
✓ All required tables exist
```

### 5. Run Simulation

```bash
# Run with 10,000 orders (default)
python simulate_trading.py

# Or specify custom number of orders
python simulate_trading.py --orders 50000 --users 200
```

## What to Expect

The simulation will:
1. Generate random buy/sell orders
2. Match orders using a priority queue-based engine
3. Execute trades and store them in MySQL
4. Calculate P&L for all positions
5. Run reconciliation checks
6. Display performance metrics

**Expected Output:**
```
MATCHING ENGINE PERFORMANCE
  Total Orders Processed: 10,000
  Average Latency: 45ms
  Total Trades Executed: 5,247

P&L SUMMARY
  Total Realized P&L: $12,456.78
  Accuracy: 99.9%

✓ Target Latency: 50ms (Achieved: 45ms)
✓ Target Accuracy: 99.9% (Achieved: 99.9%)
```

## Troubleshooting

### "Access denied for user"
- Check your MySQL username and password in `.env`
- Ensure MySQL is running: `sudo systemctl status mysql`

### "Module not found"
```bash
pip install -r requirements.txt
```

### "Can't connect to MySQL server"
```bash
# Check if MySQL is running
sudo systemctl start mysql  # Linux
brew services start mysql   # macOS
```

## Next Steps

- View data in MySQL: `mysql -u root -p trading_system`
- Run benchmarks: `python run_benchmarks.py`
- Check the full README.md for advanced features
- Explore individual modules (matching_engine.py, pnl_calculator.py, etc.)

## Project Structure

```
trading_system_simulator/
├── matching_engine.py      # Order matching logic
├── pnl_calculator.py       # P&L calculations
├── reconciliation.py       # Trade reconciliation
├── database.py             # Database operations
├── simulate_trading.py     # Main simulation script
└── setup_database.py       # Database initialization
```

## Quick Commands

```bash
# Initialize database
python setup_database.py

# Run simulation
python simulate_trading.py --orders 10000

# Run with custom parameters
python simulate_trading.py --orders 50000 --users 200

# Test individual modules
python matching_engine.py
python pnl_calculator.py
python reconciliation.py
```

## Performance Targets

| Metric | Target | Typically Achieved |
|--------|--------|-------------------|
| Order Matching Latency | < 50ms | 35-45ms |
| Report Generation | < 600ms | 400-600ms |
| Reconciliation Accuracy | > 99.9% | 99.9-100% |

## Support

If you encounter issues:
1. Check MySQL is running
2. Verify credentials in `.env`
3. Ensure all dependencies are installed
4. Check logs in `trading_system.log`

Happy Trading! 🚀
