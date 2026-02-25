"""
Database connection and query management for the Trading System
"""

import mysql.connector
from mysql.connector import Error
from contextlib import contextmanager
import logging
from config import DB_CONFIG

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DatabaseManager:
    """Manages database connections and operations"""
    
    def __init__(self):
        self.config = DB_CONFIG
        self.connection_pool = None
        
    @contextmanager
    def get_connection(self):
        """Context manager for database connections"""
        connection = None
        try:
            connection = mysql.connector.connect(**self.config)
            yield connection
        except Error as e:
            logger.error(f"Database connection error: {e}")
            raise
        finally:
            if connection and connection.is_connected():
                connection.close()
    
    def execute_query(self, query, params=None, fetch=False):
        """Execute a single query"""
        with self.get_connection() as conn:
            cursor = conn.cursor(dictionary=True)
            try:
                cursor.execute(query, params or ())
                if fetch:
                    result = cursor.fetchall()
                    return result
                conn.commit()
                return cursor.lastrowid
            except Error as e:
                logger.error(f"Query execution error: {e}")
                conn.rollback()
                raise
            finally:
                cursor.close()
    
    def execute_many(self, query, data):
        """Execute batch insert/update operations"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            try:
                cursor.executemany(query, data)
                conn.commit()
                return cursor.rowcount
            except Error as e:
                logger.error(f"Batch execution error: {e}")
                conn.rollback()
                raise
            finally:
                cursor.close()
    
    def create_database(self):
        """Create the trading system database if it doesn't exist"""
        try:
            # Connect without specifying database
            config = self.config.copy()
            db_name = config.pop('database')
            
            connection = mysql.connector.connect(**config)
            cursor = connection.cursor()
            
            cursor.execute(f"CREATE DATABASE IF NOT EXISTS {db_name}")
            logger.info(f"Database '{db_name}' created or already exists")
            
            cursor.close()
            connection.close()
        except Error as e:
            logger.error(f"Database creation error: {e}")
            raise
    
    def create_tables(self):
        """Create all necessary tables with proper indexes"""
        
        # Orders table - stores all incoming orders
        create_orders_table = """
        CREATE TABLE IF NOT EXISTS orders (
            order_id BIGINT AUTO_INCREMENT PRIMARY KEY,
            user_id INT NOT NULL,
            symbol VARCHAR(10) NOT NULL,
            side ENUM('BUY', 'SELL') NOT NULL,
            price DECIMAL(10, 2) NOT NULL,
            quantity INT NOT NULL,
            status ENUM('PENDING', 'PARTIAL', 'FILLED', 'CANCELLED') DEFAULT 'PENDING',
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            INDEX idx_symbol_side_price (symbol, side, price),
            INDEX idx_user_timestamp (user_id, timestamp),
            INDEX idx_status (status)
        ) ENGINE=InnoDB;
        """
        
        # Trades table - stores executed trades
        create_trades_table = """
        CREATE TABLE IF NOT EXISTS trades (
            trade_id BIGINT AUTO_INCREMENT PRIMARY KEY,
            buy_order_id BIGINT NOT NULL,
            sell_order_id BIGINT NOT NULL,
            symbol VARCHAR(10) NOT NULL,
            price DECIMAL(10, 2) NOT NULL,
            quantity INT NOT NULL,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (buy_order_id) REFERENCES orders(order_id),
            FOREIGN KEY (sell_order_id) REFERENCES orders(order_id),
            INDEX idx_symbol_timestamp (symbol, timestamp),
            INDEX idx_timestamp (timestamp)
        ) ENGINE=InnoDB;
        """
        
        # Positions table - tracks current positions for each user
        create_positions_table = """
        CREATE TABLE IF NOT EXISTS positions (
            position_id BIGINT AUTO_INCREMENT PRIMARY KEY,
            user_id INT NOT NULL,
            symbol VARCHAR(10) NOT NULL,
            quantity INT NOT NULL DEFAULT 0,
            avg_cost DECIMAL(10, 2) NOT NULL DEFAULT 0.00,
            realized_pnl DECIMAL(15, 2) NOT NULL DEFAULT 0.00,
            last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            UNIQUE KEY unique_user_symbol (user_id, symbol),
            INDEX idx_user_id (user_id)
        ) ENGINE=InnoDB;
        """
        
        # PnL History table - tracks historical P&L
        create_pnl_history_table = """
        CREATE TABLE IF NOT EXISTS pnl_history (
            pnl_id BIGINT AUTO_INCREMENT PRIMARY KEY,
            user_id INT NOT NULL,
            symbol VARCHAR(10) NOT NULL,
            trade_id BIGINT NOT NULL,
            realized_pnl DECIMAL(15, 2) NOT NULL,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (trade_id) REFERENCES trades(trade_id),
            INDEX idx_user_timestamp (user_id, timestamp),
            INDEX idx_symbol_timestamp (symbol, timestamp)
        ) ENGINE=InnoDB;
        """
        
        # Reconciliation log table
        create_reconciliation_table = """
        CREATE TABLE IF NOT EXISTS reconciliation_log (
            log_id BIGINT AUTO_INCREMENT PRIMARY KEY,
            check_date DATE NOT NULL,
            total_trades INT NOT NULL,
            matched_trades INT NOT NULL,
            discrepancies INT NOT NULL,
            accuracy DECIMAL(5, 2) NOT NULL,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            INDEX idx_check_date (check_date)
        ) ENGINE=InnoDB;
        """
        
        tables = [
            create_orders_table,
            create_trades_table,
            create_positions_table,
            create_pnl_history_table,
            create_reconciliation_table
        ]
        
        for table_query in tables:
            try:
                self.execute_query(table_query)
                logger.info("Table created successfully")
            except Error as e:
                logger.error(f"Error creating table: {e}")
                raise
    
    def insert_order(self, user_id, symbol, side, price, quantity):
        """Insert a new order"""
        query = """
        INSERT INTO orders (user_id, symbol, side, price, quantity)
        VALUES (%s, %s, %s, %s, %s)
        """
        return self.execute_query(query, (user_id, symbol, side, price, quantity))
    
    def bulk_insert_orders(self, orders):
        """Bulk insert orders for better performance"""
        query = """
        INSERT INTO orders (user_id, symbol, side, price, quantity)
        VALUES (%s, %s, %s, %s, %s)
        """
        return self.execute_many(query, orders)
    
    def insert_trade(self, buy_order_id, sell_order_id, symbol, price, quantity):
        """Insert a new trade"""
        query = """
        INSERT INTO trades (buy_order_id, sell_order_id, symbol, price, quantity)
        VALUES (%s, %s, %s, %s, %s)
        """
        return self.execute_query(query, (buy_order_id, sell_order_id, symbol, price, quantity))
    
    def bulk_insert_trades(self, trades):
        """Bulk insert trades for better performance"""
        query = """
        INSERT INTO trades (buy_order_id, sell_order_id, symbol, price, quantity)
        VALUES (%s, %s, %s, %s, %s)
        """
        return self.execute_many(query, trades)
    
    def update_order_status(self, order_id, status):
        """Update order status"""
        query = "UPDATE orders SET status = %s WHERE order_id = %s"
        self.execute_query(query, (status, order_id))
    
    def get_trades_by_date(self, date):
        """Get all trades for a specific date"""
        query = """
        SELECT * FROM trades 
        WHERE DATE(timestamp) = %s
        ORDER BY timestamp
        """
        return self.execute_query(query, (date,), fetch=True)
    
    def get_user_positions(self, user_id):
        """Get all positions for a user"""
        query = """
        SELECT * FROM positions 
        WHERE user_id = %s AND quantity != 0
        """
        return self.execute_query(query, (user_id,), fetch=True)
    
    def upsert_position(self, user_id, symbol, quantity_delta, avg_cost, realized_pnl_delta):
        """Update or insert a position"""
        query = """
        INSERT INTO positions (user_id, symbol, quantity, avg_cost, realized_pnl)
        VALUES (%s, %s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE
            quantity = quantity + VALUES(quantity),
            avg_cost = VALUES(avg_cost),
            realized_pnl = realized_pnl + VALUES(realized_pnl)
        """
        self.execute_query(query, (user_id, symbol, quantity_delta, avg_cost, realized_pnl_delta))
    
    def get_pnl_report(self):
        """Generate P&L report - optimized query"""
        query = """
        SELECT 
            p.user_id,
            p.symbol,
            p.quantity,
            p.avg_cost,
            p.realized_pnl,
            SUM(ph.realized_pnl) as total_realized_pnl
        FROM positions p
        LEFT JOIN pnl_history ph ON p.user_id = ph.user_id AND p.symbol = ph.symbol
        GROUP BY p.user_id, p.symbol, p.quantity, p.avg_cost, p.realized_pnl
        """
        return self.execute_query(query, fetch=True)
    
    def clear_all_data(self):
        """Clear all data from tables (for testing)"""
        tables = ['pnl_history', 'trades', 'positions', 'orders', 'reconciliation_log']
        for table in tables:
            self.execute_query(f"DELETE FROM {table}")
        logger.info("All data cleared from database")


# Convenience function for getting database manager instance
def get_db():
    """Get database manager instance"""
    return DatabaseManager()
