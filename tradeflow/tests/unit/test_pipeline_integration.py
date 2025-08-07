"""
Integration tests for the processing pipeline

Demonstrates how the new architecture enables clean integration testing
compared to the monolithic approach.
"""

import pytest
from unittest.mock import Mock, patch
from datetime import datetime

from tradeflow.pipeline import ProcessingPipeline, ProcessingContext
from tradeflow.services import ServiceContainer, ServiceConfig
from tradeflow.core.models import Alert
from tradeflow.parsers.email_llm import ParseResult


class TestProcessingPipelineIntegration:
    """Test complete pipeline processing"""
    
    @pytest.fixture
    def mock_container(self):
        """Create mock service container for testing"""
        config = ServiceConfig(debug=True, environment="test")
        container = ServiceContainer(config)
        
        # Mock Gmail provider
        mock_gmail_provider = Mock()
        mock_alert = Alert(
            source="gmail",
            content="Buy AAPL at $150",
            timestamp=datetime.utcnow(),
            metadata={
                "message_id": "test-123",
                "sender": "trader@example.com",
                "subject": "Trade Alert"
            }
        )
        mock_gmail_provider.parse_alert.return_value = mock_alert
        mock_gmail_provider.validate_sender.return_value = True
        mock_gmail_provider._is_domain_whitelisted.return_value = True
        
        # Mock email parser
        mock_email_parser = Mock()
        mock_parse_result = ParseResult(
            is_trading_alert=True,
            trades=[{"ticker": "AAPL", "action": "buy", "price": "150.00"}],
            raw_response="Trade detected"
        )
        mock_email_parser.parse_email.return_value = mock_parse_result
        mock_email_parser.anthropic_client = Mock()  # Has Anthropic
        
        # Mock loggers
        mock_sheets_logger = Mock()
        mock_llm_logger = Mock()
        
        # Configure container
        container.config.gmail_sender_whitelist = ["trader@example.com"]
        container.config.gmail_domain_whitelist = []
        
        container.register_singleton("gmail_provider", mock_gmail_provider)
        container.register_singleton("email_parser", mock_email_parser)
        container.register_singleton("sheets_logger", mock_sheets_logger)
        container.register_singleton("llm_logger", mock_llm_logger)
        
        return container
    
    @pytest.mark.asyncio
    async def test_successful_pipeline_processing(self, mock_container):
        """Test complete successful pipeline processing"""
        pipeline = ProcessingPipeline(mock_container)
        
        raw_data = {
            "message": {
                "messageId": "test-123",
                "publishTime": "2024-01-01T00:00:00Z",
                "data": "base64-encoded-data"
            }
        }
        
        # Process through pipeline
        context = await pipeline.process(raw_data)
        
        # Verify successful completion
        assert context.is_successful()
        assert context.processing_status == "completed"
        assert context.message_id == "test-123"
        assert context.sender == "trader@example.com"
        assert context.whitelist_status == "allowed"
        assert context.llm_provider == "Anthropic"
        assert context.llm_parse_result.is_trading_alert is True
        
        # Verify all handlers completed
        expected_handlers = [
            "ParseAlertHandler",
            "ValidateWhitelistHandler", 
            "LLMAnalysisHandler",
            "LoggingHandler"
        ]
        assert all(handler in context.completed_handlers for handler in expected_handlers)
        
        # Verify services were called
        gmail_provider = mock_container.get("gmail_provider")
        email_parser = mock_container.get("email_parser")
        sheets_logger = mock_container.get("sheets_logger")
        llm_logger = mock_container.get("llm_logger")
        
        gmail_provider.parse_alert.assert_called_once_with(raw_data)
        gmail_provider.validate_sender.assert_called_once_with("trader@example.com")
        email_parser.parse_email.assert_called_once_with("Buy AAPL at $150")
        sheets_logger.log_email_alert.assert_called_once()
        llm_logger.log_llm_parsing_result.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_pipeline_with_whitelist_blocked(self, mock_container):
        """Test pipeline when sender is blocked by whitelist"""
        # Configure whitelist to block sender
        mock_container.config.gmail_sender_whitelist = ["allowed@example.com"]
        gmail_provider = mock_container.get("gmail_provider")
        gmail_provider.validate_sender.return_value = False
        gmail_provider._is_domain_whitelisted.return_value = False
        
        pipeline = ProcessingPipeline(mock_container)
        
        raw_data = {
            "message": {
                "messageId": "blocked-123",
                "data": "test-data"
            }
        }
        
        context = await pipeline.process(raw_data)
        
        # Should complete but with blocked status
        assert context.processing_status == "blocked"
        assert context.whitelist_status == "blocked"
        assert context.error_message is not None
        assert "not in whitelist" in context.error_message
        
        # Should have completed parse and validate handlers
        assert "ParseAlertHandler" in context.completed_handlers
        assert "ValidateWhitelistHandler" in context.completed_handlers
        # But LLM analysis should be skipped due to blocked status
        assert "LLMAnalysisHandler" not in context.completed_handlers
    
    @pytest.mark.asyncio
    async def test_pipeline_with_llm_failure(self, mock_container):
        """Test pipeline when LLM analysis fails"""
        # Configure LLM parser to fail
        email_parser = mock_container.get("email_parser")
        email_parser.parse_email.side_effect = Exception("LLM service down")
        
        pipeline = ProcessingPipeline(mock_container)
        
        raw_data = {
            "message": {
                "messageId": "llm-fail-123",
                "data": "test-data"
            }
        }
        
        context = await pipeline.process(raw_data)
        
        # Should complete with error status
        assert context.processing_status == "error"
        assert context.error_message is not None
        assert "LLM analysis failed" in context.error_message
        
        # Should have completed early handlers
        assert "ParseAlertHandler" in context.completed_handlers
        assert "ValidateWhitelistHandler" in context.completed_handlers
        # LLM handler should have started but failed
        assert "LLMAnalysisHandler" not in context.completed_handlers
    
    @pytest.mark.asyncio
    async def test_pipeline_with_non_trading_email(self, mock_container):
        """Test pipeline with non-trading email"""
        # Configure LLM to classify as non-trading
        email_parser = mock_container.get("email_parser")
        non_trading_result = ParseResult(
            is_trading_alert=False,
            trades=None,
            raw_response="Regular email content"
        )
        email_parser.parse_email.return_value = non_trading_result
        
        pipeline = ProcessingPipeline(mock_container)
        
        raw_data = {
            "message": {
                "messageId": "non-trading-123",
                "data": "test-data"
            }
        }
        
        context = await pipeline.process(raw_data)
        
        # Should complete successfully but as non-trading
        assert context.is_successful()
        assert context.processing_status == "completed"
        assert context.llm_parse_result.is_trading_alert is False
        
        # All handlers should complete
        expected_handlers = [
            "ParseAlertHandler",
            "ValidateWhitelistHandler",
            "LLMAnalysisHandler", 
            "LoggingHandler"
        ]
        assert all(handler in context.completed_handlers for handler in expected_handlers)
    
    @pytest.mark.asyncio
    async def test_pipeline_with_missing_services(self, mock_container):
        """Test pipeline resilience when optional services are missing"""
        # Remove optional services
        mock_container.register_singleton("email_parser", None)
        mock_container.register_singleton("sheets_logger", None)
        mock_container.register_singleton("llm_logger", None)
        
        pipeline = ProcessingPipeline(mock_container)
        
        raw_data = {
            "message": {
                "messageId": "minimal-123",
                "data": "test-data"
            }
        }
        
        context = await pipeline.process(raw_data)
        
        # Should still complete basic processing
        assert context.processing_status == "completed"
        assert context.message_id == "test-123"
        assert context.whitelist_status == "allowed"
        
        # LLM analysis should be skipped
        assert context.llm_provider == "not_available"
        assert context.llm_parse_result is None
        
        # Core handlers should still run
        assert "ParseAlertHandler" in context.completed_handlers
        assert "ValidateWhitelistHandler" in context.completed_handlers
        assert "LLMAnalysisHandler" in context.completed_handlers  # Runs but does nothing
        assert "LoggingHandler" in context.completed_handlers  # Runs but logs warnings


