"""
LLM-based email parser for extracting trade information
"""

import json
import yaml
import logging
from pathlib import Path
from typing import Dict, Any, Optional
from dataclasses import dataclass
import re

from ..config import (
    OPENAI_API_KEY, OPENAI_MODEL, OPENAI_MAX_TOKENS, OPENAI_TEMPERATURE,
    ANTHROPIC_API_KEY, ANTHROPIC_MODEL, ANTHROPIC_MAX_TOKENS, ANTHROPIC_TEMPERATURE
)


logger = logging.getLogger(__name__)


@dataclass
class ParseResult:
    """Result of email parsing operation"""
    is_trading_alert: bool
    trades: Optional[list] = None
    error: Optional[str] = None
    raw_response: Optional[str] = None


class EmailLLMParser:
    """LLM-based parser for extracting trade information from emails"""
    
    def __init__(self):
        self.openai_client = None
        self.anthropic_client = None
        self._setup_llm_clients()
        self.prompt_config = self._load_prompt_config()
    
    def _setup_llm_clients(self):
        """Initialize LLM API clients"""
        # Setup OpenAI client
        if OPENAI_API_KEY:
            try:
                import openai
                self.openai_client = openai.OpenAI(api_key=OPENAI_API_KEY)
                logger.info("OpenAI client initialized successfully")
            except ImportError:
                logger.warning("OpenAI package not available. Install with: pip install openai")
            except Exception as e:
                logger.error(f"Failed to initialize OpenAI client: {e}")
        
        # Setup Anthropic client
        if ANTHROPIC_API_KEY:
            try:
                import anthropic
                self.anthropic_client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
                logger.info("Anthropic client initialized successfully")
            except ImportError:
                logger.warning("Anthropic package not available. Install with: pip install anthropic")
            except Exception as e:
                logger.error(f"Failed to initialize Anthropic client: {e}")
        
        if not self.openai_client and not self.anthropic_client:
            raise ValueError("No LLM clients available. Please provide OPENAI_API_KEY or ANTHROPIC_API_KEY")
    
    def _load_prompt_config(self) -> Dict[str, Any]:
        """Load prompt configuration from YAML file"""
        config_path = Path(__file__).parent / "extract_trade_prompt.yaml"
        
        try:
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f)
            logger.info("Prompt configuration loaded successfully")
            return config
        except FileNotFoundError:
            logger.error(f"Prompt configuration file not found at {config_path}")
            raise
        except yaml.YAMLError as e:
            logger.error(f"Failed to parse YAML configuration: {e}")
            raise
    
    def _build_prompt(self, email_content: str) -> str:
        """Build the complete prompt for LLM"""
        user_prompt = self.prompt_config["user_prompt"].format(email_content=email_content)
        return user_prompt
    
    def _call_openai(self, email_content: str) -> str:
        """Call OpenAI API for parsing"""
        if not self.openai_client:
            raise ValueError("OpenAI client not available")
        
        system_prompt = self.prompt_config["system_prompt"]
        user_prompt = self._build_prompt(email_content)
        
        try:
            response = self.openai_client.chat.completions.create(
                model=OPENAI_MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                max_tokens=OPENAI_MAX_TOKENS,
                temperature=OPENAI_TEMPERATURE
            )
            
            return response.choices[0].message.content.strip()
        
        except Exception as e:
            logger.error(f"OpenAI API call failed: {e}")
            raise
    
    def _call_anthropic(self, email_content: str) -> str:
        """Call Anthropic Claude API for parsing"""
        if not self.anthropic_client:
            raise ValueError("Anthropic client not available")
        
        system_prompt = self.prompt_config["system_prompt"]
        user_prompt = self._build_prompt(email_content)
        
        try:
            message = self.anthropic_client.messages.create(
                model=ANTHROPIC_MODEL,
                max_tokens=ANTHROPIC_MAX_TOKENS,
                temperature=ANTHROPIC_TEMPERATURE,
                system=system_prompt,
                messages=[
                    {"role": "user", "content": user_prompt}
                ]
            )
            
            return message.content[0].text.strip()
        
        except Exception as e:
            logger.error(f"Anthropic API call failed: {e}")
            raise
    
    def _extract_json_from_response(self, response: str) -> Dict[str, Any]:
        """Extract JSON from LLM response, handling potential markdown formatting"""
        # Remove markdown code blocks if present
        json_match = re.search(r'```(?:json)?\s*(.*?)\s*```', response, re.DOTALL)
        if json_match:
            json_str = json_match.group(1)
        else:
            json_str = response.strip()
        
        try:
            return json.loads(json_str)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON from response: {e}")
            logger.error(f"Raw response: {response}")
            raise ValueError(f"Invalid JSON response: {e}")
    
    def _validate_parse_result(self, parsed_data: Dict[str, Any]) -> bool:
        """Validate the parsed result matches expected schema"""
        if not isinstance(parsed_data, dict):
            return False
        
        if "is_trading_alert" not in parsed_data:
            return False
        
        if not isinstance(parsed_data["is_trading_alert"], bool):
            return False
        
        # If it's a trading alert, validate trades structure
        if parsed_data["is_trading_alert"]:
            if "trades" not in parsed_data:
                return False
            
            if not isinstance(parsed_data["trades"], list):
                return False
            
            for trade in parsed_data["trades"]:
                if not isinstance(trade, dict):
                    return False
                
                # Check required fields
                if "ticker" not in trade or "action" not in trade:
                    return False
                
                # Validate action values
                valid_actions = ["buy", "sell", "short", "adjust allocation", "close"]
                if trade["action"] not in valid_actions:
                    return False
        
        return True
    
    def parse_email(self, email_content: str) -> ParseResult:
        """
        Parse email content and extract trade information
        
        Args:
            email_content: Raw email content to parse
            
        Returns:
            ParseResult with is_trading_alert, trades, and any errors
        """
        if not email_content or not email_content.strip():
            return ParseResult(
                is_trading_alert=False,
                error="Empty email content provided"
            )
        
        # Try Anthropic first, then OpenAI as fallback
        for client_name, client_method in [("Anthropic", self._call_anthropic), ("OpenAI", self._call_openai)]:
            try:
                if (client_name == "Anthropic" and not self.anthropic_client) or \
                   (client_name == "OpenAI" and not self.openai_client):
                    continue
                
                logger.info(f"Attempting to parse email with {client_name}")
                raw_response = client_method(email_content)
                
                # Extract and validate JSON
                parsed_data = self._extract_json_from_response(raw_response)
                
                if not self._validate_parse_result(parsed_data):
                    logger.warning(f"{client_name} returned invalid result structure")
                    continue
                
                logger.info(f"Successfully parsed email with {client_name}")
                return ParseResult(
                    is_trading_alert=parsed_data["is_trading_alert"],
                    trades=parsed_data.get("trades"),
                    raw_response=raw_response
                )
                
            except Exception as e:
                logger.error(f"Failed to parse with {client_name}: {e}")
                continue
        
        # If all clients failed
        return ParseResult(
            is_trading_alert=False,
            error="All LLM clients failed to parse email"
        )