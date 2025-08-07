"""
Unit tests for pipeline handlers

Demonstrates how the new architecture enables easy testing of individual
components, unlike the monolithic approach.
"""

import pytest
from unittest.mock import Mock, patch
from datetime import datetime

from tradeflow.pipeline.context import ProcessingContext
from tradeflow.pipeline.handlers import (
    ParseAlertHandler,
    ValidateWhitelistHandler,
    LLMAnalysisHandler,
    LoggingHandler
)
from tradeflow.core.models import Alert
from tradeflow.parsers.email_llm import ParseResult


class TestParseAlertHandler:
    """Test ParseAlertHandler in isolation"""
    
    def test_successful_parsing(self):
        """Test successful alert parsing"""
        # Setup mock container
        container = Mock()
        mock_gmail_provider = Mock()
        container.get.return_value = mock_gmail_provider
        
        # Mock parsed alert
        mock_alert = Alert(
            source="gmail",
            content="Test email content",
            timestamp=datetime.utcnow(),
            metadata={
                "message_id": "test-123",
                "sender": "test@example.com",
                "subject": "Test Alert"
            }
        )
        mock_gmail_provider.parse_alert.return_value = mock_alert
        
        # Create handler and context
        handler = ParseAlertHandler(container)
        context = ProcessingContext(raw_data={"test": "data"})
        
        # Execute handler
        handler.process(context)
        
        # Verify results
        assert context.alert is mock_alert
        assert context.message_id == "test-123"
        assert context.sender == "test@example.com"
        assert context.processing_status == "parsed"
        
        # Verify service was called correctly
        container.get.assert_called_once_with("gmail_provider")
        mock_gmail_provider.parse_alert.assert_called_once_with({"test": "data"})
    
    def test_parsing_failure(self):
        """Test alert parsing failure"""
        container = Mock()
        mock_gmail_provider = Mock()
        mock_gmail_provider.parse_alert.side_effect = Exception("Parse failed")
        container.get.return_value = mock_gmail_provider
        
        handler = ParseAlertHandler(container)
        context = ProcessingContext(raw_data={"test": "data"})
        
        # Should raise exception (handled by base Handler class)
        with pytest.raises(Exception):
            handler.process(context)
    
    def test_gmail_provider_not_available(self):
        """Test when Gmail provider is not available"""
        container = Mock()
        container.get.return_value = None
        
        handler = ParseAlertHandler(container)
        context = ProcessingContext(raw_data={"test": "data"})
        
        with pytest.raises(ValueError, match="Gmail provider not available"):
            handler.process(context)


class TestValidateWhitelistHandler:
    """Test ValidateWhitelistHandler in isolation"""
    
    def test_no_whitelist_configured(self):
        """Test when no whitelist is configured"""
        container = Mock()
        container.config.gmail_sender_whitelist = []
        container.config.gmail_domain_whitelist = []
        
        handler = ValidateWhitelistHandler(container)
        context = self._create_test_context()
        
        handler.process(context)
        
        assert context.whitelist_status == "no_whitelist"
    
    def test_sender_whitelist_allowed(self):
        """Test sender passes whitelist validation"""
        container = Mock()
        container.config.gmail_sender_whitelist = ["test@example.com"]
        container.config.gmail_domain_whitelist = []
        
        mock_gmail_provider = Mock()
        mock_gmail_provider.validate_sender.return_value = True
        container.get.return_value = mock_gmail_provider
        
        handler = ValidateWhitelistHandler(container)
        context = self._create_test_context()
        
        handler.process(context)
        
        assert context.whitelist_status == "allowed"
        mock_gmail_provider.validate_sender.assert_called_once_with("test@example.com")
    
    def test_sender_whitelist_blocked(self):
        """Test sender blocked by whitelist"""
        container = Mock()
        container.config.gmail_sender_whitelist = ["allowed@example.com"]
        container.config.gmail_domain_whitelist = []
        
        mock_gmail_provider = Mock()
        mock_gmail_provider.validate_sender.return_value = False
        mock_gmail_provider._is_domain_whitelisted.return_value = False
        container.get.return_value = mock_gmail_provider
        
        handler = ValidateWhitelistHandler(container)
        context = self._create_test_context()
        
        handler.process(context)
        
        assert context.whitelist_status == "blocked"
        assert context.error_message is not None
        assert "not in whitelist" in context.error_message
    
    def test_domain_whitelist_allowed(self):
        """Test domain whitelist allows sender"""
        container = Mock()
        container.config.gmail_sender_whitelist = []
        container.config.gmail_domain_whitelist = ["example.com"]
        
        mock_gmail_provider = Mock()
        mock_gmail_provider._is_domain_whitelisted.return_value = True
        container.get.return_value = mock_gmail_provider
        
        handler = ValidateWhitelistHandler(container)
        context = self._create_test_context()
        
        handler.process(context)
        
        assert context.whitelist_status == "allowed"
        mock_gmail_provider._is_domain_whitelisted.assert_called_once_with("test@example.com")
    
    def _create_test_context(self):
        """Helper to create test context with alert"""
        alert = Alert(
            source="gmail",
            content="Test content",
            timestamp=datetime.utcnow(),
            metadata={"sender": "test@example.com", "message_id": "test-123"}
        )
        context = ProcessingContext(raw_data={"test": "data"})
        context.alert = alert
        context.sender = "test@example.com"
        return context


