"""
Abstract AlertProvider class - Base for all alert sources
"""

from abc import ABC, abstractmethod
from typing import Dict, Any
import logging
from datetime import datetime

from ..core.models import Alert


class AlertProvider(ABC):
    """
    Abstract base class for all alert providers (Gmail, Discord, Telegram, etc.)
    """
    
    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
    
    @abstractmethod
    def parse_alert(self, raw_data: Dict[str, Any]) -> Alert:
        """
        Parse raw alert data into a standardized Alert object
        
        Args:
            raw_data: Raw data from the alert source (Pub/Sub message, webhook payload, etc.)
            
        Returns:
            Alert: Standardized alert object
            
        Raises:
            ValueError: If the raw data cannot be parsed
        """
        pass
    
    @abstractmethod
    def get_source_name(self) -> str:
        """
        Get the name of this alert source
        
        Returns:
            str: Source name (e.g., "gmail", "discord", "telegram")
        """
        pass
    
    @abstractmethod
    def extract_metadata(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract metadata from raw alert data
        
        Args:
            raw_data: Raw data from the alert source
            
        Returns:
            Dict: Metadata dictionary with source-specific fields
        """
        pass
    
    def sanitize_content(self, content: str) -> str:
        """
        Sanitize alert content (remove sensitive info, normalize formatting)
        
        Args:
            content: Raw content string
            
        Returns:
            str: Sanitized content
        """
        if not content:
            return ""
        
        # Basic sanitization - can be overridden by subclasses
        sanitized = content.strip()
        
        # Remove excessive whitespace
        import re
        sanitized = re.sub(r'\s+', ' ', sanitized)
        
        return sanitized
    
    def validate_alert(self, alert: Alert) -> bool:
        """
        Validate that an alert meets basic requirements
        
        Args:
            alert: Alert object to validate
            
        Returns:
            bool: True if valid, False otherwise
        """
        try:
            # Check required fields
            if not alert.source:
                self.logger.error("Alert missing source")
                return False
            
            if not alert.content:
                self.logger.error("Alert missing content")
                return False
            
            if not isinstance(alert.timestamp, datetime):
                self.logger.error("Alert timestamp is not a datetime object")
                return False
            
            # Check content length limits
            if len(alert.content) > 10000:  # 10KB limit
                self.logger.error(f"Alert content too long: {len(alert.content)} chars")
                return False
            
            # Timestamp should be recent (within last 24 hours for safety)
            time_diff = datetime.utcnow() - alert.timestamp
            if time_diff.total_seconds() > 86400:  # 24 hours
                self.logger.warning(f"Alert timestamp is old: {alert.timestamp}")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error validating alert: {e}")
            return False


# AlertProvider registry for dynamic loading
_ALERT_PROVIDERS: Dict[str, type] = {}


def register_provider(name: str, provider_class: type):
    """Register an alert provider class"""
    _ALERT_PROVIDERS[name] = provider_class


def get_provider(name: str) -> AlertProvider:
    """Get an alert provider instance by name"""
    if name not in _ALERT_PROVIDERS:
        raise ValueError(f"Unknown alert provider: {name}")
    
    return _ALERT_PROVIDERS[name]()