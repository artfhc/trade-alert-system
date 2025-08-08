"""
Processing pipeline orchestrator

Coordinates the execution of pipeline handlers, replacing the monolithic
process_trade_alert() function with a clean, configurable pipeline.
"""

import logging
from datetime import datetime
from typing import Dict, Any

from .context import ProcessingContext
from .handlers import (
    Handler,
    ParseAlertHandler,
    ValidateWhitelistHandler,
    LLMAnalysisHandler,
    LoggingHandler
)
from ..services.container import ServiceContainer

logger = logging.getLogger(__name__)


class ProcessingPipeline:
    """
    Main pipeline orchestrator for trade alert processing
    
    Replaces the monolithic 200+ line process_trade_alert() function
    with a configurable chain of single-responsibility handlers.
    """
    
    def __init__(self, container: ServiceContainer):
        self.container = container
        self._pipeline_handler: Handler = self._build_pipeline()
        logger.info("ProcessingPipeline initialized")
    
    async def process(self, raw_data: Dict[str, Any]) -> ProcessingContext:
        """
        Process a trade alert through the pipeline
        
        Args:
            raw_data: Raw Pub/Sub message data
            
        Returns:
            ProcessingContext with results
        """
        # Create processing context
        context = ProcessingContext(
            raw_data=raw_data,
            timestamp=datetime.utcnow()
        )
        
        # Log detailed input information
        logger.info(f"🚀 Starting pipeline processing")
        logger.info(f"📥 Raw data type: {type(raw_data)}")
        logger.info(f"📥 Raw data keys: {list(raw_data.keys()) if isinstance(raw_data, dict) else 'Not a dict'}")
        
        # Log raw data structure (safely)
        try:
            import json
            raw_data_preview = json.dumps(raw_data, indent=2)[:500]
            logger.info(f"📥 Raw data preview: {raw_data_preview}...")
        except Exception as e:
            logger.info(f"📥 Raw data preview failed: {e}, data: {str(raw_data)[:200]}")
        
        message_id = context.raw_data.get('message', {}).get('messageId', 'unknown')
        logger.info(f"📧 Processing message ID: {message_id}")
        
        # Execute pipeline
        try:
            logger.info("🔄 Starting pipeline execution through handler chain")
            result_context = self._pipeline_handler.handle(context)
            
            # Log completion
            if result_context.is_successful():
                logger.info(f"✅ Pipeline processing completed successfully: {result_context.processing_status}")
            else:
                logger.warning(f"⚠️ Pipeline processing completed with issues: {result_context.processing_status}")
                if result_context.error_message:
                    logger.warning(f"Error: {result_context.error_message}")
            
            # Log summary
            self._log_processing_summary(result_context)
            
            return result_context
            
        except Exception as e:
            logger.error(f"❌ Pipeline execution failed: {e}")
            context.set_error(f"Pipeline execution failed: {str(e)}", "pipeline_error")
            return context
    
    def _build_pipeline(self) -> Handler:
        """
        Build the processing pipeline chain
        
        Creates the chain: Parse → Validate → LLMAnalysis → Logging
        """
        logger.info("Building processing pipeline")
        
        # Create handler chain using method chaining
        pipeline = (ParseAlertHandler(self.container)
                   .set_next(ValidateWhitelistHandler(self.container))
                   .set_next(LLMAnalysisHandler(self.container))
                   .set_next(LoggingHandler(self.container)))
        
        logger.info("Processing pipeline built: ParseAlert → ValidateWhitelist → LLMAnalysis → Logging")
        return pipeline
    
    def _log_processing_summary(self, context: ProcessingContext) -> None:
        """Log summary of processing results"""
        summary = context.get_summary()
        
        logger.info("📊 Processing Summary:")
        logger.info(f"   Message ID: {summary['message_id']}")
        logger.info(f"   Sender: {summary['sender']}")
        logger.info(f"   Status: {summary['processing_status']}")
        logger.info(f"   Whitelist: {summary['whitelist_status']}")
        logger.info(f"   LLM Provider: {summary['llm_provider']}")
        
        if summary['llm_is_trading_alert'] is not None:
            logger.info(f"   Is Trading Alert: {summary['llm_is_trading_alert']}")
            logger.info(f"   Trades Count: {summary['llm_trades_count']}")
        
        if summary['processing_time_ms'] > 0:
            logger.info(f"   LLM Processing Time: {summary['processing_time_ms']:.1f}ms")
        
        logger.info(f"   Completed Handlers: {', '.join(summary['completed_handlers'])}")
        
        if summary['error_message']:
            logger.info(f"   Error: {summary['error_message']}")


class ProcessingPipelineBuilder:
    """
    Builder for creating custom processing pipelines
    
    Allows for flexible pipeline configuration and testing
    """
    
    def __init__(self, container: ServiceContainer):
        self.container = container
        self._handlers = []
    
    def add_handler(self, handler_class, *args, **kwargs) -> 'ProcessingPipelineBuilder':
        """Add a handler to the pipeline"""
        handler = handler_class(self.container, *args, **kwargs)
        self._handlers.append(handler)
        return self
    
    def add_parse_alert(self) -> 'ProcessingPipelineBuilder':
        """Add ParseAlertHandler to pipeline"""
        return self.add_handler(ParseAlertHandler)
    
    def add_validate_whitelist(self) -> 'ProcessingPipelineBuilder':
        """Add ValidateWhitelistHandler to pipeline"""
        return self.add_handler(ValidateWhitelistHandler)
    
    def add_llm_analysis(self) -> 'ProcessingPipelineBuilder':
        """Add LLMAnalysisHandler to pipeline"""
        return self.add_handler(LLMAnalysisHandler)
    
    def add_logging(self) -> 'ProcessingPipelineBuilder':
        """Add LoggingHandler to pipeline"""
        return self.add_handler(LoggingHandler)
    
    def build(self) -> ProcessingPipeline:
        """Build the custom pipeline"""
        if not self._handlers:
            raise ValueError("Pipeline must have at least one handler")
        
        # Chain handlers together
        for i in range(len(self._handlers) - 1):
            self._handlers[i].set_next(self._handlers[i + 1])
        
        # Create pipeline with custom handler chain
        pipeline = ProcessingPipeline.__new__(ProcessingPipeline)
        pipeline.container = self.container
        pipeline._pipeline_handler = self._handlers[0]
        
        logger.info(f"Custom pipeline built with {len(self._handlers)} handlers")
        return pipeline


def create_default_pipeline(container: ServiceContainer) -> ProcessingPipeline:
    """Create the standard processing pipeline"""
    return ProcessingPipeline(container)


def create_minimal_pipeline(container: ServiceContainer) -> ProcessingPipeline:
    """Create a minimal pipeline for testing (parse + logging only)"""
    builder = ProcessingPipelineBuilder(container)
    return (builder
            .add_parse_alert()
            .add_logging()
            .build())


def create_no_llm_pipeline(container: ServiceContainer) -> ProcessingPipeline:
    """Create pipeline without LLM analysis"""
    builder = ProcessingPipelineBuilder(container)
    return (builder
            .add_parse_alert()
            .add_validate_whitelist()
            .add_logging()
            .build())