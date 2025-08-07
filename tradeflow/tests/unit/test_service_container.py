"""
Unit tests for service layer architecture

Demonstrates the improved testability compared to the monolithic approach
"""

import pytest
from unittest.mock import Mock, patch
from tradeflow.services import ServiceContainer, ServiceConfig


class TestServiceContainer:
    """Test service container functionality"""
    
    def test_service_container_initialization(self):
        """Test basic service container setup"""
        config = ServiceConfig(debug=True, environment="test")
        container = ServiceContainer(config)
        
        assert container.config.debug is True
        assert container.config.environment == "test"
    
    def test_register_and_get_factory(self):
        """Test service factory registration and retrieval"""
        config = ServiceConfig()
        container = ServiceContainer(config)
        
        # Mock service factory
        mock_service = Mock()
        mock_factory = Mock(return_value=mock_service)
        
        # Register factory
        container.register_factory("test_service", mock_factory)
        
        # Get service
        service = container.get("test_service")
        
        assert service is mock_service
        mock_factory.assert_called_once_with(config)
    
    def test_singleton_behavior(self):
        """Test that services are created once and reused"""
        config = ServiceConfig()
        container = ServiceContainer(config)
        
        mock_factory = Mock(return_value=Mock())
        container.register_factory("test_service", mock_factory)
        
        # Get service twice
        service1 = container.get("test_service")
        service2 = container.get("test_service")
        
        # Should be same instance
        assert service1 is service2
        # Factory should be called only once
        mock_factory.assert_called_once()
    
    def test_service_not_found(self):
        """Test error handling for unregistered services"""
        config = ServiceConfig()
        container = ServiceContainer(config)
        
        with pytest.raises(KeyError):
            container.get("nonexistent_service")
    
    def test_optional_service_returns_none(self):
        """Test optional service retrieval"""
        config = ServiceConfig()
        container = ServiceContainer(config)
        
        service = container.get_optional("nonexistent_service")
        assert service is None
    
    def test_health_check(self):
        """Test service health checking"""
        config = ServiceConfig()
        container = ServiceContainer(config)
        
        # Register healthy service
        healthy_service = Mock()
        healthy_service.is_healthy = Mock(return_value=True)
        container.register_singleton("healthy_service", healthy_service)
        
        # Register unhealthy service  
        unhealthy_service = Mock()
        unhealthy_service.is_healthy = Mock(return_value=False)
        container.register_singleton("unhealthy_service", unhealthy_service)
        
        health_status = container.health_check()
        
        assert health_status["healthy_service"] is True
        assert health_status["unhealthy_service"] is False


class TestServiceConfig:
    """Test service configuration"""
    
    def test_default_config_from_environment(self):
        """Test configuration loading from environment"""
        with patch.multiple(
            'tradeflow.services.config',
            DEBUG=True,
            ENVIRONMENT="production",
            OPENAI_API_KEY="test-key"
        ):
            config = ServiceConfig()
            
            assert config.debug is True
            assert config.environment == "production"
            assert config.openai_api_key == "test-key"
    
    def test_config_validation_success(self):
        """Test successful configuration validation"""
        config = ServiceConfig(
            openai_api_key="test-key",
            google_credentials_file="test.json",
            google_sheets_doc_id="test-doc-id"
        )
        
        is_valid, error = config.validate()
        assert is_valid is True
        assert error is None
    
    def test_config_validation_failure(self):
        """Test configuration validation failure"""
        config = ServiceConfig()  # No API keys or credentials
        
        is_valid, error = config.validate()
        assert is_valid is False
        assert "LLM API key" in error
        assert "Google Sheets" in error
    
    def test_config_to_dict_redacts_secrets(self):
        """Test that sensitive information is redacted"""
        config = ServiceConfig(
            openai_api_key="secret-key",
            anthropic_api_key="another-secret",
            debug=True
        )
        
        config_dict = config.to_dict()
        
        assert config_dict["openai_api_key"] == "***REDACTED***"
        assert config_dict["anthropic_api_key"] == "***REDACTED***"
        assert config_dict["debug"] is True  # Non-secret values preserved


@pytest.fixture
def mock_container():
    """Fixture providing a mocked service container for testing"""
    config = ServiceConfig(debug=True, environment="test")
    container = ServiceContainer(config)
    
    # Register mock services
    container.register_singleton("gmail_provider", Mock())
    container.register_singleton("sheets_logger", Mock())
    container.register_singleton("llm_logger", Mock())
    container.register_singleton("email_parser", Mock())
    
    return container