"""
P&L (Profit and Loss) Calculator
Handles position tracking, realized/unrealized P&L calculation
"""

import logging
from typing import Dict, List, Tuple
from dataclasses import dataclass, field
from database import get_db

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class Position:
    """Represents a trading position"""
    user_id: int
    symbol: str
    quantity: int = 0  # Positive for long, negative for short
    avg_cost: float = 0.0
    realized_pnl: float = 0.0
    
    def is_flat(self) -> bool:
        """Check if position is flat (no holdings)"""
        return self.quantity == 0


@dataclass
class PnLReport:
    """P&L report for a user or portfolio"""
    user_id: int
    total_realized_pnl: float = 0.0
    total_unrealized_pnl: float = 0.0
    total_pnl: float = 0.0
    positions: List[Dict] = field(default_factory=list)
    num_trades: int = 0


class PnLCalculator:
    """
    Calculates profit and loss for trading positions
    Uses FIFO (First In First Out) for position tracking
    """
    
    def __init__(self):
        self.db = get_db()
        self.positions = {}  # (user_id, symbol) -> Position
        self.current_prices = {}  # symbol -> current_price
    
    def _get_position(self, user_id: int, symbol: str) -> Position:
        """Get or create position for user and symbol"""
        key = (user_id, symbol)
        if key not in self.positions:
            self.positions[key] = Position(user_id=user_id, symbol=symbol)
        return self.positions[key]
    
    def process_trade(self, user_id: int, symbol: str, side: str, 
                     price: float, quantity: int, trade_id: int = None):
        """
        Process a trade and update position and P&L
        
        Args:
            user_id: User ID
            symbol: Trading symbol
            side: 'BUY' or 'SELL'
            price: Trade price
            quantity: Trade quantity
            trade_id: Optional trade ID for database tracking
        """
        position = self._get_position(user_id, symbol)
        
        if side == 'BUY':
            self._process_buy(position, price, quantity)
        else:  # SELL
            self._process_sell(position, price, quantity)
        
        # Update database if trade_id provided
        if trade_id:
            self._update_position_in_db(position, trade_id)
    
    def _process_buy(self, position: Position, price: float, quantity: int):
        """Process a buy trade - increases position"""
        old_quantity = position.quantity
        old_avg_cost = position.avg_cost
        
        # Calculate new average cost
        if old_quantity >= 0:
            # Adding to long position or opening new long
            total_cost = (old_quantity * old_avg_cost) + (quantity * price)
            position.quantity = old_quantity + quantity
            position.avg_cost = total_cost / position.quantity if position.quantity > 0 else 0
        else:
            # Covering short position
            if quantity <= abs(old_quantity):
                # Partial or full cover
                realized_pnl = quantity * (old_avg_cost - price)
                position.realized_pnl += realized_pnl
                position.quantity = old_quantity + quantity
                
                if position.quantity == 0:
                    position.avg_cost = 0
            else:
                # Cover short and go long
                cover_quantity = abs(old_quantity)
                realized_pnl = cover_quantity * (old_avg_cost - price)
                position.realized_pnl += realized_pnl
                
                remaining_quantity = quantity - cover_quantity
                position.quantity = remaining_quantity
                position.avg_cost = price
    
    def _process_sell(self, position: Position, price: float, quantity: int):
        """Process a sell trade - decreases position"""
        old_quantity = position.quantity
        old_avg_cost = position.avg_cost
        
        # Calculate new average cost
        if old_quantity <= 0:
            # Adding to short position or opening new short
            total_cost = (abs(old_quantity) * old_avg_cost) + (quantity * price)
            position.quantity = old_quantity - quantity
            position.avg_cost = total_cost / abs(position.quantity) if position.quantity != 0 else 0
        else:
            # Closing long position
            if quantity <= old_quantity:
                # Partial or full close
                realized_pnl = quantity * (price - old_avg_cost)
                position.realized_pnl += realized_pnl
                position.quantity = old_quantity - quantity
                
                if position.quantity == 0:
                    position.avg_cost = 0
            else:
                # Close long and go short
                close_quantity = old_quantity
                realized_pnl = close_quantity * (price - old_avg_cost)
                position.realized_pnl += realized_pnl
                
                remaining_quantity = quantity - close_quantity
                position.quantity = -remaining_quantity
                position.avg_cost = price
    
    def calculate_unrealized_pnl(self, position: Position, current_price: float) -> float:
        """Calculate unrealized P&L for a position"""
        if position.quantity == 0:
            return 0.0
        
        if position.quantity > 0:
            # Long position
            return position.quantity * (current_price - position.avg_cost)
        else:
            # Short position
            return abs(position.quantity) * (position.avg_cost - current_price)
    
    def set_current_price(self, symbol: str, price: float):
        """Set current market price for a symbol"""
        self.current_prices[symbol] = price
    
    def get_position_summary(self, user_id: int, symbol: str) -> Dict:
        """Get summary of a specific position"""
        position = self._get_position(user_id, symbol)
        current_price = self.current_prices.get(symbol, position.avg_cost)
        
        unrealized_pnl = self.calculate_unrealized_pnl(position, current_price)
        
        return {
            'user_id': user_id,
            'symbol': symbol,
            'quantity': position.quantity,
            'avg_cost': round(position.avg_cost, 2),
            'current_price': round(current_price, 2),
            'market_value': round(abs(position.quantity) * current_price, 2),
            'cost_basis': round(abs(position.quantity) * position.avg_cost, 2),
            'realized_pnl': round(position.realized_pnl, 2),
            'unrealized_pnl': round(unrealized_pnl, 2),
            'total_pnl': round(position.realized_pnl + unrealized_pnl, 2)
        }
    
    def generate_user_pnl_report(self, user_id: int) -> PnLReport:
        """Generate complete P&L report for a user"""
        report = PnLReport(user_id=user_id)
        
        for (uid, symbol), position in self.positions.items():
            if uid != user_id:
                continue
            
            current_price = self.current_prices.get(symbol, position.avg_cost)
            unrealized_pnl = self.calculate_unrealized_pnl(position, current_price)
            
            report.total_realized_pnl += position.realized_pnl
            report.total_unrealized_pnl += unrealized_pnl
            
            if position.quantity != 0 or position.realized_pnl != 0:
                report.positions.append({
                    'symbol': symbol,
                    'quantity': position.quantity,
                    'avg_cost': round(position.avg_cost, 2),
                    'current_price': round(current_price, 2),
                    'realized_pnl': round(position.realized_pnl, 2),
                    'unrealized_pnl': round(unrealized_pnl, 2),
                    'total_pnl': round(position.realized_pnl + unrealized_pnl, 2)
                })
        
        report.total_pnl = report.total_realized_pnl + report.total_unrealized_pnl
        return report
    
    def generate_portfolio_pnl_report(self) -> Dict:
        """Generate P&L report for entire portfolio (all users)"""
        total_realized = 0.0
        total_unrealized = 0.0
        user_reports = []
        
        # Get unique users
        users = set(user_id for (user_id, _) in self.positions.keys())
        
        for user_id in users:
            user_report = self.generate_user_pnl_report(user_id)
            total_realized += user_report.total_realized_pnl
            total_unrealized += user_report.total_unrealized_pnl
            
            user_reports.append({
                'user_id': user_id,
                'realized_pnl': round(user_report.total_realized_pnl, 2),
                'unrealized_pnl': round(user_report.total_unrealized_pnl, 2),
                'total_pnl': round(user_report.total_pnl, 2),
                'num_positions': len(user_report.positions)
            })
        
        return {
            'total_realized_pnl': round(total_realized, 2),
            'total_unrealized_pnl': round(total_unrealized, 2),
            'total_pnl': round(total_realized + total_unrealized, 2),
            'num_users': len(users),
            'user_reports': sorted(user_reports, key=lambda x: x['total_pnl'], reverse=True)
        }
    
    def _update_position_in_db(self, position: Position, trade_id: int):
        """Update position in database"""
        try:
            # Update positions table
            self.db.upsert_position(
                user_id=position.user_id,
                symbol=position.symbol,
                quantity_delta=position.quantity,  # This will be handled by ON DUPLICATE KEY UPDATE
                avg_cost=position.avg_cost,
                realized_pnl_delta=position.realized_pnl
            )
            
            # Insert P&L history record
            if position.realized_pnl != 0:
                query = """
                INSERT INTO pnl_history (user_id, symbol, trade_id, realized_pnl)
                VALUES (%s, %s, %s, %s)
                """
                self.db.execute_query(
                    query, 
                    (position.user_id, position.symbol, trade_id, position.realized_pnl)
                )
        except Exception as e:
            logger.error(f"Error updating position in database: {e}")
    
    def load_positions_from_db(self):
        """Load all positions from database"""
        try:
            query = "SELECT user_id, symbol, quantity, avg_cost, realized_pnl FROM positions"
            positions = self.db.execute_query(query, fetch=True)
            
            for pos in positions:
                key = (pos['user_id'], pos['symbol'])
                self.positions[key] = Position(
                    user_id=pos['user_id'],
                    symbol=pos['symbol'],
                    quantity=pos['quantity'],
                    avg_cost=float(pos['avg_cost']),
                    realized_pnl=float(pos['realized_pnl'])
                )
            
            logger.info(f"Loaded {len(positions)} positions from database")
        except Exception as e:
            logger.error(f"Error loading positions from database: {e}")
    
    def reset(self):
        """Reset calculator (useful for testing)"""
        self.positions = {}
        self.current_prices = {}


