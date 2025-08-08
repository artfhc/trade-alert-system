"""
Pipeline processing for trade alert system

Replaces the monolithic 200+ line process_trade_alert() function with
a clean chain of single-responsibility handlers.
"""

from .context import ProcessingContext
from .handlers import (
    Handler,
    ParseAlertHandler,
    ValidateWhitelistHandler, 
    LLMAnalysisHandler,
    LoggingHandler
)
from .pipeline import ProcessingPipeline, create_default_pipeline

__all__ = [
    'ProcessingContext',
    'Handler',
    'ParseAlertHandler',
    'ValidateWhitelistHandler',
    'LLMAnalysisHandler', 
    'LoggingHandler',
    'ProcessingPipeline',
    'create_default_pipeline'
]