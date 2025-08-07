"""
Configuration management for secrets, API keys, and constants
"""

import os
import base64
import json
import tempfile
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

def _create_temp_credentials_file(base64_content: str, prefix: str) -> str:
    """Create a temporary file from base64 encoded credentials"""
    try:
        # Decode base64 content
        json_content = base64.b64decode(base64_content).decode('utf-8')
        
        # Validate it's valid JSON
        json.loads(json_content)
        
        # Create temporary file
        temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.json', prefix=prefix, delete=False)
        temp_file.write(json_content)
        temp_file.close()
        
        return temp_file.name
    except Exception as e:
        raise ValueError(f"Failed to create credentials file from base64: {e}")

def _get_credentials_file(env_var_file: str, env_var_json: str, default_file: str) -> str:
    """Get credentials file path, either from file path or base64 JSON"""
    # First try to get file path
    file_path = os.getenv(env_var_file, default_file)
    
    # If file exists, use it
    if os.path.exists(file_path):
        return file_path
    
    # Otherwise, try to get base64 JSON and create temp file
    base64_json = os.getenv(env_var_json)
    if base64_json:
        prefix = env_var_json.lower().replace('_', '-')
        return _create_temp_credentials_file(base64_json, prefix)
    
    # Fall back to default file path (might not exist)
    return file_path

# =============================================================================
# Google Cloud Configuration
# =============================================================================

GOOGLE_PROJECT_ID = os.getenv('GOOGLE_PROJECT_ID', 'gmail-trade-alert-system')
GOOGLE_CREDENTIALS_FILE = _get_credentials_file('GOOGLE_CREDENTIALS_FILE', 'GOOGLE_CREDENTIALS_JSON', 'credentials.json')
GMAIL_CREDENTIALS_FILE = _get_credentials_file('GMAIL_CREDENTIALS_FILE', 'GMAIL_CREDENTIALS_JSON', 'gmail_credentials.json')
GMAIL_TOKEN_FILE = _get_credentials_file('GMAIL_TOKEN_FILE', 'GMAIL_TOKEN_JSON', 'gmail_token.json')

# =============================================================================
# Pub/Sub Configuration  
# =============================================================================

PUBSUB_TOPIC = os.getenv('PUBSUB_TOPIC', 'gmail-trade-alerts')
PUBSUB_SUBSCRIPTION = os.getenv('PUBSUB_SUBSCRIPTION', 'gmail-alerts-sub')
PUBSUB_WEBHOOK_SUBSCRIPTION = os.getenv('PUBSUB_WEBHOOK_SUBSCRIPTION', 'gmail-webhook-sub')

# =============================================================================
# Gmail Configuration
# =============================================================================

GMAIL_SENDER_WHITELIST = os.getenv('GMAIL_SENDER_WHITELIST', '').split(',') if os.getenv('GMAIL_SENDER_WHITELIST') else []
GMAIL_DOMAIN_WHITELIST = os.getenv('GMAIL_DOMAIN_WHITELIST', 'txt.voice.google.com').split(',') if os.getenv('GMAIL_DOMAIN_WHITELIST') else ['txt.voice.google.com']
GMAIL_ALERT_KEYWORDS = os.getenv('GMAIL_ALERT_KEYWORDS', 'trade,alert,buy,sell,position').split(',')
GMAIL_LABEL_FILTER = os.getenv('GMAIL_LABEL_FILTER', 'INBOX')

# =============================================================================
# Alpaca Trading Configuration
# =============================================================================

ALPACA_API_KEY = os.getenv('ALPACA_API_KEY')
ALPACA_SECRET_KEY = os.getenv('ALPACA_SECRET_KEY')
ALPACA_BASE_URL = os.getenv('ALPACA_BASE_URL', 'https://paper-api.alpaca.markets')

# =============================================================================
# LLM Configuration
# =============================================================================

# OpenAI Configuration
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
OPENAI_MODEL = os.getenv('OPENAI_MODEL', 'gpt-4')
OPENAI_MAX_TOKENS = int(os.getenv('OPENAI_MAX_TOKENS', '1000'))
OPENAI_TEMPERATURE = float(os.getenv('OPENAI_TEMPERATURE', '0.1'))

# Anthropic Configuration  
ANTHROPIC_API_KEY = os.getenv('ANTHROPIC_API_KEY')
ANTHROPIC_MODEL = os.getenv('ANTHROPIC_MODEL', 'claude-3-5-sonnet-20241022')
ANTHROPIC_MAX_TOKENS = int(os.getenv('ANTHROPIC_MAX_TOKENS', '1000'))
ANTHROPIC_TEMPERATURE = float(os.getenv('ANTHROPIC_TEMPERATURE', '0.1'))

# =============================================================================
# Google Sheets Logging
# =============================================================================

GOOGLE_SHEETS_DOC_ID = os.getenv('GOOGLE_SHEETS_DOC_ID')
GOOGLE_SHEETS_WORKSHEET = os.getenv('GOOGLE_SHEETS_WORKSHEET', 'TradeLog')
GOOGLE_SHEETS_LLM_WORKSHEET = os.getenv('GOOGLE_SHEETS_LLM_WORKSHEET', 'LLMParsingLog')

# =============================================================================
# Web Server Configuration
# =============================================================================

HOST = os.getenv('HOST', '0.0.0.0')
PORT = int(os.getenv('PORT', '8000'))
WEBHOOK_BASE_URL = os.getenv('WEBHOOK_BASE_URL')
WEBHOOK_SECRET = os.getenv('WEBHOOK_SECRET')


# =============================================================================
# Trading Configuration
# =============================================================================

DEFAULT_POSITION_SIZE = float(os.getenv('DEFAULT_POSITION_SIZE', '1000'))
MAX_POSITION_SIZE = float(os.getenv('MAX_POSITION_SIZE', '10000'))
MAX_DAILY_TRADES = int(os.getenv('MAX_DAILY_TRADES', '10'))
MAX_PORTFOLIO_RISK = float(os.getenv('MAX_PORTFOLIO_RISK', '0.02'))

# =============================================================================
# Logging Configuration
# =============================================================================

LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
LOG_FILE = os.getenv('LOG_FILE', 'logs/tradeflow.log')

# =============================================================================
# Development Configuration
# =============================================================================

ENVIRONMENT = os.getenv('ENVIRONMENT', 'development')
DEBUG = os.getenv('DEBUG', 'True').lower() in ('true', '1', 'yes', 'on')
ENABLE_TRADING = os.getenv('ENABLE_TRADING', 'False').lower() in ('true', '1', 'yes', 'on')

def validate_config():
    """Validate that required configuration is present."""
    required_vars = []
    
    if not GOOGLE_PROJECT_ID:
        required_vars.append('GOOGLE_PROJECT_ID')
    
    if not GOOGLE_CREDENTIALS_FILE and not GMAIL_CREDENTIALS_FILE:
        required_vars.append('GOOGLE_CREDENTIALS_FILE or GMAIL_CREDENTIALS_FILE')
    
    if required_vars:
        raise ValueError(f"Missing required environment variables: {', '.join(required_vars)}")
    
    return True