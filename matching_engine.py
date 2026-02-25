"""
Order Matching Engine using Priority Queues
Implements price-time priority matching for buy and sell orders
"""

import heapq
import time
import logging
from dataclasses import dataclass
from typing import List, Tuple, Optional
from enum import Enum

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class OrderSide(Enum):
    BUY = "BUY"
    SELL = "SELL"


class OrderStatus(Enum):
    PENDING = "PENDING"
    PARTIAL = "PARTIAL"
    FILLED = "FILLED"
    CANCELLED = "CANCELLED"


@dataclass
class Order:
    """Represents a trading order"""
    order_id: int
    user_id: int
    symbol: str
    side: OrderSide
    price: float
    quantity: int
    timestamp: float
    status: OrderStatus = OrderStatus.PENDING
    filled_quantity: int = 0
    
    def remaining_quantity(self):
        """Get remaining unfilled quantity"""
        return self.quantity - self.filled_quantity
    
    def __lt__(self, other):
        """
        Comparison for heap operations
        Buy orders: Higher price has priority (max heap behavior)
        Sell orders: Lower price has priority (min heap behavior)
        If prices equal, earlier timestamp has priority
        """
        if self.side == OrderSide.BUY:
            # For buy orders, we want higher prices first (negate for min heap)
            if self.price != other.price:
                return self.price > other.price
            return self.timestamp < other.timestamp
        else:  # SELL
            # For sell orders, we want lower prices first
            if self.price != other.price:
                return self.price < other.price
            return self.timestamp < other.timestamp


@dataclass
class Trade:
    """Represents an executed trade"""
    trade_id: Optional[int]
    buy_order_id: int
    sell_order_id: int
    symbol: str
    price: float
    quantity: int
    timestamp: float


class OrderBook:
    """
    Order book for a single symbol
    Maintains separate buy and sell queues using heaps
    """
    
    def __init__(self, symbol: str):
        self.symbol = symbol
        self.buy_orders = []  # Max heap (highest price first)
        self.sell_orders = []  # Min heap (lowest price first)
        self.order_map = {}  # order_id -> Order
        
    def add_order(self, order: Order):
        """Add order to the order book"""
        if order.side == OrderSide.BUY:
            heapq.heappush(self.buy_orders, order)
        else:
            heapq.heappush(self.sell_orders, order)
        
        self.order_map[order.order_id] = order
    
    def remove_filled_orders(self):
        """Clean up fully filled orders from heaps"""
        # Clean buy orders
        while self.buy_orders and self.buy_orders[0].remaining_quantity() == 0:
            heapq.heappop(self.buy_orders)
        
        # Clean sell orders
        while self.sell_orders and self.sell_orders[0].remaining_quantity() == 0:
            heapq.heappop(self.sell_orders)
    
    def can_match(self) -> bool:
        """Check if top buy and sell orders can be matched"""
        if not self.buy_orders or not self.sell_orders:
            return False
        
        best_buy = self.buy_orders[0]
        best_sell = self.sell_orders[0]
        
        # Match if buy price >= sell price
        return best_buy.price >= best_sell.price
    
    def get_best_buy(self) -> Optional[Order]:
        """Get best buy order"""
        return self.buy_orders[0] if self.buy_orders else None
    
    def get_best_sell(self) -> Optional[Order]:
        """Get best sell order"""
        return self.sell_orders[0] if self.sell_orders else None


