"""
LLM sizing extraction from scraped HTML forum content
"""

# TODO: Implement ForumLLMParser class with methods:
#   - extract_sizing(self, forum_content) -> str
#   - parse_percentage(self, content) -> float
#   - parse_dollar_amount(self, content) -> float
#   - validate_sizing_format(self, sizing) -> bool

# TODO: Create LLM prompts for sizing extraction:
#   - System prompt for position sizing
#   - Examples of different sizing formats:
#     * "Buy 5% of portfolio"
#     * "Risk $1000 on this trade"
#     * "Full position (10%)"
#     * "Half position"
#   - Output format specification (percentage or dollar)

# TODO: Implement sizing normalization:
#   - Convert various formats to standard percentage
#   - Handle relative sizing ("half position", "double down")
#   - Map text descriptions to percentages
#   - Validate reasonable sizing ranges (0.1% - 20%)

# TODO: Add context-aware parsing:
#   - Consider portfolio size context
#   - Handle multiple sizing mentions
#   - Extract stop-loss information
#   - Identify risk management notes

# TODO: Implement error handling:
#   - No sizing information found
#   - Ambiguous sizing instructions
#   - LLM parsing failures
#   - Invalid sizing values

# TODO: Add safety checks:
#   - Maximum position size limits
#   - Minimum position size thresholds
#   - Risk management validation
#   - Confirmation for large positions