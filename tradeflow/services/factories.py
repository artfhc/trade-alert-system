"""
Service factory functions for dependency injection

These factories create service instances based on configuration,
replacing the global service initialization from the monolithic approach.
"""

import logging
from typing import Optional

from .container import ServiceContainer
from .config import ServiceConfig
from ..providers.gmail_pubsub import GmailPubSubProvider
from ..logging.google_sheets import GoogleSheetsLogger, LLMParsingLogger
from ..parsers.email_llm import EmailLLMParser

logger = logging.getLogger(__name__)


def create_gmail_provider(config: ServiceConfig) -> Optional[GmailPubSubProvider]:
    """Create Gmail Pub/Sub provider instance"""
    try:
        provider = GmailPubSubProvider(
            credentials_file=config.gmail_credentials_file,
            token_file=config.gmail_token_file,
            sender_whitelist=config.gmail_sender_whitelist,
            domain_whitelist=config.gmail_domain_whitelist
        )
        logger.info("Gmail provider created successfully")
        return provider
    except Exception as e:
        logger.error(f"Failed to create Gmail provider: {e}")
        raise


def create_sheets_logger(config: ServiceConfig) -> Optional[GoogleSheetsLogger]:
    """Create Google Sheets logger instance"""
    if not config.google_credentials_file or not config.google_sheets_doc_id:
        logger.warning("Google Sheets configuration incomplete - skipping sheets logger")
        return None
        
    try:
        sheets_logger = GoogleSheetsLogger(
            credentials_file=config.google_credentials_file,
            spreadsheet_id=config.google_sheets_doc_id,
            worksheet_name=config.google_sheets_worksheet
        )
        logger.info("Google Sheets logger created successfully")
        return sheets_logger
    except Exception as e:
        logger.error(f"Failed to create Google Sheets logger: {e}")
        raise


def create_llm_logger(config: ServiceConfig) -> Optional[LLMParsingLogger]:
    """Create LLM parsing logger instance"""
    if not config.google_credentials_file or not config.google_sheets_doc_id:
        logger.warning("Google Sheets configuration incomplete - skipping LLM logger")
        return None
        
    try:
        llm_logger = LLMParsingLogger(
            credentials_file=config.google_credentials_file,
            spreadsheet_id=config.google_sheets_doc_id,
            worksheet_name=config.google_sheets_llm_worksheet
        )
        logger.info("LLM parsing logger created successfully")
        return llm_logger
    except Exception as e:
        logger.error(f"Failed to create LLM parsing logger: {e}")
        raise


def create_email_parser(config: ServiceConfig) -> Optional[EmailLLMParser]:
    """Create Email LLM parser instance"""
    if not config.openai_api_key and not config.anthropic_api_key:
        logger.warning("No LLM API keys configured - skipping email parser")
        return None
        
    try:
        # Note: EmailLLMParser gets its configuration from environment variables
        # This is consistent with the current implementation
        parser = EmailLLMParser()
        logger.info("Email LLM parser created successfully")
        return parser
    except Exception as e:
        logger.error(f"Failed to create Email LLM parser: {e}")
        raise


def create_service_container(config: Optional[ServiceConfig] = None) -> ServiceContainer:
    """
    Create and configure a service container with all standard services
    
    Args:
        config: Service configuration, uses default if None
        
    Returns:
        Configured ServiceContainer instance
    """
    if config is None:
        from .config import create_default_config
        config = create_default_config()
    
    # Validate configuration
    is_valid, error_message = config.validate()
    if not is_valid:
        logger.warning(f"Service configuration validation failed: {error_message}")
        # Continue anyway - some services may still work
    
    # Create container
    container = ServiceContainer(config)
    
    # Register all service factories
    container.register_factory("gmail_provider", create_gmail_provider)
    container.register_factory("sheets_logger", create_sheets_logger)
    container.register_factory("llm_logger", create_llm_logger)
    container.register_factory("email_parser", create_email_parser)
    
    logger.info("Service container created with all factories registered")
    return container


def create_test_container() -> ServiceContainer:
    """
    Create a service container suitable for testing
    
    Returns container with mock-friendly configuration
    """
    from .config import ServiceConfig
    
    # Create minimal config for testing
    test_config = ServiceConfig(
        debug=True,
        environment="test",
        enable_trading=False
    )
    
    container = ServiceContainer(test_config)
    
    # Register factories but with test-specific implementations
    # (In real tests, these would be replaced with mocks)
    container.register_factory("gmail_provider", create_gmail_provider)
    container.register_factory("sheets_logger", create_sheets_logger)
    container.register_factory("llm_logger", create_llm_logger) 
    container.register_factory("email_parser", create_email_parser)
    
    logger.info("Test service container created")
    return container