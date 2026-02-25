"""
Configuration settings for the Trading System Simulator
"""

import os
from dotenv import load_dotenv

# Load environment variables from .env file if it exists
load_dotenv()

# Database Configuration
DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': 'Rishiraghu@11',
    'database': 'trading_system',
    'port': 3306
}

# Trading Configuration
TRADING_CONFIG = {
    'symbols': ['AAPL', 'GOOGL', 'MSFT', 'AMZN', 'TSLA', 'META', 'NVDA', 'JPM'],
    'min_price': 50.0,
    'max_price': 500.0,
    'min_quantity': 10,
    'max_quantity': 1000,
    'price_tick': 0.01,  # Minimum price increment
}

# Performance Thresholds
PERFORMANCE_CONFIG = {
    'target_matching_latency_ms': 50,  # Target order matching latency
    'target_report_time_ms': 600,      # Target report generation time
    'target_reconciliation_accuracy': 99.9,  # Target accuracy percentage
    'batch_size': 1000,                # Batch size for database operations
}

# Logging Configuration
LOGGING_CONFIG = {
    'level': 'INFO',
    'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    'file': 'trading_system.log'
}

# Testing Configuration
TEST_CONFIG = {
    'num_test_orders': 10000,
    'num_test_users': 100,
    'test_date_range_days': 30,
}
