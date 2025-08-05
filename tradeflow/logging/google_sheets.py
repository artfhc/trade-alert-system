"""
GSpread logic for appending logs to Google Sheets
"""

import logging
import json
from datetime import datetime
from typing import Dict, Any, Optional, List

try:
    import gspread
    from google.oauth2.service_account import Credentials
    GSPREAD_AVAILABLE = True
except ImportError:
    GSPREAD_AVAILABLE = False

from ..version import get_version
from ..core.models import Alert

logger = logging.getLogger(__name__)

class GoogleSheetsLogger:
    """
    Google Sheets logger for trade alert system
    Logs all email alerts with version info and whitelist status
    """
    
    # Sheet column headers
    HEADERS = [
        "Timestamp",
        "App Version", 
        "Message ID",
        "Source",
        "Email Subject",
        "Email Sender", 
        "Email Content",
        "Whitelist Status",
        "Processing Status",
        "Error Message",
        "Raw Metadata"
    ]
    
    def __init__(self, credentials_file: str = None, spreadsheet_id: str = None, worksheet_name: str = "TradeLog"):
        """
        Initialize Google Sheets logger
        
        Args:
            credentials_file: Path to Google service account credentials
            spreadsheet_id: Google Sheets spreadsheet ID
            worksheet_name: Name of the worksheet to log to
        """
        self.credentials_file = credentials_file
        self.spreadsheet_id = spreadsheet_id
        self.worksheet_name = worksheet_name
        self.sheet = None
        self.worksheet = None
        self.version = get_version()
        
        if not GSPREAD_AVAILABLE:
            logger.warning("gspread not available - logging to console only")
            return
        
        if credentials_file and spreadsheet_id:
            self._setup_sheets_client()
        else:
            logger.warning("Google Sheets credentials or spreadsheet ID not provided - logging to console only")
        
        logger.info(f"GoogleSheetsLogger initialized (version: {self.version})")
    
    def _setup_sheets_client(self):
        """Setup Google Sheets client with service account authentication"""
        try:
            # Setup credentials with required scopes
            scopes = [
                'https://www.googleapis.com/auth/spreadsheets',
                'https://www.googleapis.com/auth/drive'
            ]
            
            creds = Credentials.from_service_account_file(self.credentials_file, scopes=scopes)
            client = gspread.authorize(creds)
            
            # Open the spreadsheet
            self.sheet = client.open_by_key(self.spreadsheet_id)
            
            # Get or create the worksheet
            try:
                self.worksheet = self.sheet.worksheet(self.worksheet_name)
                logger.info(f"Connected to existing worksheet: {self.worksheet_name}")
            except gspread.WorksheetNotFound:
                self.worksheet = self.sheet.add_worksheet(title=self.worksheet_name, rows=1000, cols=len(self.HEADERS))
                logger.info(f"Created new worksheet: {self.worksheet_name}")
            
            # Setup headers if worksheet is empty
            self._ensure_headers()
            
            logger.info(f"Google Sheets client initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to setup Google Sheets client: {e}")
            self.sheet = None
            self.worksheet = None
    
    def _ensure_headers(self):
        """Ensure the worksheet has proper headers"""
        try:
            if not self.worksheet:
                return
            
            # Check if first row has headers
            first_row = self.worksheet.row_values(1)
            
            if not first_row or first_row != self.HEADERS:
                # Set headers
                self.worksheet.update('A1', [self.HEADERS])
                logger.info("Headers added to Google Sheets")
            
        except Exception as e:
            logger.warning(f"Could not ensure headers: {e}")
    
    def log_email_alert(self, 
                       alert: Alert = None,
                       raw_data: Dict[str, Any] = None,
                       whitelist_status: str = "unknown",
                       processing_status: str = "received", 
                       error_message: str = None) -> bool:
        """
        Log email alert to Google Sheets
        
        Args:
            alert: Parsed Alert object (may be None if parsing failed)
            raw_data: Raw Pub/Sub message data
            whitelist_status: "allowed", "blocked", "unknown", "no_whitelist"
            processing_status: "received", "parsed", "processing", "success", "error"
            error_message: Error details if processing failed
            
        Returns:
            bool: True if logged successfully
        """
        try:
            # Prepare log entry
            log_entry = self._prepare_log_entry(
                alert=alert,
                raw_data=raw_data, 
                whitelist_status=whitelist_status,
                processing_status=processing_status,
                error_message=error_message
            )
            
            # Try to write to Google Sheets first
            if self.worksheet:
                try:
                    # Prepare row data in the correct order
                    row_data = [log_entry[header] for header in self.HEADERS]
                    
                    # Convert complex objects to JSON strings for sheets
                    for i, value in enumerate(row_data):
                        if isinstance(value, (dict, list)):
                            row_data[i] = json.dumps(value)
                        elif value is None:
                            row_data[i] = ""
                        else:
                            row_data[i] = str(value)
                    
                    # Append to sheets
                    self.worksheet.append_row(row_data)
                    logger.info(f"📊 Logged to Google Sheets: {log_entry['Message ID']} - {log_entry['Processing Status']}")
                    return True
                    
                except Exception as e:
                    logger.error(f"Failed to write to Google Sheets: {e}")
                    # Fall through to console logging
            
            # Fallback: log to console
            logger.info("📊 ALERT LOG ENTRY:")
            for key, value in log_entry.items():
                if key == "Email Content" and value and len(value) > 200:
                    logger.info(f"  {key}: {value[:200]}...")
                elif key == "Raw Metadata" and value:
                    logger.info(f"  {key}: {json.dumps(value, indent=2)[:300]}...")
                else:
                    logger.info(f"  {key}: {value}")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to log email alert: {e}")
            return False
    
    def _prepare_log_entry(self,
                          alert: Alert = None,
                          raw_data: Dict[str, Any] = None,
                          whitelist_status: str = "unknown",
                          processing_status: str = "received",
                          error_message: str = None) -> Dict[str, Any]:
        """Prepare log entry data"""
        
        # Extract data from alert if available
        if alert:
            timestamp = alert.timestamp.isoformat()
            message_id = alert.metadata.get('message_id', 'unknown')
            source = alert.source
            email_subject = alert.metadata.get('subject', '')
            email_sender = alert.metadata.get('sender', '')
            email_content = alert.content
            raw_metadata = alert.metadata
        else:
            # Fallback to raw data
            timestamp = datetime.utcnow().isoformat()
            message_id = raw_data.get('message', {}).get('messageId', 'unknown') if raw_data else 'unknown'
            source = 'gmail'
            email_subject = 'Parse Failed'
            email_sender = 'unknown'
            email_content = f"Raw data: {json.dumps(raw_data)[:500]}..." if raw_data else "No data"
            raw_metadata = raw_data or {}
        
        return {
            "Timestamp": timestamp,
            "App Version": self.version,
            "Message ID": message_id,
            "Source": source,
            "Email Subject": email_subject,
            "Email Sender": email_sender,
            "Email Content": email_content,
            "Whitelist Status": whitelist_status,
            "Processing Status": processing_status,
            "Error Message": error_message or "",
            "Raw Metadata": raw_metadata
        }
    
    def setup_sheet_headers(self) -> bool:
        """Setup sheet headers if they don't exist"""
        if self.worksheet:
            self._ensure_headers()
            return True
        else:
            logger.info(f"Sheet headers would be: {', '.join(self.HEADERS)}")
            return False