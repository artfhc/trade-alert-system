"""
Data models for Alert, TradeEvent, and enums
"""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Dict, Any, Optional


class TradeStatus(Enum):
    PENDING = "pending"
    SUCCESS = "success"
    FAILED = "fail"


class TradeAction(Enum):
    BUY = "Buy"
    SELL = "Sell"


@dataclass
class Alert:
    """
    Represents a trading alert from any source (Gmail, Discord, etc.)
    """
    source: str  # gmail, discord, telegram, etc.
    content: str  # raw email/message content
    timestamp: datetime
    metadata: Dict[str, Any]  # sender, subject, message_id, etc.
    
    def __post_init__(self):
        """Validate alert data after initialization"""
        if not self.source:
            raise ValueError("Alert source cannot be empty")
        if not self.content:
            raise ValueError("Alert content cannot be empty")
        if not isinstance(self.timestamp, datetime):
            raise ValueError("Alert timestamp must be a datetime object")
        if not isinstance(self.metadata, dict):
            raise ValueError("Alert metadata must be a dictionary")


@dataclass
class TradeEvent:
    """
    Represents a trade execution event for logging
    """
    trade_id: str  # e.g., "email-20250802-001"
    source: str  # "gmail"
    ticker: str  # "COIN"
    action: TradeAction  # Buy/Sell
    sizing: str  # "5%"
    status: TradeStatus  # pending/success/fail
    order_id: Optional[str]  # Alpaca order reference
    message: str  # "Executed" or error info
    timestamp: datetime  # UTC datetime
    
    def __post_init__(self):
        """Validate trade event data after initialization"""
        if not self.trade_id:
            raise ValueError("Trade ID cannot be empty")
        if not self.source:
            raise ValueError("Trade source cannot be empty")
        if not self.ticker:
            raise ValueError("Trade ticker cannot be empty")
        if not isinstance(self.action, TradeAction):
            raise ValueError("Trade action must be a TradeAction enum")
        if not isinstance(self.status, TradeStatus):
            raise ValueError("Trade status must be a TradeStatus enum")
        if not isinstance(self.timestamp, datetime):
            raise ValueError("Trade timestamp must be a datetime object")


# TODO: Add more specific validation methods for ticker symbols, sizing formats, etc.