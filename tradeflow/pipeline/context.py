"""
Processing context for pipeline handlers

Contains all state and data that flows through the processing pipeline,
replacing scattered variables and state management from the monolithic approach.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Any, Optional, List
from ..core.models import Alert
from ..parsers.email_llm import ParseResult


@dataclass
class ProcessingContext:
    """
    Context object that flows through the processing pipeline
    
    Contains all state, data, and metadata needed by pipeline handlers.
    Replaces scattered local variables from the monolithic function.
    """
    
    # Input data
    raw_data: Dict[str, Any]
    timestamp: datetime = field(default_factory=datetime.utcnow)
    
    # Processing state
    processing_status: str = "received"
    error_message: Optional[str] = None
    whitelist_status: str = "pending_validation"
    
    # Parsed objects
    alert: Optional[Alert] = None
    
    # LLM Analysis results
    llm_parse_result: Optional[ParseResult] = None
    llm_provider: str = "none"
    processing_time_ms: float = 0.0
    
    # Metadata for logging and tracking
    message_id: str = "unknown"
    sender: str = "unknown"
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    # Handler execution tracking
    completed_handlers: List[str] = field(default_factory=list)
    current_handler: Optional[str] = None
    
    def mark_handler_complete(self, handler_name: str) -> None:
        """Mark a handler as completed"""
        if handler_name not in self.completed_handlers:
            self.completed_handlers.append(handler_name)
        self.current_handler = None
    
    def start_handler(self, handler_name: str) -> None:
        """Mark a handler as currently executing"""
        self.current_handler = handler_name
    
    def set_error(self, error_message: str, status: str = "error") -> None:
        """Set error state for the context"""
        self.error_message = error_message
        self.processing_status = status
    
    def is_successful(self) -> bool:
        """Check if processing completed successfully"""
        return self.processing_status in ["completed", "parsed_trading_alert", "parsed_non_trading"]
    
    def has_error(self) -> bool:
        """Check if processing encountered an error"""
        return self.error_message is not None
    
    def should_continue_processing(self) -> bool:
        """Determine if pipeline should continue processing"""
        # Continue if not explicitly stopped or blocked
        # Allow processing to continue even with non-critical errors
        return self.processing_status not in ["blocked", "completed"]
    
    def get_summary(self) -> Dict[str, Any]:
        """Get summary information for logging"""
        return {
            "message_id": self.message_id,
            "sender": self.sender,
            "processing_status": self.processing_status,
            "whitelist_status": self.whitelist_status,
            "error_message": self.error_message,
            "llm_provider": self.llm_provider,
            "llm_is_trading_alert": self.llm_parse_result.is_trading_alert if self.llm_parse_result else None,
            "llm_trades_count": len(self.llm_parse_result.trades) if self.llm_parse_result and self.llm_parse_result.trades else 0,
            "processing_time_ms": self.processing_time_ms,
            "completed_handlers": self.completed_handlers,
            "timestamp": self.timestamp.isoformat()
        }