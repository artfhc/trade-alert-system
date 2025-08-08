"""
Pipeline handlers for processing trade alerts

Each handler has a single responsibility, replacing the monolithic
process_trade_alert() function with clean, testable components.
"""

import logging
import time
from abc import ABC, abstractmethod
from typing import Optional

from .context import ProcessingContext
from ..services.container import ServiceContainer
from ..core.models import Alert

logger = logging.getLogger(__name__)


class Handler(ABC):
    """
    Base class for pipeline handlers
    
    Implements Chain of Responsibility pattern with consistent error handling
    and logging. Each handler focuses on a single responsibility.
    """
    
    def __init__(self, container: ServiceContainer):
        self.container = container
        self._next_handler: Optional['Handler'] = None
    
    def set_next(self, handler: 'Handler') -> 'Handler':
        """Set the next handler in the chain"""
        self._next_handler = handler
        return handler
    
    def handle(self, context: ProcessingContext) -> ProcessingContext:
        """
        Process the context and pass to next handler
        
        Template method that provides consistent error handling
        and logging for all handlers.
        """
        handler_name = self.__class__.__name__
        context.start_handler(handler_name)
        
        try:
            logger.info(f"🔄 Processing with {handler_name}")
            
            # Skip processing if context has errors or should not continue
            if not context.should_continue_processing():
                logger.info(f"⏭️  Skipping {handler_name} - processing stopped")
                return self.handle_next(context)
            
            # Execute handler-specific logic
            self.process(context)
            
            # Mark handler as completed
            context.mark_handler_complete(handler_name)
            logger.info(f"✅ {handler_name} completed successfully")
            
        except Exception as e:
            error_message = f"{handler_name} failed: {str(e)}"
            context.set_error(error_message, "error")
            logger.error(f"❌ {error_message}")
        
        # Continue to next handler
        return self.handle_next(context)
    
    @abstractmethod
    def process(self, context: ProcessingContext) -> None:
        """Handler-specific processing logic"""
        pass
    
    def handle_next(self, context: ProcessingContext) -> ProcessingContext:
        """Pass context to next handler if available"""
        if self._next_handler:
            return self._next_handler.handle(context)
        return context


class ParseAlertHandler(Handler):
    """
    Parse raw Pub/Sub data into Alert object
    
    Replaces the alert parsing section from the monolithic function
    """
    
    def process(self, context: ProcessingContext) -> None:
        gmail_provider = self.container.get_optional("gmail_provider")
        
        if not gmail_provider:
            # Gmail provider not available - try to extract basic info from Pub/Sub message
            logger.warning("⚠️ Gmail provider not available - attempting basic Pub/Sub parsing")
            alert = self._parse_pubsub_message_basic(context.raw_data)
        else:
            # Use Gmail provider for full parsing
            alert = gmail_provider.parse_alert(context.raw_data)
        
        # Update context
        context.alert = alert
        context.message_id = alert.metadata.get('message_id', 'unknown')
        context.sender = alert.metadata.get('sender', 'unknown')
        context.metadata = alert.metadata
        context.processing_status = "parsed"
        
        logger.info(f"📧 Alert parsed from {context.sender}")
        logger.info(f"📝 Content preview: {alert.content[:100]}...")
    
    def _parse_pubsub_message_basic(self, raw_data: dict) -> 'Alert':
        """
        Basic parsing of Pub/Sub message when Gmail provider is not available
        
        This creates a minimal Alert object from the Pub/Sub message data,
        allowing the pipeline to continue processing even without Gmail API access.
        """
        from datetime import datetime
        from ..core.models import Alert
        import base64
        import json
        
        message = raw_data.get('message', {})
        message_id = message.get('messageId', 'unknown')
        publish_time = message.get('publishTime', datetime.utcnow().isoformat())
        
        # Try to decode the base64 data
        email_content = "Unable to decode email content"
        try:
            if 'data' in message:
                decoded_data = base64.b64decode(message['data']).decode('utf-8')
                # The decoded data might be JSON or raw email content
                try:
                    # Try parsing as JSON first (Gmail API format)
                    email_data = json.loads(decoded_data)
                    email_content = email_data.get('snippet', email_data.get('body', decoded_data))
                except json.JSONDecodeError:
                    # Treat as raw email content
                    email_content = decoded_data
        except Exception as e:
            logger.warning(f"Could not decode Pub/Sub message data: {e}")
        
        # Create basic alert with available information
        alert = Alert(
            source="gmail_pubsub_basic",
            content=email_content,
            timestamp=datetime.utcnow(),
            metadata={
                'message_id': message_id,
                'publish_time': publish_time,
                'sender': 'unknown',
                'subject': 'Gmail API Not Available',
                'parsing_method': 'basic_pubsub',
                'note': 'Parsed without Gmail API access - limited metadata available'
            }
        )
        
        logger.info(f"📧 Created basic alert from Pub/Sub message: {message_id}")
        return alert