# Example usage
if __name__ == "__main__":
    calculator = PnLCalculator()
    
    # Simulate some trades
    print("Processing trades...")
    
    # User 1 trades
    calculator.process_trade(user_id=1, symbol="AAPL", side="BUY", price=150.00, quantity=100)
    calculator.process_trade(user_id=1, symbol="AAPL", side="BUY", price=151.00, quantity=50)
    calculator.process_trade(user_id=1, symbol="AAPL", side="SELL", price=152.00, quantity=75)
    
    # User 2 trades
    calculator.process_trade(user_id=2, symbol="GOOGL", side="BUY", price=2800.00, quantity=10)
    calculator.process_trade(user_id=2, symbol="GOOGL", side="SELL", price=2850.00, quantity=5)
    
    # Set current prices
    calculator.set_current_price("AAPL", 153.00)
    calculator.set_current_price("GOOGL", 2900.00)
    
    # Generate reports
    print("\n--- User 1 P&L Report ---")
    user1_report = calculator.generate_user_pnl_report(1)
    print(f"Total Realized P&L: ${user1_report.total_realized_pnl:.2f}")
    print(f"Total Unrealized P&L: ${user1_report.total_unrealized_pnl:.2f}")
    print(f"Total P&L: ${user1_report.total_pnl:.2f}")
    print("\nPositions:")
    for pos in user1_report.positions:
        print(f"  {pos['symbol']}: {pos['quantity']} shares @ ${pos['avg_cost']:.2f}")
        print(f"    Realized P&L: ${pos['realized_pnl']:.2f}")
        print(f"    Unrealized P&L: ${pos['unrealized_pnl']:.2f}")
    
    print("\n--- Portfolio P&L Report ---")
    portfolio_report = calculator.generate_portfolio_pnl_report()
    print(f"Total Portfolio P&L: ${portfolio_report['total_pnl']:.2f}")
    print(f"Number of Users: {portfolio_report['num_users']}")
    print("\nTop Users by P&L:")
    for user in portfolio_report['user_reports'][:5]:
        print(f"  User {user['user_id']}: ${user['total_pnl']:.2f} "
              f"({user['num_positions']} positions)")
