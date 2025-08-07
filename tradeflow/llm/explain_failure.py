"""
LLM-generated error summaries and failure explanations
"""

# TODO: Implement FailureExplainer class with methods:
#   - generate_explanation(self, error_context, trade_data) -> str
#   - categorize_failure(self, error_message) -> str
#   - create_user_friendly_message(self, technical_error) -> str
#   - suggest_resolution(self, error_category) -> str

# TODO: Create error categorization system:
#   - API failures (Alpaca, Gmail, etc.)
#   - Parsing errors (LLM email parsing)
#   - Validation errors (invalid symbols, sizing)
#   - Market-related errors (closed markets, halted stocks)
#   - Authentication/permission errors

# TODO: Implement LLM prompts for error explanation:
#   - System prompt for error analysis
#   - Context-aware explanations based on failure type
#   - User-friendly language generation
#   - Actionable resolution suggestions

# TODO: Add error context collection:
#   - Capture relevant trade data
#   - Include error timestamps
#   - Collect stack traces safely
#   - Add environment information

# TODO: Implement explanation templates:
#   - Common error patterns
#   - Template-based responses for frequent issues
#   - Fallback explanations for unknown errors
#   - Escalation paths for critical failures

# TODO: Add user communication features:
#   - Email notifications with explanations
#   - Slack/Discord alerts
#   - Dashboard error summaries
#   - Error trend analysis

# TODO: Implement caching and optimization:
#   - Cache explanations for similar errors
#   - Rate limit LLM calls for explanations
#   - Prioritize critical vs informational errors
#   - Batch explanation generation

# TODO: Add monitoring and feedback:
#   - Track explanation quality
#   - Monitor resolution success rates
#   - Collect user feedback on explanations
#   - Improve prompts based on outcomes