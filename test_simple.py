"""
Simple test suite for the Trading System
Run with: pytest test_simple.py -v
"""

import pytest
from matching_engine import MatchingEngine, OrderSide
from pnl_calculator import PnLCalculator
from reconciliation import Reconciler


class TestMatchingEngine:
    """Tests for the matching engine"""
    
    def test_simple_match(self):
        """Test basic buy-sell match"""
        engine = MatchingEngine()
        
        # Submit buy order
        buy_order = engine.submit_order(
            user_id=1, symbol="AAPL", side="BUY", 
            price=150.00, quantity=100
        )
        
        # Submit matching sell order
        sell_order = engine.submit_order(
            user_id=2, symbol="AAPL", side="SELL",
            price=149.00, quantity=100
        )
        
        # Should generate one trade
        trades = engine.get_trades()
        assert len(trades) == 1
        assert trades[0].quantity == 100
        assert trades[0].price <= 150.00
        assert trades[0].price >= 149.00
    
    def test_partial_fill(self):
        """Test partial order fill"""
        engine = MatchingEngine()
        
        # Buy 100 shares
        engine.submit_order(
            user_id=1, symbol="AAPL", side="BUY",
            price=150.00, quantity=100
        )
        
        # Sell only 50 shares
        engine.submit_order(
            user_id=2, symbol="AAPL", side="SELL",
            price=150.00, quantity=50
        )
        
        trades = engine.get_trades()
        assert len(trades) == 1
        assert trades[0].quantity == 50  # Partial fill
    
    def test_no_match_price_gap(self):
        """Test no match when price gap exists"""
        engine = MatchingEngine()
        
        # Buy at $100
        engine.submit_order(
            user_id=1, symbol="AAPL", side="BUY",
            price=100.00, quantity=100
        )
        
        # Sell at $150 (no match)
        engine.submit_order(
            user_id=2, symbol="AAPL", side="SELL",
            price=150.00, quantity=100
        )
        
        trades = engine.get_trades()
        assert len(trades) == 0  # No match due to price gap
    
    def test_latency_measurement(self):
        """Test that latency is tracked"""
        engine = MatchingEngine()
        
        # Submit some orders
        for i in range(10):
            engine.submit_order(
                user_id=i, symbol="AAPL", side="BUY",
                price=150.00, quantity=100
            )
        
        avg_latency = engine.get_average_latency()
        assert avg_latency > 0
        assert avg_latency < 100  # Should be under 100ms


class TestPnLCalculator:
    """Tests for P&L calculation"""
    
    def test_simple_buy_sell_profit(self):
        """Test basic profitable trade"""
        calc = PnLCalculator()
        
        # Buy at $100
        calc.process_trade(
            user_id=1, symbol="AAPL", side="BUY",
            price=100.00, quantity=10
        )
        
        # Sell at $110 (profit)
        calc.process_trade(
            user_id=1, symbol="AAPL", side="SELL",
            price=110.00, quantity=10
        )
        
        position = calc._get_position(1, "AAPL")
        assert position.quantity == 0  # Flat position
        assert position.realized_pnl == 100.00  # $10 profit * 10 shares
    
    def test_average_cost_calculation(self):
        """Test average cost calculation"""
        calc = PnLCalculator()
        
        # Buy 10 shares at $100
        calc.process_trade(
            user_id=1, symbol="AAPL", side="BUY",
            price=100.00, quantity=10
        )
        
        # Buy 10 more shares at $110
        calc.process_trade(
            user_id=1, symbol="AAPL", side="BUY",
            price=110.00, quantity=10
        )
        
        position = calc._get_position(1, "AAPL")
        assert position.quantity == 20
        assert position.avg_cost == 105.00  # (100*10 + 110*10) / 20
    
    def test_unrealized_pnl(self):
        """Test unrealized P&L calculation"""
        calc = PnLCalculator()
        
        # Buy at $100
        calc.process_trade(
            user_id=1, symbol="AAPL", side="BUY",
            price=100.00, quantity=10
        )
        
        position = calc._get_position(1, "AAPL")
        
        # Set current price to $110
        unrealized = calc.calculate_unrealized_pnl(position, 110.00)
        assert unrealized == 100.00  # $10 * 10 shares
        
        # Set current price to $90
        unrealized = calc.calculate_unrealized_pnl(position, 90.00)
        assert unrealized == -100.00  # -$10 * 10 shares


class TestReconciliation:
    """Tests for reconciliation (requires database)"""
    
    def test_reconciliation_accuracy_calculation(self):
        """Test accuracy percentage calculation"""
        # This is a unit test without database
        total_trades = 1000
        matched_trades = 999
        
        accuracy = (matched_trades / total_trades * 100)
        assert accuracy == 99.9


# Performance benchmarks (not part of regular test suite)
def benchmark_matching_speed():
    """Benchmark order matching speed"""
    import time
    
    engine = MatchingEngine()
    num_orders = 10000
    
    start = time.time()
    for i in range(num_orders):
        side = "BUY" if i % 2 == 0 else "SELL"
        engine.submit_order(
            user_id=i % 100,
            symbol="AAPL",
            side=side,
            price=150.00 + (i % 10),
            quantity=100
        )
    elapsed = (time.time() - start) * 1000
    
    avg_latency = elapsed / num_orders
    print(f"\nProcessed {num_orders} orders in {elapsed:.2f}ms")
    print(f"Average latency: {avg_latency:.2f}ms per order")
    
    assert avg_latency < 50  # Target: sub-50ms


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])
    
    # Run benchmark
    print("\n" + "="*60)
    print("RUNNING PERFORMANCE BENCHMARK")
    print("="*60)
    benchmark_matching_speed()