class ValidateWhitelistHandler(Handler):
    """
    Validate sender against whitelist configuration
    
    Replaces the whitelist validation logic from the monolithic function
    """
    
    def process(self, context: ProcessingContext) -> None:
        if not context.alert:
            raise ValueError("No alert available for whitelist validation")
        
        gmail_provider = self.container.get("gmail_provider")
        sender = context.sender
        
        # Check if whitelists are configured
        has_sender_whitelist = bool(self.container.config.gmail_sender_whitelist)
        has_domain_whitelist = bool(self.container.config.gmail_domain_whitelist)
        
        if not has_sender_whitelist and not has_domain_whitelist:
            context.whitelist_status = "no_whitelist"
            logger.info("📂 No whitelist configured - allowing all senders")
            return
        
        # Validate sender and domain
        sender_ok = not has_sender_whitelist or gmail_provider.validate_sender(sender)
        domain_ok = not has_domain_whitelist or gmail_provider._is_domain_whitelisted(sender)
        
        # Allow if EITHER check passes
        if sender_ok or domain_ok:
            context.whitelist_status = "allowed"
            logger.info(f"✅ Sender {sender} passed whitelist validation")
        else:
            context.whitelist_status = "blocked"
            context.set_error(f"Sender '{sender}' not in whitelist", "blocked")
            logger.warning(f"🚫 Sender {sender} blocked by whitelist")


class LLMAnalysisHandler(Handler):
    """
    Process email content with LLM for trade analysis
    
    Replaces the LLM processing section from the monolithic function
    """
    
    def process(self, context: ProcessingContext) -> None:
        if not context.alert:
            raise ValueError("No alert available for LLM analysis")
        
        email_parser = self.container.get_optional("email_parser")
        
        if not email_parser:
            context.processing_status = "llm_not_available"
            context.llm_provider = "not_available"
            logger.warning("⚠️ Email LLM Parser not available - skipping LLM analysis")
            return
        
        logger.info("🧠 Processing email with LLM Parser")
        
        # Track processing time
        start_time = time.time()
        
        try:
            # Parse email content
            llm_parse_result = email_parser.parse_email(context.alert.content)
            
            # Calculate processing time
            context.processing_time_ms = (time.time() - start_time) * 1000
            
            # Determine which LLM provider was used
            context.llm_provider = self._determine_llm_provider(email_parser, llm_parse_result)
            
            # Update context
            context.llm_parse_result = llm_parse_result
            
            # Set processing status based on results
            if llm_parse_result.error:
                context.set_error(f"LLM parsing failed: {llm_parse_result.error}", "llm_error")
                logger.error(f"❌ LLM parsing failed: {llm_parse_result.error}")
            elif llm_parse_result.is_trading_alert:
                context.processing_status = "parsed_trading_alert"
                self._log_trading_alert_details(context)
            else:
                context.processing_status = "parsed_non_trading"
                logger.info("📧 Email classified as non-trading content")
                
            logger.info(f"⏱️  LLM processing completed in {context.processing_time_ms:.1f}ms using {context.llm_provider}")
            
        except Exception as e:
            context.processing_time_ms = (time.time() - start_time) * 1000
            context.llm_provider = "error"
            raise ValueError(f"LLM analysis failed: {str(e)}")
    
    def _determine_llm_provider(self, email_parser, llm_parse_result) -> str:
        """Determine which LLM provider was used for the analysis"""
        if llm_parse_result.raw_response:
            if hasattr(email_parser, 'anthropic_client') and email_parser.anthropic_client:
                return "Anthropic"
            elif hasattr(email_parser, 'openai_client') and email_parser.openai_client:
                return "OpenAI"
        return "unknown"
    
    def _log_trading_alert_details(self, context: ProcessingContext) -> None:
        """Log details of detected trading alert"""
        logger.info("✅ Trading alert detected!")
        
        if context.llm_parse_result and context.llm_parse_result.trades:
            trades = context.llm_parse_result.trades
            logger.info(f"📈 Found {len(trades)} trade(s):")
            
            for i, trade in enumerate(trades, 1):
                logger.info(f"  {i}. {trade.get('ticker', 'N/A')}: {trade.get('action', 'N/A')}")
                if trade.get('price'):
                    logger.info(f"     Price: ${trade['price']}")
                if trade.get('target_allocation'):
                    logger.info(f"     Target Allocation: {trade['target_allocation']}")