class TestLLMAnalysisHandler:
    """Test LLMAnalysisHandler in isolation"""
    
    def test_successful_llm_analysis(self):
        """Test successful LLM analysis"""
        container = Mock()
        mock_email_parser = Mock()
        container.get_optional.return_value = mock_email_parser
        
        # Mock LLM result
        mock_parse_result = ParseResult(
            is_trading_alert=True,
            trades=[{"ticker": "AAPL", "action": "buy", "price": "150.00"}],
            raw_response="LLM response"
        )
        mock_email_parser.parse_email.return_value = mock_parse_result
        mock_email_parser.anthropic_client = Mock()  # Has Anthropic client
        
        handler = LLMAnalysisHandler(container)
        context = self._create_test_context_with_alert()
        
        handler.process(context)
        
        assert context.llm_parse_result is mock_parse_result
        assert context.processing_status == "parsed_trading_alert"
        assert context.llm_provider == "Anthropic"
        assert context.processing_time_ms > 0
        
        mock_email_parser.parse_email.assert_called_once_with("Test email content")
    
    def test_llm_parser_not_available(self):
        """Test when LLM parser is not available"""
        container = Mock()
        container.get_optional.return_value = None
        
        handler = LLMAnalysisHandler(container)
        context = self._create_test_context_with_alert()
        
        handler.process(context)
        
        assert context.processing_status == "llm_not_available"
        assert context.llm_provider == "not_available"
    
    def test_llm_analysis_failure(self):
        """Test LLM analysis failure"""
        container = Mock()
        mock_email_parser = Mock()
        mock_email_parser.parse_email.side_effect = Exception("LLM failed")
        container.get_optional.return_value = mock_email_parser
        
        handler = LLMAnalysisHandler(container)
        context = self._create_test_context_with_alert()
        
        with pytest.raises(ValueError, match="LLM analysis failed"):
            handler.process(context)
    
    def test_non_trading_alert(self):
        """Test non-trading email classification"""
        container = Mock()
        mock_email_parser = Mock()
        container.get_optional.return_value = mock_email_parser
        
        mock_parse_result = ParseResult(
            is_trading_alert=False,
            trades=None,
            raw_response="Not a trading alert"
        )
        mock_email_parser.parse_email.return_value = mock_parse_result
        
        handler = LLMAnalysisHandler(container)
        context = self._create_test_context_with_alert()
        
        handler.process(context)
        
        assert context.processing_status == "parsed_non_trading"
        assert context.llm_parse_result.is_trading_alert is False
    
    def _create_test_context_with_alert(self):
        """Helper to create context with alert for LLM testing"""
        alert = Alert(
            source="gmail",
            content="Test email content",
            timestamp=datetime.utcnow(),
            metadata={"sender": "test@example.com", "message_id": "test-123"}
        )
        context = ProcessingContext(raw_data={"test": "data"})
        context.alert = alert
        return context


class TestLoggingHandler:
    """Test LoggingHandler in isolation"""
    
    def test_successful_logging(self):
        """Test successful logging to both sheets"""
        container = Mock()
        mock_sheets_logger = Mock()
        mock_llm_logger = Mock()
        
        container.get_optional.side_effect = lambda name: {
            "sheets_logger": mock_sheets_logger,
            "llm_logger": mock_llm_logger
        }.get(name)
        
        handler = LoggingHandler(container)
        context = self._create_test_context_with_llm_result()
        
        handler.process(context)
        
        assert context.processing_status == "completed"
        
        # Verify both loggers were called
        mock_sheets_logger.log_email_alert.assert_called_once()
        mock_llm_logger.log_llm_parsing_result.assert_called_once()
    
    def test_logging_with_no_loggers(self):
        """Test logging when loggers are not available"""
        container = Mock()
        container.get_optional.return_value = None
        
        handler = LoggingHandler(container)
        context = self._create_test_context_with_llm_result()
        
        # Should not raise exception, just warn
        handler.process(context)
        
        assert context.processing_status == "completed"
    
    def _create_test_context_with_llm_result(self):
        """Helper to create context with LLM results"""
        alert = Alert(
            source="gmail",
            content="Test content",
            timestamp=datetime.utcnow(),
            metadata={"sender": "test@example.com", "message_id": "test-123"}
        )
        
        context = ProcessingContext(raw_data={"test": "data"})
        context.alert = alert
        context.sender = "test@example.com"
        context.llm_parse_result = ParseResult(
            is_trading_alert=True,
            trades=[{"ticker": "AAPL", "action": "buy"}],
            raw_response="LLM response"
        )
        context.llm_provider = "Anthropic"
        context.processing_time_ms = 1500.0
        
        return context