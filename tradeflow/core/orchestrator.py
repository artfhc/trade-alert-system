"""
TradeFlow controller - Main orchestration logic for trade execution
"""

# TODO: Implement TradeFlow class that coordinates the entire trade execution flow
# TODO: Define TradeFlow.__init__(self, alert_provider, email_parser, ...)
# TODO: Implement execute_trade(self, alert) method that:
#   - Parses email using LLM to extract trade details and sizing
#   - Calculates position size
#   - Executes trade via Alpaca
#   - Logs result to Google Sheets
#   - Generates error explanations if needed
# TODO: Add error handling and retry logic
# TODO: Implement trade deduplication logic using Trade ID
# TODO: Add logging throughout the flow