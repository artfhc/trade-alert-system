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
        
        logger.info(f"🔄 [{handler_name}] Starting processing")
        logger.info(f"🔍 [{handler_name}] Context state - Status: {context.processing_status}, Error: {context.error_message is not None}")
        logger.info(f"🔍 [{handler_name}] Should continue: {context.should_continue_processing()}")
        
        try:
            # Skip processing if context has errors or should not continue
            if not context.should_continue_processing():
                logger.info(f"⏭️  [{handler_name}] Skipping - processing stopped (status: {context.processing_status})")
                return self.handle_next(context)
            
            logger.info(f"▶️  [{handler_name}] Executing handler-specific logic")
            
            # Execute handler-specific logic
            self.process(context)
            
            # Mark handler as completed
            context.mark_handler_complete(handler_name)
            logger.info(f"✅ [{handler_name}] completed successfully")
            
        except Exception as e:
            error_message = f"{handler_name} failed: {str(e)}"
            context.set_error(error_message, "error")
            logger.error(f"❌ [{handler_name}] {error_message}")
            import traceback
            logger.error(f"❌ [{handler_name}] Stack trace: {traceback.format_exc()}")
        
        logger.info(f"➡️  [{handler_name}] Passing to next handler")
        # Continue to next handler
        return self.handle_next(context)
    
    @abstractmethod
    def process(self, context: ProcessingContext) -> None:
        """Handler-specific processing logic"""
        pass
    
    def handle_next(self, context: ProcessingContext) -> ProcessingContext:
        """Pass context to next handler if available"""
        current_handler = self.__class__.__name__
        if self._next_handler:
            next_handler = self._next_handler.__class__.__name__
            logger.info(f"🔗 [{current_handler}] Passing control to {next_handler}")
            return self._next_handler.handle(context)
        else:
            logger.info(f"🏁 [{current_handler}] End of pipeline - no next handler")
            return context


