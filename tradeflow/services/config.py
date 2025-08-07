"""
Service configuration for dependency injection container
"""

from dataclasses import dataclass
from typing import Optional, Dict, Any
from ..config import (
    # Gmail configuration
    GMAIL_CREDENTIALS_FILE, GMAIL_TOKEN_FILE, GMAIL_SENDER_WHITELIST, GMAIL_DOMAIN_WHITELIST,
    # LLM configuration  
    OPENAI_API_KEY, OPENAI_MODEL, OPENAI_MAX_TOKENS, OPENAI_TEMPERATURE,
    ANTHROPIC_API_KEY, ANTHROPIC_MODEL, ANTHROPIC_MAX_TOKENS, ANTHROPIC_TEMPERATURE,
    # Google Sheets configuration
    GOOGLE_CREDENTIALS_FILE, GOOGLE_SHEETS_DOC_ID, 
    GOOGLE_SHEETS_WORKSHEET, GOOGLE_SHEETS_LLM_WORKSHEET,
    # Environment settings
    DEBUG, ENVIRONMENT, ENABLE_TRADING
)


@dataclass
class ServiceConfig:
    """Configuration for service layer components"""
    
    # Gmail Provider Configuration
    gmail_credentials_file: Optional[str] = None
    gmail_token_file: Optional[str] = None
    gmail_sender_whitelist: list = None
    gmail_domain_whitelist: list = None
    
    # LLM Configuration
    openai_api_key: Optional[str] = None
    openai_model: str = "gpt-4"
    openai_max_tokens: int = 1000
    openai_temperature: float = 0.1
    
    anthropic_api_key: Optional[str] = None
    anthropic_model: str = "claude-3-5-sonnet-20241022"
    anthropic_max_tokens: int = 1000
    anthropic_temperature: float = 0.1
    
    # Google Sheets Configuration
    google_credentials_file: Optional[str] = None
    google_sheets_doc_id: Optional[str] = None
    google_sheets_worksheet: str = "TradeLog"
    google_sheets_llm_worksheet: str = "LLMParsingLog"
    
    # Environment Settings
    debug: bool = False
    environment: str = "development"
    enable_trading: bool = False
    
    def __post_init__(self):
        """Set defaults from environment if not provided"""
        if self.gmail_credentials_file is None:
            self.gmail_credentials_file = GMAIL_CREDENTIALS_FILE
        if self.gmail_token_file is None:
            self.gmail_token_file = GMAIL_TOKEN_FILE
        if self.gmail_sender_whitelist is None:
            self.gmail_sender_whitelist = GMAIL_SENDER_WHITELIST or []
        if self.gmail_domain_whitelist is None:
            self.gmail_domain_whitelist = GMAIL_DOMAIN_WHITELIST or []
            
        if self.openai_api_key is None:
            self.openai_api_key = OPENAI_API_KEY
        if self.openai_model is None:
            self.openai_model = OPENAI_MODEL
        if self.openai_max_tokens is None:
            self.openai_max_tokens = OPENAI_MAX_TOKENS
        if self.openai_temperature is None:
            self.openai_temperature = OPENAI_TEMPERATURE
            
        if self.anthropic_api_key is None:
            self.anthropic_api_key = ANTHROPIC_API_KEY
        if self.anthropic_model is None:
            self.anthropic_model = ANTHROPIC_MODEL
        if self.anthropic_max_tokens is None:
            self.anthropic_max_tokens = ANTHROPIC_MAX_TOKENS
        if self.anthropic_temperature is None:
            self.anthropic_temperature = ANTHROPIC_TEMPERATURE
            
        if self.google_credentials_file is None:
            self.google_credentials_file = GOOGLE_CREDENTIALS_FILE
        if self.google_sheets_doc_id is None:
            self.google_sheets_doc_id = GOOGLE_SHEETS_DOC_ID
        if self.google_sheets_worksheet is None:
            self.google_sheets_worksheet = GOOGLE_SHEETS_WORKSHEET
        if self.google_sheets_llm_worksheet is None:
            self.google_sheets_llm_worksheet = GOOGLE_SHEETS_LLM_WORKSHEET
            
        self.debug = DEBUG
        self.environment = ENVIRONMENT  
        self.enable_trading = ENABLE_TRADING
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary for logging/debugging"""
        config_dict = {}
        for key, value in self.__dict__.items():
            # Redact sensitive information
            if 'api_key' in key.lower() or 'token' in key.lower() or 'password' in key.lower():
                config_dict[key] = '***REDACTED***' if value else None
            else:
                config_dict[key] = value
        return config_dict
    
    def validate(self) -> tuple[bool, Optional[str]]:
        """Validate configuration for required services"""
        errors = []
        
        # Check for at least one LLM provider
        if not self.openai_api_key and not self.anthropic_api_key:
            errors.append("At least one LLM API key (OpenAI or Anthropic) is required")
        
        # Check Gmail configuration if sender/domain whitelists are configured
        if (self.gmail_sender_whitelist or self.gmail_domain_whitelist) and not self.gmail_credentials_file:
            errors.append("Gmail credentials file required when using sender/domain whitelists")
        
        # Check Google Sheets configuration if logging is needed
        if not self.google_credentials_file or not self.google_sheets_doc_id:
            errors.append("Google Sheets configuration (credentials + doc ID) required for logging")
        
        if errors:
            return False, "; ".join(errors)
        
        return True, None


def create_default_config() -> ServiceConfig:
    """Create default service configuration from environment variables"""
    return ServiceConfig()