class LoggingHandler(Handler):
    """
    Log processing results to Google Sheets
    
    Replaces the dual logging logic from the monolithic function.
    This handler should always run, even if previous handlers failed.
    """
    
    def handle(self, context: ProcessingContext) -> ProcessingContext:
        """
        Override base handler to ensure logging never fails the pipeline
        
        The LoggingHandler is special - it should always complete successfully
        and log whatever information is available, even if previous handlers failed.
        """
        handler_name = self.__class__.__name__
        context.start_handler(handler_name)
        
        try:
            logger.info(f"🔄 Processing with {handler_name}")
            
            # Execute logging logic - always try to log regardless of previous errors
            self.process(context)
            
            # Mark handler as completed
            context.mark_handler_complete(handler_name)
            logger.info(f"✅ {handler_name} completed successfully")
            
        except Exception as e:
            # Log the error but don't fail the pipeline
            logger.error(f"❌ {handler_name} encountered error: {str(e)}")
            logger.info("📊 Continuing pipeline despite logging error")
            # Don't call context.set_error() - we want logging to be non-blocking
        
        # Always continue to next handler (there shouldn't be any after logging)
        return self.handle_next(context)
    
    def process(self, context: ProcessingContext) -> None:
        # Always try to log, even if earlier handlers failed
        try:
            # Log to main trade log
            self._log_to_sheets(context)
            
            # Log to LLM parsing log if LLM analysis was performed
            if context.llm_parse_result is not None or context.llm_provider != "none":
                self._log_to_llm_sheets(context)
            
            # Mark processing as completed only if no errors
            if not context.has_error():
                context.processing_status = "completed"
            
            logger.info("📊 Logging completed successfully")
            
        except Exception as e:
            # Log the logging error but don't fail the entire pipeline
            logger.error(f"📊 Logging failed: {e}")
            # Don't raise the exception - we want to complete processing
    
    def _log_to_sheets(self, context: ProcessingContext) -> None:
        """Log to main Google Sheets trade log"""
        sheets_logger = self.container.get_optional("sheets_logger")
        
        if not sheets_logger:
            logger.warning("⚠️ Google Sheets logger not available")
            return
        
        # Create enhanced alert with LLM metadata (handle case where alert is None)
        if context.alert:
            enhanced_alert = self._create_enhanced_alert(context)
        else:
            # Create a minimal alert for logging failures
            from datetime import datetime
            from ..core.models import Alert
            enhanced_alert = Alert(
                source="gmail",
                content="Failed to parse email content",
                timestamp=datetime.utcnow(),
                metadata={
                    'message_id': context.message_id,
                    'sender': context.sender,
                    'error': 'Alert parsing failed'
                }
            )
        
        sheets_logger.log_email_alert(
            alert=enhanced_alert,
            raw_data=context.raw_data,
            whitelist_status=context.whitelist_status,
            processing_status=context.processing_status,
            error_message=context.error_message
        )
        
        logger.info("📊 Logged to main Google Sheets")
    
    def _log_to_llm_sheets(self, context: ProcessingContext) -> None:
        """Log to LLM-specific Google Sheets log"""
        llm_logger = self.container.get_optional("llm_logger")
        
        if not llm_logger:
            logger.warning("⚠️ LLM logger not available")
            return
        
        # Use the alert if available, otherwise use None (LLM logger should handle this)
        alert_for_logging = context.alert if context.alert else None
        
        llm_logger.log_llm_parsing_result(
            alert=alert_for_logging,
            llm_parse_result=context.llm_parse_result,
            llm_provider=context.llm_provider,
            processing_time_ms=context.processing_time_ms,
            error_message=context.error_message
        )
        
        logger.info("📊 Logged to LLM parsing Google Sheets")
    
    def _create_enhanced_alert(self, context: ProcessingContext) -> Alert:
        """Create alert with enhanced metadata for logging"""
        enhanced_metadata = context.metadata.copy()
        
        # Add LLM parsing results to metadata
        if context.llm_parse_result:
            enhanced_metadata.update({
                'llm_is_trading_alert': context.llm_parse_result.is_trading_alert,
                'llm_trades_count': len(context.llm_parse_result.trades) if context.llm_parse_result.trades else 0,
                'llm_raw_response': context.llm_parse_result.raw_response[:500] if context.llm_parse_result.raw_response else None  # Truncate
            })
            
            if context.llm_parse_result.trades:
                enhanced_metadata['llm_tickers'] = [trade.get('ticker') for trade in context.llm_parse_result.trades]
                enhanced_metadata['llm_actions'] = [trade.get('action') for trade in context.llm_parse_result.trades]
        
        # Create enhanced alert
        return Alert(
            source=context.alert.source,
            content=context.alert.content,
            timestamp=context.alert.timestamp,
            metadata=enhanced_metadata
        )