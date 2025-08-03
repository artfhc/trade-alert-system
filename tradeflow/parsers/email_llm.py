"""
LLM-based email parser for extracting trade information
"""

# TODO: Implement EmailLLMParser class with methods:
#   - parse_email(self, email_content) -> dict
#   - extract_ticker(self, content) -> str
#   - extract_action(self, content) -> str (Buy/Sell)
#   - extract_reference_link(self, content) -> str (forum link)

# TODO: Create LLM prompt templates for email parsing:
#   - System prompt for trade alert extraction
#   - Few-shot examples for different email formats
#   - Structured output schema (JSON)

# TODO: Implement LLM client integration:
#   - OpenAI API client setup
#   - Claude API client setup
#   - Fallback between providers
#   - Token usage tracking

# TODO: Add validation for LLM responses:
#   - Check required fields are present
#   - Validate ticker symbols
#   - Ensure action is Buy/Sell
#   - Verify forum link format

# TODO: Implement error handling:
#   - LLM API failures
#   - Invalid response formats
#   - Rate limiting
#   - Retry logic with exponential backoff

# TODO: Add prompt engineering utilities:
#   - Dynamic prompt building
#   - Context length management
#   - Response caching for similar emails