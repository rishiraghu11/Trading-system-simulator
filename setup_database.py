"""
Database Setup Script
Initializes the MySQL database and creates all necessary tables
"""

import logging
from database import DatabaseManager
from config import DB_CONFIG

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def setup_database():
    """
    Initialize the trading system database
    Creates database and all required tables with proper indexes
    """
    try:
        logger.info("Starting database setup...")
        
        # Create database manager
        db = DatabaseManager()
        
        # Step 1: Create database
        logger.info(f"Creating database '{DB_CONFIG['database']}'...")
        db.create_database()
        
        # Step 2: Create tables
        logger.info("Creating tables...")
        db.create_tables()
        
        logger.info("✓ Database setup completed successfully!")
        logger.info("\nCreated tables:")
        logger.info("  - orders (with indexes on symbol, user_id, status)")
        logger.info("  - trades (with indexes on symbol, timestamp)")
        logger.info("  - positions (with unique constraint on user_id + symbol)")
        logger.info("  - pnl_history (with indexes on user_id, symbol, timestamp)")
        logger.info("  - reconciliation_log (with index on check_date)")
        
        return True
        
    except Exception as e:
        logger.error(f"✗ Database setup failed: {e}")
        return False


def verify_setup():
    """Verify database setup by checking table existence"""
    try:
        db = DatabaseManager()
        
        # Check if tables exist
        query = """
        SELECT TABLE_NAME 
        FROM INFORMATION_SCHEMA.TABLES 
        WHERE TABLE_SCHEMA = %s
        """
        
        tables = db.execute_query(query, (DB_CONFIG['database'],), fetch=True)
        
        expected_tables = {'orders', 'trades', 'positions', 'pnl_history', 'reconciliation_log'}
        existing_tables = {table['TABLE_NAME'] for table in tables}
        
        if expected_tables.issubset(existing_tables):
            logger.info("✓ All required tables exist")
            return True
        else:
            missing = expected_tables - existing_tables
            logger.error(f"✗ Missing tables: {missing}")
            return False
            
    except Exception as e:
        logger.error(f"✗ Verification failed: {e}")
        return False


def show_table_info():
    """Display information about created tables"""
    try:
        db = DatabaseManager()
        
        query = """
        SELECT 
            TABLE_NAME, 
            TABLE_ROWS, 
            AVG_ROW_LENGTH, 
            DATA_LENGTH,
            CREATE_TIME
        FROM INFORMATION_SCHEMA.TABLES 
        WHERE TABLE_SCHEMA = %s
        ORDER BY TABLE_NAME
        """
        
        tables = db.execute_query(query, (DB_CONFIG['database'],), fetch=True)
        
        print("\n" + "="*80)
        print("TABLE INFORMATION")
        print("="*80)
        print(f"{'Table Name':<25} {'Rows':<10} {'Created':<20}")
        print("-"*80)
        
        for table in tables:
            table_name = table['TABLE_NAME']
            rows = table['TABLE_ROWS'] or 0
            created = table['CREATE_TIME']
            print(f"{table_name:<25} {rows:<10} {str(created):<20}")
        
        print("="*80)
        
    except Exception as e:
        logger.error(f"Error showing table info: {e}")


if __name__ == "__main__":
    print("\n" + "="*80)
    print("TRADING SYSTEM DATABASE SETUP")
    print("="*80 + "\n")
    
    print(f"Database Configuration:")
    print(f"  Host: {DB_CONFIG['host']}")
    print(f"  Port: {DB_CONFIG['port']}")
    print(f"  Database: {DB_CONFIG['database']}")
    print(f"  User: {DB_CONFIG['user']}")
    print()
    
    # Run setup
    success = setup_database()
    
    if success:
        print("\nVerifying setup...")
        if verify_setup():
            print("\n✓ Database is ready for use!")
            show_table_info()
            
            print("\nNext steps:")
            print("  1. Run: python simulate_trading.py --orders 10000")
            print("  2. Check results in the database")
            print("  3. Run reconciliation: python reconciliation.py")
        else:
            print("\n✗ Verification failed. Please check the logs.")
    else:
        print("\n✗ Setup failed. Please check your database credentials in config.py")
        print("\nCommon issues:")
        print("  - MySQL server not running")
        print("  - Incorrect credentials in config.py")
        print("  - Insufficient database permissions")
