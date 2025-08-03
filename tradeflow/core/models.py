"""
Data models for Alert, TradeEvent, and enums
"""

# TODO: Define Alert dataclass/model with fields:
#   - source (gmail, discord, etc.)
#   - content (raw email/message content)
#   - timestamp
#   - metadata (sender, subject, etc.)

# TODO: Define TradeEvent dataclass/model with fields:
#   - trade_id (e.g., "email-20250802-001")
#   - source ("gmail")
#   - ticker ("COIN")
#   - action ("Buy"/"Sell")
#   - sizing ("5%")
#   - status ("pending"/"success"/"fail")
#   - order_id (Alpaca order reference)
#   - message ("Executed" or error info)
#   - timestamp (UTC datetime)

# TODO: Define TradeStatus enum:
#   - PENDING
#   - SUCCESS
#   - FAILED

# TODO: Define TradeAction enum:
#   - BUY
#   - SELL

# TODO: Add validation methods to ensure data integrity