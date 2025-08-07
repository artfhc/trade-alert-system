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
                 sender_whitelist: List[str] = None, domain_whitelist: List[str] = None):
        super().__init__()
        
        if not GOOGLE_AVAILABLE:
            raise ImportError("Google client libraries not available. Install with: pip install google-auth google-auth-oauthlib google-auth-httplib2 google-api-python-client")
        
        self.credentials_file = credentials_file
        self.token_file = token_file or 'gmail_token.json'
        self.sender_whitelist = sender_whitelist or []
        self.domain_whitelist = domain_whitelist or []
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
                    try:
                        creds.refresh(Request())
                    except Exception as e:
                        self.logger.error(f"Failed to refresh credentials: {e}")
                        # In production, we can't do interactive auth, so we'll skip Gmail setup
                        self._handle_production_auth_failure()
                        return
                else:
                    if not self.credentials_file:
                        self.logger.warning("Gmail credentials file not provided")
                        self._handle_production_auth_failure()
                        return
                    
                    # Check if we're in a production environment (no display/browser available)
                    import os
                    if os.getenv('ENVIRONMENT') == 'production' or not os.getenv('DISPLAY'):
                        self.logger.warning("Production environment detected - skipping interactive OAuth")
                        self._handle_production_auth_failure()
                        return
                    
                    try:
                        flow = InstalledAppFlow.from_client_secrets_file(
                            self.credentials_file, self.SCOPES)
                        creds = flow.run_local_server(port=0)
                    except Exception as e:
                        self.logger.error(f"Interactive OAuth failed: {e}")
                        self._handle_production_auth_failure()
                        return
                
                # Save credentials for future use
                if self.token_file and creds:
                    try:
                        with open(self.token_file, 'w') as token:
                            token.write(creds.to_json())
                    except Exception as e:
                        self.logger.warning(f"Could not save token file: {e}")
            
            if creds:
                self.gmail_service = build('gmail', 'v1', credentials=creds)
                self.logger.info("Gmail API client initialized successfully")
            else:
                self._handle_production_auth_failure()
            
        except Exception as e:
            self.logger.error(f"Failed to setup Gmail client: {e}")
            self._handle_production_auth_failure()
    
    def _handle_production_auth_failure(self):
        """Handle authentication failure in production environment"""
        self.gmail_service = None
        self.logger.warning("Gmail service not available - webhook will accept messages but cannot fetch email content")
        self.logger.info("For full functionality, you need to:")
        self.logger.info("1. Run OAuth flow locally to generate gmail_token.json")
        self.logger.info("2. Upload gmail_token.json to your production environment")
        self.logger.info("3. Or use service account authentication instead")
    
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
            
            # Extract Gmail message ID from Pub/Sub notification
            # Gmail Pub/Sub notifications contain historyId, but we need to extract the actual message ID
            # from the Gmail API using the historyId
            gmail_message_id = None
            
            # Try different possible locations for message ID
            if 'messageId' in pubsub_data:
                gmail_message_id = pubsub_data['messageId']
            elif 'historyId' in pubsub_data:
                # We have a historyId - in a real implementation, we'd use this to get recent messages
                history_id = pubsub_data['historyId']
                self.logger.info(f"Received Gmail history ID: {history_id}")
                # For now, we'll skip fetching the actual message and use the notification data
                gmail_message_id = f"history_{history_id}"
            else:
                # Fallback - look in the raw Pub/Sub message
                raw_message = raw_data.get('message', {})
                gmail_message_id = raw_message.get('messageId', 'unknown')
            
            # Default metadata and content
            metadata = {
                'message_id': gmail_message_id,
                'sender': 'unknown',
                'subject': 'Gmail Pub/Sub Notification',
                'raw_pubsub_data': pubsub_data
            }
            timestamp = datetime.utcnow()
            content = f"Gmail Pub/Sub notification received. Message ID: {gmail_message_id}"
            
            # Try to fetch full email content from Gmail API if service is available
            if self.gmail_service and gmail_message_id and gmail_message_id != 'unknown':
                try:
                    if gmail_message_id.startswith('history_'):
                        # We have a history ID - get recent messages
                        history_id = gmail_message_id.replace('history_', '')
                        recent_message = self._get_recent_message_from_history(history_id)
                        if recent_message:
                            email_data = self._fetch_email_content(recent_message)
                            self.logger.info(f"Fetched email data for message {recent_message} (truncated for logs)")
                            self.logger.debug(f"Full email data: {json.dumps(email_data, indent=2, default=str)}")
                            metadata = self.extract_metadata(email_data)
                            timestamp = self._extract_timestamp(email_data)
                            content = self._extract_email_body(email_data)
                            content = self.sanitize_content(content)
                            self.logger.info(f"📧 Email content extracted from message {recent_message}:")
                            self.logger.info(f"📧 Subject: {metadata.get('subject', 'N/A')}")
                            self.logger.info(f"📧 From: {metadata.get('sender', 'N/A')}")
                            self.logger.info(f"📧 Content: {content[:500]}...")  # First 500 chars
                    else:
                        # We have a direct message ID
                        email_data = self._fetch_email_content(gmail_message_id)
                        self.logger.info(f"Fetched email data for message {gmail_message_id} (truncated for logs)")
                        self.logger.debug(f"Full email data: {json.dumps(email_data, indent=2, default=str)}")
                        metadata = self.extract_metadata(email_data)
                        timestamp = self._extract_timestamp(email_data)
                        content = self._extract_email_body(email_data)
                        content = self.sanitize_content(content)
                        self.logger.info(f"📧 Email content extracted from message {gmail_message_id}:")
                        self.logger.info(f"📧 Subject: {metadata.get('subject', 'N/A')}")
                        self.logger.info(f"📧 From: {metadata.get('sender', 'N/A')}")
                        self.logger.info(f"📧 Content: {content[:500]}...")  # First 500 chars
                except Exception as e:
                    self.logger.warning(f"Could not fetch email content for {gmail_message_id}: {e}")
                    # Keep default values
            else:
                if not self.gmail_service:
                    self.logger.warning("Gmail service not available - using basic Pub/Sub data only")
                else:
                    self.logger.warning(f"Invalid Gmail message ID: {gmail_message_id} - using basic Pub/Sub data only")
            
            # Validate sender and domain whitelists
            sender = metadata.get('sender', '')
            if sender != 'unknown' and (self.sender_whitelist or self.domain_whitelist):
                sender_allowed = not self.sender_whitelist or any(allowed in sender for allowed in self.sender_whitelist)
                domain_allowed = not self.domain_whitelist or self._is_domain_whitelisted(sender)
                
                # Allow if either whitelist passes (or if no whitelist is configured for that type)
                if not (sender_allowed or domain_allowed):
                    error_parts = []
                    if self.sender_whitelist:
                        whitelist_str = ', '.join(self.sender_whitelist)
                        error_parts.append(f"sender not in whitelist (allowed: {whitelist_str})")
                    if self.domain_whitelist:
                        domain_str = ', '.join(self.domain_whitelist)
                        error_parts.append(f"domain not in whitelist (allowed: {domain_str})")
                    
                    error_message = f"Sender '{sender}' rejected: " + " and ".join(error_parts)
                    raise ValueError(error_message)
            
            alert = Alert(
                source=self.get_source_name(),
                content=content,
                timestamp=timestamp,
                metadata=metadata
            )
            
            is_valid, validation_error = self.validate_alert(alert)
            if not is_valid:
                raise ValueError(f"Alert validation failed: {validation_error}")
            
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
            
            self.logger.info(f"Raw Pub/Sub message: {json.dumps(raw_data, indent=2)}")
            
            if data:
                try:
                    # Decode base64 data
                    decoded_data = base64.b64decode(data).decode('utf-8')
                    parsed_data = json.loads(decoded_data)
                    self.logger.info(f"Decoded Pub/Sub data: {json.dumps(parsed_data, indent=2)}")
                    return parsed_data
                except Exception as decode_error:
                    self.logger.warning(f"Could not decode base64 data: {decode_error}")
                    # Return raw data if decoding fails
                    return {'raw_data': data}
            else:
                # Sometimes the data might be directly in attributes or message itself
                attributes = message.get('attributes', {})
                self.logger.info(f"Using Pub/Sub attributes: {json.dumps(attributes, indent=2)}")
                return attributes
                
        except Exception as e:
            self.logger.error(f"Error decoding Pub/Sub message: {e}")
            # Return whatever we can extract instead of failing
            return {
                'error': str(e),
                'raw_message': raw_data.get('message', {}),
                'message_id': raw_data.get('message', {}).get('messageId', 'unknown')
            }
    
    def _get_recent_message_from_history(self, history_id: str) -> Optional[str]:
        """Get the most recent message ID from Gmail history"""
        try:
            if not self.gmail_service:
                return None
            
            self.logger.info(f"Searching for messages around history ID: {history_id}")
            
            # First, try to get messages from a slightly earlier history point
            # because the historyId in Pub/Sub might be the current state
            try:
                earlier_history_id = str(int(history_id) - 100)  # Go back 100 history entries
                self.logger.info(f"Trying earlier history ID: {earlier_history_id}")
                
                history = self.gmail_service.users().history().list(
                    userId='me',
                    startHistoryId=earlier_history_id,
                    maxResults=50  # Get more messages to find recent ones
                ).execute()
                
                messages = []
                if 'history' in history:
                    for history_item in history['history']:
                        if 'messagesAdded' in history_item:
                            for message_added in history_item['messagesAdded']:
                                messages.append(message_added['message']['id'])
                
                if messages:
                    latest_message_id = messages[-1]  # Get the last (most recent) message
                    self.logger.info(f"Found recent message ID from earlier history: {latest_message_id}")
                    return latest_message_id
                    
            except Exception as earlier_error:
                self.logger.warning(f"Could not search earlier history: {earlier_error}")
            
            # If that didn't work, try getting recent messages directly
            try:
                self.logger.info("Trying to get recent messages directly")
                messages_result = self.gmail_service.users().messages().list(
                    userId='me',
                    maxResults=10,
                    q=""  # Get all recent messages
                ).execute()
                
                if 'messages' in messages_result and messages_result['messages']:
                    latest_message_id = messages_result['messages'][0]['id']  # First message is most recent
                    self.logger.info(f"Found recent message ID from direct query: {latest_message_id}")
                    return latest_message_id
                    
            except Exception as direct_error:
                self.logger.warning(f"Could not get recent messages directly: {direct_error}")
            
            self.logger.warning(f"No messages found using any method for history {history_id}")
            return None
                
        except Exception as e:
            self.logger.error(f"Error fetching Gmail history {history_id}: {e}")
            return None

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
    
    def _is_domain_whitelisted(self, sender: str) -> bool:
        """Check if sender domain is in the whitelist"""
        if not sender or '@' not in sender:
            return False
        
        # Extract domain from sender email (e.g., "user@txt.voice.google.com")
        sender_domain = sender.split('@')[-1].lower()
        
        # Check if any whitelisted domain matches
        for allowed_domain in self.domain_whitelist:
            allowed_domain = allowed_domain.lower().strip()
            # Support wildcard subdomains (e.g., txt.voice.google.com matches abc.txt.voice.google.com)
            if sender_domain == allowed_domain or sender_domain.endswith('.' + allowed_domain):
                return True
        
        return False


# Register the provider
register_provider('gmail', GmailPubSubProvider)