class MatchingEngine:
    """
    Central matching engine for processing orders
    Maintains order books for multiple symbols
    """
    
    def __init__(self):
        self.order_books = {}  # symbol -> OrderBook
        self.trades = []
        self.next_order_id = 1
        self.next_trade_id = 1
        self.total_latency = 0
        self.order_count = 0
        
    def get_or_create_order_book(self, symbol: str) -> OrderBook:
        """Get order book for symbol, create if doesn't exist"""
        if symbol not in self.order_books:
            self.order_books[symbol] = OrderBook(symbol)
        return self.order_books[symbol]
    
    def submit_order(self, user_id: int, symbol: str, side: str, 
                    price: float, quantity: int) -> Order:
        """
        Submit a new order to the matching engine
        Returns the created order
        """
        start_time = time.time()
        
        order = Order(
            order_id=self.next_order_id,
            user_id=user_id,
            symbol=symbol,
            side=OrderSide(side),
            price=price,
            quantity=quantity,
            timestamp=time.time()
        )
        
        self.next_order_id += 1
        
        # Get or create order book for this symbol
        order_book = self.get_or_create_order_book(symbol)
        
        # Add order to book
        order_book.add_order(order)
        
        # Try to match orders
        self._match_orders(order_book)
        
        # Track latency
        latency = (time.time() - start_time) * 1000  # Convert to ms
        self.total_latency += latency
        self.order_count += 1
        
        return order
    
    def _match_orders(self, order_book: OrderBook):
        """
        Match orders in the order book
        Implements price-time priority matching
        """
        while order_book.can_match():
            buy_order = order_book.get_best_buy()
            sell_order = order_book.get_best_sell()
            
            if not buy_order or not sell_order:
                break
            
            # Calculate trade quantity (minimum of remaining quantities)
            trade_quantity = min(
                buy_order.remaining_quantity(),
                sell_order.remaining_quantity()
            )
            
            # Trade executes at the price of the order that arrived first
            trade_price = (buy_order.price if buy_order.timestamp < sell_order.timestamp 
                          else sell_order.price)
            
            # Create trade
            trade = Trade(
                trade_id=self.next_trade_id,
                buy_order_id=buy_order.order_id,
                sell_order_id=sell_order.order_id,
                symbol=order_book.symbol,
                price=trade_price,
                quantity=trade_quantity,
                timestamp=time.time()
            )
            
            self.next_trade_id += 1
            self.trades.append(trade)
            
            # Update order filled quantities
            buy_order.filled_quantity += trade_quantity
            sell_order.filled_quantity += trade_quantity
            
            # Update order statuses
            if buy_order.remaining_quantity() == 0:
                buy_order.status = OrderStatus.FILLED
            elif buy_order.filled_quantity > 0:
                buy_order.status = OrderStatus.PARTIAL
            
            if sell_order.remaining_quantity() == 0:
                sell_order.status = OrderStatus.FILLED
            elif sell_order.filled_quantity > 0:
                sell_order.status = OrderStatus.PARTIAL
            
            # Clean up filled orders
            order_book.remove_filled_orders()
            
            logger.debug(f"Trade executed: {trade.symbol} {trade.quantity}@{trade.price}")
    
    def get_average_latency(self) -> float:
        """Get average order processing latency in milliseconds"""
        if self.order_count == 0:
            return 0.0
        return self.total_latency / self.order_count
    
    def get_trades(self) -> List[Trade]:
        """Get all executed trades"""
        return self.trades
    
    def get_order_book_snapshot(self, symbol: str) -> dict:
        """Get current state of order book"""
        if symbol not in self.order_books:
            return {"buy_orders": [], "sell_orders": []}
        
        order_book = self.order_books[symbol]
        
        # Get active orders
        buy_orders = [
            {
                "order_id": o.order_id,
                "price": o.price,
                "quantity": o.remaining_quantity()
            }
            for o in sorted(order_book.buy_orders, reverse=True)[:10]
            if o.remaining_quantity() > 0
        ]
        
        sell_orders = [
            {
                "order_id": o.order_id,
                "price": o.price,
                "quantity": o.remaining_quantity()
            }
            for o in sorted(order_book.sell_orders)[:10]
            if o.remaining_quantity() > 0
        ]
        
        return {
            "symbol": symbol,
            "buy_orders": buy_orders,
            "sell_orders": sell_orders,
            "spread": (sell_orders[0]["price"] - buy_orders[0]["price"]) 
                     if buy_orders and sell_orders else 0
        }
    
    def get_statistics(self) -> dict:
        """Get engine statistics"""
        return {
            "total_orders": self.order_count,
            "total_trades": len(self.trades),
            "average_latency_ms": round(self.get_average_latency(), 2),
            "symbols_traded": len(self.order_books),
            "match_rate": (len(self.trades) / self.order_count * 100) 
                         if self.order_count > 0 else 0
        }
    
    def reset(self):
        """Reset the matching engine (useful for testing)"""
        self.order_books = {}
        self.trades = []
        self.next_order_id = 1
        self.next_trade_id = 1
        self.total_latency = 0
        self.order_count = 0


# Example usage
if __name__ == "__main__":
    # Create matching engine
    engine = MatchingEngine()
    
    # Submit some sample orders
    print("Submitting orders...")
    
    # Buy orders
    engine.submit_order(user_id=1, symbol="AAPL", side="BUY", price=150.00, quantity=100)
    engine.submit_order(user_id=2, symbol="AAPL", side="BUY", price=149.50, quantity=200)
    engine.submit_order(user_id=3, symbol="AAPL", side="BUY", price=150.50, quantity=150)
    
    # Sell orders
    engine.submit_order(user_id=4, symbol="AAPL", side="SELL", price=150.25, quantity=120)
    engine.submit_order(user_id=5, symbol="AAPL", side="SELL", price=149.75, quantity=100)
    engine.submit_order(user_id=6, symbol="AAPL", side="SELL", price=151.00, quantity=80)
    
    # Print results
    print("\n--- Matching Engine Statistics ---")
    stats = engine.get_statistics()
    for key, value in stats.items():
        print(f"{key}: {value}")
    
    print("\n--- Executed Trades ---")
    for trade in engine.get_trades():
        print(f"Trade {trade.trade_id}: {trade.symbol} "
              f"{trade.quantity}@${trade.price:.2f} "
              f"(Buy Order: {trade.buy_order_id}, Sell Order: {trade.sell_order_id})")
    
    print("\n--- Order Book Snapshot ---")
    snapshot = engine.get_order_book_snapshot("AAPL")
    print(f"Symbol: {snapshot['symbol']}")
    print(f"Spread: ${snapshot['spread']:.2f}")
    print(f"Best Buy Orders: {snapshot['buy_orders'][:3]}")
    print(f"Best Sell Orders: {snapshot['sell_orders'][:3]}")
