"""
Configuration management for secrets, API keys, and constants
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# =============================================================================
# Google Cloud Configuration
# =============================================================================

GOOGLE_PROJECT_ID = os.getenv('GOOGLE_PROJECT_ID', 'gmail-trade-alert-system')
GOOGLE_CREDENTIALS_FILE = os.getenv('GOOGLE_CREDENTIALS_FILE', 'credentials.json')
GMAIL_CREDENTIALS_FILE = os.getenv('GMAIL_CREDENTIALS_FILE', 'gmail_credentials.json')

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

OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
OPENAI_MODEL = os.getenv('OPENAI_MODEL', 'gpt-4')
OPENAI_MAX_TOKENS = int(os.getenv('OPENAI_MAX_TOKENS', '1000'))

ANTHROPIC_API_KEY = os.getenv('ANTHROPIC_API_KEY')

# =============================================================================
# Google Sheets Logging
# =============================================================================

GOOGLE_SHEETS_DOC_ID = os.getenv('GOOGLE_SHEETS_DOC_ID')
GOOGLE_SHEETS_WORKSHEET = os.getenv('GOOGLE_SHEETS_WORKSHEET', 'TradeLog')

# =============================================================================
# Web Server Configuration
# =============================================================================

HOST = os.getenv('HOST', '0.0.0.0')
PORT = int(os.getenv('PORT', '8000'))
WEBHOOK_BASE_URL = os.getenv('WEBHOOK_BASE_URL')
WEBHOOK_SECRET = os.getenv('WEBHOOK_SECRET')

# =============================================================================
# Forum Scraping Configuration
# =============================================================================

FORUM_BASE_URL = os.getenv('FORUM_BASE_URL', 'https://io-fund.com')
FORUM_LOGIN_URL = os.getenv('FORUM_LOGIN_URL', 'https://io-fund.com/login')
FORUM_USERNAME = os.getenv('FORUM_USERNAME')
FORUM_PASSWORD = os.getenv('FORUM_PASSWORD')
USER_AGENT = os.getenv('USER_AGENT', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')

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