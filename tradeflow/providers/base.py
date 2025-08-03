"""
Abstract AlertProvider class - Base for all alert sources
"""

# TODO: Define abstract AlertProvider base class with methods:
#   - parse_alert(self, raw_data) -> Alert
#   - validate_alert(self, alert) -> bool
#   - get_source_name(self) -> str

# TODO: Add abstract methods that implementations must override:
#   - extract_metadata(self, raw_data) -> dict
#   - sanitize_content(self, content) -> str

# TODO: Implement common validation logic:
#   - Required fields check
#   - Content length limits
#   - Timestamp validation

# TODO: Add logging interface for alert processing events

# TODO: Define AlertProvider registry for dynamic provider loading