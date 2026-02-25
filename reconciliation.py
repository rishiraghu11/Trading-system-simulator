"""
Trade Reconciliation Module
Validates data integrity and accuracy across trade capture systems
"""

import logging
from datetime import datetime, date
from typing import Dict, List, Tuple
from database import get_db

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class Reconciler:
    """
    Trade reconciliation system
    Validates trades against orders and checks for data discrepancies
    """
    
    def __init__(self):
        self.db = get_db()
        self.discrepancies = []
    
    def reconcile_trades(self, check_date: date = None) -> Dict:
        """
        Perform full trade reconciliation for a given date
        
        Args:
            check_date: Date to reconcile (defaults to today)
        
        Returns:
            Dictionary with reconciliation results including accuracy
        """
        if check_date is None:
            check_date = date.today()
        
        logger.info(f"Starting reconciliation for {check_date}")
        
        # Get all trades for the date
        trades = self._get_trades_for_date(check_date)
        total_trades = len(trades)
        
        if total_trades == 0:
            logger.warning(f"No trades found for {check_date}")
            return {
                'check_date': check_date,
                'total_trades': 0,
                'matched_trades': 0,
                'discrepancies': 0,
                'accuracy': 100.0,
                'issues': []
            }
        
        # Run reconciliation checks
        matched_trades = 0
        issues = []
        
        for trade in trades:
            is_valid, error_msg = self._validate_trade(trade)
            if is_valid:
                matched_trades += 1
            else:
                issues.append({
                    'trade_id': trade['trade_id'],
                    'error': error_msg,
                    'timestamp': trade['timestamp']
                })
                self.discrepancies.append({
                    'date': check_date,
                    'trade_id': trade['trade_id'],
                    'issue': error_msg
                })
        
        discrepancies = total_trades - matched_trades
        accuracy = (matched_trades / total_trades * 100) if total_trades > 0 else 0
        
        # Log results to database
        self._log_reconciliation_results(
            check_date, total_trades, matched_trades, discrepancies, accuracy
        )
        
        result = {
            'check_date': str(check_date),
            'total_trades': total_trades,
            'matched_trades': matched_trades,
            'discrepancies': discrepancies,
            'accuracy': round(accuracy, 2),
            'issues': issues
        }
        
        logger.info(f"Reconciliation complete: {accuracy:.2f}% accuracy "
                   f"({matched_trades}/{total_trades} trades matched)")
        
        return result
    
    def _get_trades_for_date(self, check_date: date) -> List[Dict]:
        """Get all trades for a specific date"""
        try:
            return self.db.get_trades_by_date(check_date)
        except Exception as e:
            logger.error(f"Error fetching trades: {e}")
            return []
    
    def _validate_trade(self, trade: Dict) -> Tuple[bool, str]:
        """
        Validate a single trade against business rules
        
        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            # Check 1: Verify buy and sell orders exist
            buy_order = self._get_order(trade['buy_order_id'])
            sell_order = self._get_order(trade['sell_order_id'])
            
            if not buy_order:
                return False, f"Buy order {trade['buy_order_id']} not found"
            
            if not sell_order:
                return False, f"Sell order {trade['sell_order_id']} not found"
            
            # Check 2: Verify symbols match
            if buy_order['symbol'] != trade['symbol']:
                return False, f"Buy order symbol mismatch: {buy_order['symbol']} vs {trade['symbol']}"
            
            if sell_order['symbol'] != trade['symbol']:
                return False, f"Sell order symbol mismatch: {sell_order['symbol']} vs {trade['symbol']}"
            
            # Check 3: Verify sides are correct
            if buy_order['side'] != 'BUY':
                return False, f"Buy order has incorrect side: {buy_order['side']}"
            
            if sell_order['side'] != 'SELL':
                return False, f"Sell order has incorrect side: {sell_order['side']}"
            
            # Check 4: Verify trade price is within bid-ask spread
            if trade['price'] > buy_order['price']:
                return False, f"Trade price {trade['price']} exceeds buy price {buy_order['price']}"
            
            if trade['price'] < sell_order['price']:
                return False, f"Trade price {trade['price']} below sell price {sell_order['price']}"
            
            # Check 5: Verify quantity is valid
            if trade['quantity'] <= 0:
                return False, f"Invalid trade quantity: {trade['quantity']}"
            
            if trade['quantity'] > buy_order['quantity']:
                return False, f"Trade quantity {trade['quantity']} exceeds buy order quantity {buy_order['quantity']}"
            
            if trade['quantity'] > sell_order['quantity']:
                return False, f"Trade quantity {trade['quantity']} exceeds sell order quantity {sell_order['quantity']}"
            
            # Check 6: Verify timestamp ordering
            if trade['timestamp'] < buy_order['timestamp']:
                return False, "Trade timestamp before buy order timestamp"
            
            if trade['timestamp'] < sell_order['timestamp']:
                return False, "Trade timestamp before sell order timestamp"
            
            # All checks passed
            return True, ""
            
        except Exception as e:
            logger.error(f"Error validating trade {trade.get('trade_id')}: {e}")
            return False, f"Validation error: {str(e)}"
    
    def _get_order(self, order_id: int) -> Dict:
        """Get order by ID"""
        try:
            query = "SELECT * FROM orders WHERE order_id = %s"
            results = self.db.execute_query(query, (order_id,), fetch=True)
            return results[0] if results else None
        except Exception as e:
            logger.error(f"Error fetching order {order_id}: {e}")
            return None
    
    def _log_reconciliation_results(self, check_date: date, total_trades: int,
                                   matched_trades: int, discrepancies: int,
                                   accuracy: float):
        """Log reconciliation results to database"""
        try:
            query = """
            INSERT INTO reconciliation_log 
            (check_date, total_trades, matched_trades, discrepancies, accuracy)
            VALUES (%s, %s, %s, %s, %s)
            """
            self.db.execute_query(
                query,
                (check_date, total_trades, matched_trades, discrepancies, accuracy)
            )
        except Exception as e:
            logger.error(f"Error logging reconciliation results: {e}")
    
    def get_reconciliation_history(self, days: int = 30) -> List[Dict]:
        """Get reconciliation history for last N days"""
        try:
            query = """
            SELECT check_date, total_trades, matched_trades, 
                   discrepancies, accuracy, timestamp
            FROM reconciliation_log
            ORDER BY check_date DESC
            LIMIT %s
            """
            return self.db.execute_query(query, (days,), fetch=True)
        except Exception as e:
            logger.error(f"Error fetching reconciliation history: {e}")
            return []
    
    def check_data_integrity(self) -> Dict:
        """
        Perform comprehensive data integrity checks
        Returns summary of any data quality issues
        """
        issues = []
        
        # Check for orphaned trades (trades without corresponding orders)
        try:
            query = """
            SELECT t.trade_id, t.buy_order_id, t.sell_order_id
            FROM trades t
            LEFT JOIN orders o1 ON t.buy_order_id = o1.order_id
            LEFT JOIN orders o2 ON t.sell_order_id = o2.order_id
            WHERE o1.order_id IS NULL OR o2.order_id IS NULL
            """
            orphaned_trades = self.db.execute_query(query, fetch=True)
            if orphaned_trades:
                issues.append({
                    'type': 'orphaned_trades',
                    'count': len(orphaned_trades),
                    'description': 'Trades without corresponding orders'
                })
        except Exception as e:
            logger.error(f"Error checking orphaned trades: {e}")
        
        # Check for negative quantities
        try:
            query = "SELECT COUNT(*) as count FROM trades WHERE quantity <= 0"
            result = self.db.execute_query(query, fetch=True)
            if result and result[0]['count'] > 0:
                issues.append({
                    'type': 'negative_quantities',
                    'count': result[0]['count'],
                    'description': 'Trades with zero or negative quantities'
                })
        except Exception as e:
            logger.error(f"Error checking negative quantities: {e}")
        
        # Check for duplicate trades
        try:
            query = """
            SELECT buy_order_id, sell_order_id, COUNT(*) as count
            FROM trades
            GROUP BY buy_order_id, sell_order_id
            HAVING count > 1
            """
            duplicates = self.db.execute_query(query, fetch=True)
            if duplicates:
                issues.append({
                    'type': 'duplicate_trades',
                    'count': len(duplicates),
                    'description': 'Duplicate trade records'
                })
        except Exception as e:
            logger.error(f"Error checking duplicates: {e}")
        
        return {
            'total_issues': len(issues),
            'is_clean': len(issues) == 0,
            'issues': issues
        }
    
    def fix_common_issues(self) -> Dict:
        """
        Attempt to automatically fix common data issues
        Returns summary of fixes applied
        """
        fixes_applied = []
        
        # Delete trades with invalid quantities
        try:
            query = "DELETE FROM trades WHERE quantity <= 0"
            rows_deleted = self.db.execute_query(query)
            if rows_deleted:
                fixes_applied.append({
                    'fix': 'deleted_invalid_quantities',
                    'rows_affected': rows_deleted
                })
        except Exception as e:
            logger.error(f"Error fixing invalid quantities: {e}")
        
        logger.info(f"Applied {len(fixes_applied)} fixes")
        return {'fixes_applied': fixes_applied}
    
    def get_accuracy_stats(self) -> Dict:
        """Get overall accuracy statistics"""
        try:
            query = """
            SELECT 
                AVG(accuracy) as avg_accuracy,
                MIN(accuracy) as min_accuracy,
                MAX(accuracy) as max_accuracy,
                COUNT(*) as total_checks
            FROM reconciliation_log
            """
            result = self.db.execute_query(query, fetch=True)
            if result:
                stats = result[0]
                return {
                    'average_accuracy': round(float(stats['avg_accuracy'] or 0), 2),
                    'min_accuracy': round(float(stats['min_accuracy'] or 0), 2),
                    'max_accuracy': round(float(stats['max_accuracy'] or 0), 2),
                    'total_reconciliation_checks': stats['total_checks']
                }
        except Exception as e:
            logger.error(f"Error getting accuracy stats: {e}")
        
        return {
            'average_accuracy': 0.0,
            'min_accuracy': 0.0,
            'max_accuracy': 0.0,
            'total_reconciliation_checks': 0
        }


# Example usage
if __name__ == "__main__":
    reconciler = Reconciler()
    
    # Perform reconciliation for today
    print("Running trade reconciliation...")
    result = reconciler.reconcile_trades()
    
    print("\n--- Reconciliation Results ---")
    print(f"Date: {result['check_date']}")
    print(f"Total Trades: {result['total_trades']}")
    print(f"Matched Trades: {result['matched_trades']}")
    print(f"Discrepancies: {result['discrepancies']}")
    print(f"Accuracy: {result['accuracy']}%")
    
    if result['issues']:
        print("\nIssues Found:")
        for issue in result['issues'][:5]:  # Show first 5 issues
            print(f"  Trade {issue['trade_id']}: {issue['error']}")
    
    # Check data integrity
    print("\n--- Data Integrity Check ---")
    integrity = reconciler.check_data_integrity()
    print(f"Total Issues: {integrity['total_issues']}")
    print(f"Data Clean: {integrity['is_clean']}")
    
    if integrity['issues']:
        for issue in integrity['issues']:
            print(f"  {issue['type']}: {issue['count']} - {issue['description']}")
    
    # Get accuracy statistics
    print("\n--- Overall Accuracy Statistics ---")
    stats = reconciler.get_accuracy_stats()
    print(f"Average Accuracy: {stats['average_accuracy']}%")
    print(f"Total Reconciliation Checks: {stats['total_reconciliation_checks']}")
