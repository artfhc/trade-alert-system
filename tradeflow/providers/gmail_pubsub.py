"""
Gmail Pub/Sub implementation of AlertProvider
"""

import base64
import json
import logging
from datetime import datetime
from typing import Dict, Any, Optional, List
from email.mime.text import MIMEText
from email.utils import parsedate_to_datetime

try:
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build
    GOOGLE_AVAILABLE = True
except ImportError:
    GOOGLE_AVAILABLE = False

from .base import AlertProvider, register_provider
from ..core.models import Alert


class GmailPubSubProvider(AlertProvider):
    """
    Gmail Pub/Sub provider for processing trade alerts from email
    """
    
    SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']
    
    def __init__(self, credentials_file: str = None, token_file: str = None, 
                 sender_whitelist: List[str] = None):
        super().__init__()
        
        if not GOOGLE_AVAILABLE:
            raise ImportError("Google client libraries not available. Install with: pip install google-auth google-auth-oauthlib google-auth-httplib2 google-api-python-client")
        
        self.credentials_file = credentials_file
        self.token_file = token_file or 'gmail_token.json'
        self.sender_whitelist = sender_whitelist or []
        self.gmail_service = None
        
        self._setup_gmail_client()
    
    def _setup_gmail_client(self):
        """Set up Gmail API client with authentication"""
        try:
            creds = None
            
            # Load existing token
            if self.token_file:
                try:
                    creds = Credentials.from_authorized_user_file(self.token_file, self.SCOPES)
                except Exception as e:
                    self.logger.warning(f"Could not load token file: {e}")
            
            # If no valid credentials, get new ones
            if not creds or not creds.valid:
                if creds and creds.expired and creds.refresh_token:
                    creds.refresh(Request())
                else:
                    if not self.credentials_file:
                        raise ValueError("Gmail credentials file not provided")
                    
                    flow = InstalledAppFlow.from_client_secrets_file(
                        self.credentials_file, self.SCOPES)
                    creds = flow.run_local_server(port=0)
                
                # Save credentials for future use
                if self.token_file:
                    with open(self.token_file, 'w') as token:
                        token.write(creds.to_json())
            
            self.gmail_service = build('gmail', 'v1', credentials=creds)
            self.logger.info("Gmail API client initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to setup Gmail client: {e}")
            raise
    
    def get_source_name(self) -> str:
        """Get the source name for this provider"""
        return "gmail"
    
    def parse_alert(self, raw_data: Dict[str, Any]) -> Alert:
        """
        Parse Gmail Pub/Sub notification into Alert object
        
        Args:
            raw_data: Pub/Sub message data
            
        Returns:
            Alert: Parsed alert object
        """
        try:
            # Extract Pub/Sub message
            pubsub_data = self._decode_pubsub_message(raw_data)
            
            # Get Gmail message ID
            message_id = pubsub_data.get('historyId')  # This might need adjustment based on actual Pub/Sub format
            
            # For now, we'll use a placeholder since we need to understand the exact Pub/Sub format
            # In a real implementation, you'd extract the message ID from the Pub/Sub notification
            gmail_message_id = pubsub_data.get('messageId', 'unknown')
            
            # Fetch full email content from Gmail API
            email_data = self._fetch_email_content(gmail_message_id)
            
            # Extract metadata
            metadata = self.extract_metadata(email_data)
            
            # Create timestamp
            timestamp = self._extract_timestamp(email_data)
            
            # Get email content
            content = self._extract_email_body(email_data)
            content = self.sanitize_content(content)
            
            # Validate sender if whitelist is configured
            if self.sender_whitelist:
                sender = metadata.get('sender', '')
                if not any(allowed in sender for allowed in self.sender_whitelist):
                    raise ValueError(f"Sender {sender} not in whitelist")
            
            alert = Alert(
                source=self.get_source_name(),
                content=content,
                timestamp=timestamp,
                metadata=metadata
            )
            
            if not self.validate_alert(alert):
                raise ValueError("Alert validation failed")
            
            return alert
            
        except Exception as e:
            self.logger.error(f"Error parsing Gmail alert: {e}")
            raise ValueError(f"Failed to parse Gmail alert: {e}")
    
    def extract_metadata(self, email_data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract metadata from Gmail message data"""
        headers = email_data.get('payload', {}).get('headers', [])
        header_dict = {h['name']: h['value'] for h in headers}
        
        return {
            'message_id': email_data.get('id'),
            'thread_id': email_data.get('threadId'),
            'sender': header_dict.get('From', ''),
            'subject': header_dict.get('Subject', ''),
            'date': header_dict.get('Date', ''),
            'labels': email_data.get('labelIds', []),
            'snippet': email_data.get('snippet', ''),
        }
    
    def _decode_pubsub_message(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """Decode base64 Pub/Sub message data"""
        try:
            # Handle Pub/Sub message format
            message = raw_data.get('message', {})
            data = message.get('data', '')
            
            if data:
                # Decode base64 data
                decoded_data = base64.b64decode(data).decode('utf-8')
                return json.loads(decoded_data)
            else:
                # Sometimes the data might be directly in attributes
                return message.get('attributes', {})
                
        except Exception as e:
            self.logger.error(f"Error decoding Pub/Sub message: {e}")
            raise ValueError(f"Invalid Pub/Sub message format: {e}")
    
    def _fetch_email_content(self, message_id: str) -> Dict[str, Any]:
        """Fetch full email content from Gmail API"""
        try:
            if not self.gmail_service:
                raise ValueError("Gmail service not initialized")
            
            # Get the full message
            message = self.gmail_service.users().messages().get(
                userId='me', 
                id=message_id,
                format='full'
            ).execute()
            
            return message
            
        except Exception as e:
            self.logger.error(f"Error fetching Gmail message {message_id}: {e}")
            raise
    
    def _extract_email_body(self, email_data: Dict[str, Any]) -> str:
        """Extract email body content"""
        try:
            payload = email_data.get('payload', {})
            
            # Handle multipart messages
            if 'parts' in payload:
                for part in payload['parts']:
                    if part.get('mimeType') == 'text/plain':
                        data = part.get('body', {}).get('data', '')
                        if data:
                            return base64.urlsafe_b64decode(data).decode('utf-8')
            
            # Handle simple messages
            if payload.get('mimeType') == 'text/plain':
                data = payload.get('body', {}).get('data', '')
                if data:
                    return base64.urlsafe_b64decode(data).decode('utf-8')
            
            # Fallback to snippet
            return email_data.get('snippet', '')
            
        except Exception as e:
            self.logger.error(f"Error extracting email body: {e}")
            return email_data.get('snippet', '')
    
    def _extract_timestamp(self, email_data: Dict[str, Any]) -> datetime:
        """Extract timestamp from email data"""
        try:
            # Try internal date first (Unix timestamp in milliseconds)
            internal_date = email_data.get('internalDate')
            if internal_date:
                return datetime.fromtimestamp(int(internal_date) / 1000)
            
            # Fallback to Date header
            headers = email_data.get('payload', {}).get('headers', [])
            for header in headers:
                if header['name'] == 'Date':
                    return parsedate_to_datetime(header['value'])
            
            # Ultimate fallback
            return datetime.utcnow()
            
        except Exception as e:
            self.logger.warning(f"Error extracting timestamp: {e}")
            return datetime.utcnow()
    
    def validate_sender(self, sender: str) -> bool:
        """Validate sender against whitelist"""
        if not self.sender_whitelist:
            return True
        
        return any(allowed in sender for allowed in self.sender_whitelist)
    
    def check_alert_keywords(self, subject: str, content: str, 
                           keywords: List[str] = None) -> bool:
        """Check if email contains required alert keywords"""
        if not keywords:
            keywords = ['trade', 'alert', 'buy', 'sell', 'position']
        
        text = f"{subject} {content}".lower()
        return any(keyword.lower() in text for keyword in keywords)


# Register the provider
register_provider('gmail', GmailPubSubProvider)