class ParseAlertHandler(Handler):
    """
    Parse raw Pub/Sub data into Alert object
    
    Replaces the alert parsing section from the monolithic function
    """
    
    def process(self, context: ProcessingContext) -> None:
        logger.info("🔍 [ParseAlertHandler] Checking for Gmail provider")
        gmail_provider = self.container.get_optional("gmail_provider")
        
        if not gmail_provider:
            # Gmail provider not available - try to extract basic info from Pub/Sub message
            logger.warning("⚠️ [ParseAlertHandler] Gmail provider not available - attempting basic Pub/Sub parsing")
            logger.info(f"🔍 [ParseAlertHandler] Raw data type: {type(context.raw_data)}")
            logger.info(f"🔍 [ParseAlertHandler] Raw data keys: {list(context.raw_data.keys()) if isinstance(context.raw_data, dict) else 'Not a dict'}")
            
            alert = self._parse_pubsub_message_basic(context.raw_data)
            logger.info("✅ [ParseAlertHandler] Basic Pub/Sub parsing completed")
        else:
            # Use Gmail provider for full parsing
            logger.info("📧 [ParseAlertHandler] Using Gmail provider for full parsing")
            alert = gmail_provider.parse_alert(context.raw_data)
            logger.info("✅ [ParseAlertHandler] Gmail provider parsing completed")
        
        logger.info(f"🔍 [ParseAlertHandler] Alert created - Source: {alert.source}, Content length: {len(alert.content)}")
        
        # Update context
        context.alert = alert
        context.message_id = alert.metadata.get('message_id', 'unknown')
        context.sender = alert.metadata.get('sender', 'unknown')
        context.metadata = alert.metadata
        context.processing_status = "parsed"
        
        logger.info(f"📧 [ParseAlertHandler] Alert parsed from {context.sender}")
        logger.info(f"📧 [ParseAlertHandler] Message ID: {context.message_id}")
        logger.info(f"📝 [ParseAlertHandler] Content preview: {alert.content[:100]}...")
        logger.info(f"🔍 [ParseAlertHandler] Context updated - Status: {context.processing_status}")
    
    def _parse_pubsub_message_basic(self, raw_data: dict) -> 'Alert':
        """
        Basic parsing of Pub/Sub message when Gmail provider is not available
        
        This creates a minimal Alert object from the Pub/Sub message data,
        allowing the pipeline to continue processing even without Gmail API access.
        This method should never fail - it will create an alert with whatever data is available.
        """
        from datetime import datetime
        from ..core.models import Alert
        import base64
        import binascii
        import json
        
        # Safely extract message data with defaults
        try:
            message = raw_data.get('message', {})
        except (AttributeError, TypeError):
            # raw_data is not a dict or is None
            message = {}
        
        message_id = message.get('messageId', f'pubsub_{int(datetime.utcnow().timestamp())}')
        publish_time = message.get('publishTime', datetime.utcnow().isoformat())
        
        # Try to decode the base64 data - with multiple fallback strategies
        email_content = "No email content available"
        parsing_notes = []
        
        try:
            if 'data' in message and message['data']:
                # Try to decode base64
                try:
                    decoded_data = base64.b64decode(message['data']).decode('utf-8')
                    parsing_notes.append("Successfully decoded base64 data")
                    
                    # Try parsing as JSON first (Gmail API format)
                    try:
                        email_data = json.loads(decoded_data)
                        email_content = email_data.get('snippet', email_data.get('body', email_data.get('content', decoded_data)))
                        parsing_notes.append("Parsed as JSON format")
                    except json.JSONDecodeError:
                        # Treat as raw email content
                        email_content = decoded_data
                        parsing_notes.append("Treated as raw email content")
                        
                except (binascii.Error, UnicodeDecodeError, TypeError) as e:
                    parsing_notes.append(f"Base64 decode failed: {e}")
                    # Try to use data as-is if it's a string
                    if isinstance(message.get('data'), str):
                        email_content = message['data']
                        parsing_notes.append("Using raw data as fallback")
                        
            elif 'attributes' in message:
                # Sometimes the content is in attributes
                attributes = message.get('attributes', {})
                email_content = attributes.get('content', attributes.get('body', str(attributes)))
                parsing_notes.append("Extracted from message attributes")
                
            else:
                # Last resort - use the entire message as content
                email_content = f"Raw Pub/Sub message: {json.dumps(raw_data, indent=2)}"
                parsing_notes.append("Using entire message as fallback content")
                
        except Exception as e:
            parsing_notes.append(f"All parsing attempts failed: {e}")
            email_content = f"Parsing error - Raw data: {str(raw_data)[:200]}..."
        
        # Ensure we have some content to work with
        if not email_content or email_content.strip() == "":
            email_content = f"Empty content - Message ID: {message_id}"
        
        # Create basic alert with available information - this should never fail
        try:
            alert = Alert(
                source="gmail_pubsub_basic",
                content=email_content,
                timestamp=datetime.utcnow(),
                metadata={
                    'message_id': message_id,
                    'publish_time': publish_time,
                    'sender': 'unknown',
                    'subject': 'Parsed via Basic Pub/Sub',
                    'parsing_method': 'basic_pubsub',
                    'parsing_notes': parsing_notes,
                    'raw_data_type': str(type(raw_data)),
                    'note': 'Parsed without Gmail API access - limited metadata available'
                }
            )
            
            logger.info(f"📧 Created basic alert from Pub/Sub message: {message_id}")
            logger.info(f"📝 Content length: {len(email_content)} chars")
            logger.info(f"🔍 Parsing notes: {'; '.join(parsing_notes)}")
            return alert
            
        except Exception as e:
            # Last resort - create minimal alert that should always work
            logger.error(f"Failed to create Alert object: {e}")
            
            minimal_alert = Alert(
                source="gmail_pubsub_minimal",
                content=f"Alert creation failed: {str(e)}",
                timestamp=datetime.utcnow(),
                metadata={
                    'message_id': 'error',
                    'error': str(e),
                    'raw_data_summary': str(raw_data)[:100]
                }
            )
            
            logger.warning("📧 Created minimal emergency alert")
            return minimal_alert


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
        logger.info("🔍 [LLMAnalysisHandler] Starting LLM analysis")
        
        if not context.alert:
            logger.error("❌ [LLMAnalysisHandler] No alert available for LLM analysis")
            raise ValueError("No alert available for LLM analysis")
        
        logger.info(f"✅ [LLMAnalysisHandler] Alert available - Content length: {len(context.alert.content)}")
        logger.info(f"🔍 [LLMAnalysisHandler] Checking for email parser")
        
        email_parser = self.container.get_optional("email_parser")
        
        if not email_parser:
            context.processing_status = "llm_not_available"
            context.llm_provider = "not_available"
            logger.warning("⚠️ [LLMAnalysisHandler] Email LLM Parser not available - skipping LLM analysis")
            logger.info("📊 [LLMAnalysisHandler] Analysis skipped due to missing parser")
            return
        
        logger.info("🧠 [LLMAnalysisHandler] Email parser available - processing email with LLM Parser")
        logger.info(f"📝 [LLMAnalysisHandler] Email content to analyze: {context.alert.content[:200]}...")
        
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
                # Don't set error state for LLM failures - still want to log the attempt
                context.processing_status = "llm_error"
                # Store error message but don't use set_error() which blocks further processing
                if not context.error_message:  # Don't overwrite previous errors
                    context.error_message = f"LLM parsing failed: {llm_parse_result.error}"
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
        
        logger.info(f"🔄 [LoggingHandler] Starting logging (ALWAYS RUNS)")
        logger.info(f"🔍 [LoggingHandler] Context state - Status: {context.processing_status}, Error: {context.error_message is not None}")
        logger.info(f"🔍 [LoggingHandler] Alert available: {context.alert is not None}")
        logger.info(f"🔍 [LoggingHandler] LLM result available: {context.llm_parse_result is not None}")
        
        try:
            logger.info(f"▶️  [LoggingHandler] Executing logging logic")
            
            # Execute logging logic - always try to log regardless of previous errors
            self.process(context)
            
            # Mark handler as completed
            context.mark_handler_complete(handler_name)
            logger.info(f"✅ [LoggingHandler] completed successfully")
            
        except Exception as e:
            # Log the error but don't fail the pipeline
            logger.error(f"❌ [LoggingHandler] encountered error: {str(e)}")
            import traceback
            logger.error(f"❌ [LoggingHandler] Stack trace: {traceback.format_exc()}")
            logger.info("📊 [LoggingHandler] Continuing pipeline despite logging error")
            # Don't call context.set_error() - we want logging to be non-blocking
        
        logger.info(f"➡️  [LoggingHandler] Completed (no next handler)")
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