"""
Queue Modeling.

Models order queue position and execution probability.
"""
import numpy as np
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


class QueueModel:
    """Models order queue position and execution."""
    
    def __init__(self):
        """Initialize queue model."""
        pass
    
    def estimate_queue_position(
        self,
        symbol: str,
        limit_price: float,
        current_bid: float,
        current_ask: float,
        order_side: str = "BUY"
    ) -> Dict[str, Any]:
        """
        Estimate queue position for a limit order.
        
        Args:
            symbol: Trading symbol
            limit_price: Limit order price
            current_bid: Current bid price
            current_ask: Current ask price
            order_side: BUY or SELL
            
        Returns:
            Dict with queue position estimate
        """
        if order_side == "BUY":
            # For buy orders, compare to bid
            if limit_price >= current_ask:
                # Marketable limit order (at or above ask)
                queue_position = "front"  # Will execute immediately
                execution_probability = 0.95
            elif limit_price > current_bid:
                # Between bid and ask
                queue_position = "middle"
                execution_probability = 0.5
            elif limit_price == current_bid:
                # At bid (join queue)
                queue_position = "queue"
                execution_probability = 0.3
            else:
                # Below bid (unlikely to fill)
                queue_position = "back"
                execution_probability = 0.1
        else:  # SELL
            # For sell orders, compare to ask
            if limit_price <= current_bid:
                # Marketable limit order (at or below bid)
                queue_position = "front"
                execution_probability = 0.95
            elif limit_price < current_ask:
                # Between bid and ask
                queue_position = "middle"
                execution_probability = 0.5
            elif limit_price == current_ask:
                # At ask (join queue)
                queue_position = "queue"
                execution_probability = 0.3
            else:
                # Above ask (unlikely to fill)
                queue_position = "back"
                execution_probability = 0.1
        
        return {
            "queue_position": queue_position,
            "execution_probability": float(execution_probability),
            "limit_price": float(limit_price),
            "current_bid": float(current_bid),
            "current_ask": float(current_ask),
            "spread": float(current_ask - current_bid)
        }
    
    def estimate_execution_time(
        self,
        queue_position: str,
        symbol: str,
        order_size: float
    ) -> Dict[str, Any]:
        """
        Estimate execution time based on queue position.
        
        Args:
            queue_position: Queue position (front/middle/queue/back)
            symbol: Trading symbol
            order_size: Order size in shares
            
        Returns:
            Dict with execution time estimates
        """
        # Base execution times (in seconds)
        base_times = {
            "front": 1.0,  # Immediate
            "middle": 30.0,  # 30 seconds
            "queue": 300.0,  # 5 minutes
            "back": 3600.0  # 1 hour (unlikely)
        }
        
        base_time = base_times.get(queue_position, 300.0)
        
        # Adjust for order size (larger orders take longer)
        size_factor = 1.0 + (order_size / 10000.0) * 0.5
        estimated_time = base_time * size_factor
        
        return {
            "estimated_execution_time_seconds": float(estimated_time),
            "estimated_execution_time_minutes": float(estimated_time / 60.0),
            "queue_position": queue_position
        }
    
    def calculate_fill_probability_over_time(
        self,
        execution_probability: float,
        time_elapsed_minutes: float
    ) -> float:
        """
        Calculate fill probability as time elapses.
        
        Args:
            execution_probability: Initial execution probability
            time_elapsed_minutes: Time elapsed since order placement
            
        Returns:
            Updated fill probability
        """
        # Probability increases with time (exponential decay of "no fill")
        # P(fill) = 1 - (1 - P0) * exp(-t/tau)
        tau = 10.0  # Time constant (minutes)
        
        no_fill_prob = 1.0 - execution_probability
        updated_no_fill = no_fill_prob * np.exp(-time_elapsed_minutes / tau)
        updated_fill_prob = 1.0 - updated_no_fill
        
        return float(updated_fill_prob)


class OrderQueueManager:
    """Manages order queue and execution tracking."""
    
    def __init__(self):
        """Initialize queue manager."""
        self.active_orders: Dict[str, Dict[str, Any]] = {}
        self.queue_model = QueueModel()
    
    def add_order(
        self,
        order_id: str,
        symbol: str,
        limit_price: float,
        shares: float,
        order_side: str,
        current_bid: float,
        current_ask: float
    ) -> Dict[str, Any]:
        """
        Add order to queue.
        
        Args:
            order_id: Unique order ID
            symbol: Trading symbol
            limit_price: Limit price
            shares: Number of shares
            order_side: BUY or SELL
            current_bid: Current bid
            current_ask: Current ask
            
        Returns:
            Queue position info
        """
        queue_info = self.queue_model.estimate_queue_position(
            symbol=symbol,
            limit_price=limit_price,
            current_bid=current_bid,
            current_ask=current_ask,
            order_side=order_side
        )
        
        execution_time = self.queue_model.estimate_execution_time(
            queue_position=queue_info["queue_position"],
            symbol=symbol,
            order_size=shares
        )
        
        order_record = {
            "order_id": order_id,
            "symbol": symbol,
            "limit_price": limit_price,
            "shares": shares,
            "order_side": order_side,
            "queue_position": queue_info["queue_position"],
            "execution_probability": queue_info["execution_probability"],
            "estimated_execution_time": execution_time,
            "timestamp": datetime.now().isoformat(),
            "status": "pending"
        }
        
        self.active_orders[order_id] = order_record
        
        return order_record
    
    def update_order_status(
        self,
        order_id: str,
        time_elapsed_minutes: float
    ) -> Dict[str, Any]:
        """
        Update order status based on time elapsed.
        
        Args:
            order_id: Order ID
            time_elapsed_minutes: Time elapsed since order placement
            
        Returns:
            Updated order info
        """
        if order_id not in self.active_orders:
            return {"error": "Order not found"}
        
        order = self.active_orders[order_id]
        
        # Update fill probability
        updated_prob = self.queue_model.calculate_fill_probability_over_time(
            execution_probability=order["execution_probability"],
            time_elapsed_minutes=time_elapsed_minutes
        )
        
        order["updated_execution_probability"] = updated_prob
        order["time_elapsed_minutes"] = time_elapsed_minutes
        
        return order