class TestProcessingContext:
    """Test ProcessingContext functionality"""
    
    def test_context_initialization(self):
        """Test context is initialized correctly"""
        raw_data = {"test": "data"}
        context = ProcessingContext(raw_data=raw_data)
        
        assert context.raw_data == raw_data
        assert context.processing_status == "received"
        assert context.whitelist_status == "pending_validation"
        assert context.completed_handlers == []
        assert context.current_handler is None
        assert context.error_message is None
    
    def test_handler_tracking(self):
        """Test handler execution tracking"""
        context = ProcessingContext(raw_data={})
        
        # Start handler
        context.start_handler("TestHandler")
        assert context.current_handler == "TestHandler"
        
        # Complete handler
        context.mark_handler_complete("TestHandler")
        assert "TestHandler" in context.completed_handlers
        assert context.current_handler is None
        
        # Don't duplicate completed handlers
        context.mark_handler_complete("TestHandler")
        assert context.completed_handlers.count("TestHandler") == 1
    
    def test_error_handling(self):
        """Test error state management"""
        context = ProcessingContext(raw_data={})
        
        assert not context.has_error()
        assert context.should_continue_processing()
        
        # Set error
        context.set_error("Something went wrong", "error")
        
        assert context.has_error()
        assert context.error_message == "Something went wrong"
        assert context.processing_status == "error"
        assert not context.should_continue_processing()
    
    def test_success_status_detection(self):
        """Test success status detection"""
        context = ProcessingContext(raw_data={})
        
        # Initially not successful
        assert not context.is_successful()
        
        # Set success statuses
        for status in ["completed", "parsed_trading_alert", "parsed_non_trading"]:
            context.processing_status = status
            assert context.is_successful()
        
        # Set non-success status
        context.processing_status = "error"
        assert not context.is_successful()
    
    def test_get_summary(self):
        """Test context summary generation"""
        context = ProcessingContext(raw_data={"test": "data"})
        context.message_id = "test-123"
        context.sender = "test@example.com"
        context.processing_status = "completed"
        context.whitelist_status = "allowed"
        context.llm_provider = "Anthropic"
        context.processing_time_ms = 1500.0
        context.completed_handlers = ["Handler1", "Handler2"]
        
        summary = context.get_summary()
        
        assert summary["message_id"] == "test-123"
        assert summary["sender"] == "test@example.com"
        assert summary["processing_status"] == "completed"
        assert summary["whitelist_status"] == "allowed"
        assert summary["llm_provider"] == "Anthropic"
        assert summary["processing_time_ms"] == 1500.0
        assert summary["completed_handlers"] == ["Handler1", "Handler2"]
        assert "timestamp" in summary