#!/usr/bin/env python3
"""
Gmail Watch Setup Script

This script sets up Gmail watch functionality for the trade alert system.
Run this after configuring your Google Cloud project and credentials.

Usage:
    python setup_gmail_watch.py
"""

import os
import json
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google.oauth2.service_account import Credentials as ServiceAccountCredentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from config import (
    GOOGLE_PROJECT_ID,
    PUBSUB_TOPIC,
    GMAIL_CREDENTIALS_FILE,
    GOOGLE_CREDENTIALS_FILE
)

SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']

def get_gmail_credentials():
    """Get Gmail API credentials from OAuth2 or service account."""
    creds = None
    
    # Try OAuth2 credentials first (for development)
    if os.path.exists(GMAIL_CREDENTIALS_FILE):
        print(f"Using OAuth2 credentials from {GMAIL_CREDENTIALS_FILE}")
        
        # Check if we have stored credentials
        token_file = 'gmail_token.json'
        if os.path.exists(token_file):
            creds = Credentials.from_authorized_user_file(token_file, SCOPES)
        
        # If credentials are invalid or don't exist, refresh or create new ones
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    GMAIL_CREDENTIALS_FILE, SCOPES)
                creds = flow.run_local_server(port=0)
            
            # Save credentials for next run
            with open(token_file, 'w') as token:
                token.write(creds.to_json())
    
    # Try service account credentials (for production)
    elif os.path.exists(GOOGLE_CREDENTIALS_FILE):
        print(f"Using service account credentials from {GOOGLE_CREDENTIALS_FILE}")
        creds = ServiceAccountCredentials.from_service_account_file(
            GOOGLE_CREDENTIALS_FILE, scopes=SCOPES)
    
    else:
        raise FileNotFoundError(
            f"No credentials found. Please provide either:\n"
            f"- OAuth2 credentials at: {GMAIL_CREDENTIALS_FILE}\n"
            f"- Service account credentials at: {GOOGLE_CREDENTIALS_FILE}"
        )
    
    return creds

def setup_gmail_watch():
    """Set up Gmail watch to send notifications to Pub/Sub topic."""
    try:
        # Get credentials
        creds = get_gmail_credentials()
        
        # Build Gmail API service
        service = build('gmail', 'v1', credentials=creds)
        
        # Configure watch request
        topic_name = f'projects/{GOOGLE_PROJECT_ID}/topics/{PUBSUB_TOPIC}'
        
        request_body = {
            'labelIds': ['INBOX'],  # Monitor INBOX for all emails
            'topicName': topic_name
        }
        
        print(f"Setting up Gmail watch...")
        print(f"Project: {GOOGLE_PROJECT_ID}")
        print(f"Topic: {topic_name}")
        
        # Start watching
        result = service.users().watch(userId='me', body=request_body).execute()
        
        print("\n✅ Gmail watch setup successful!")
        print(f"History ID: {result.get('historyId')}")
        print(f"Expiration: {result.get('expiration')}")
        
        # Save watch info for reference
        watch_info = {
            'historyId': result.get('historyId'),
            'expiration': result.get('expiration'),
            'topic': topic_name,
            'setup_timestamp': result.get('expiration', 'unknown')
        }
        
        with open('gmail_watch_info.json', 'w') as f:
            json.dump(watch_info, f, indent=2)
        
        print(f"Watch info saved to: gmail_watch_info.json")
        
        return result
        
    except Exception as e:
        print(f"❌ Error setting up Gmail watch: {e}")
        raise

def check_watch_status():
    """Check if Gmail watch is currently active."""
    try:
        creds = get_gmail_credentials()
        service = build('gmail', 'v1', credentials=creds)
        
        # Get current profile to check watch status
        profile = service.users().getProfile(userId='me').execute()
        
        print(f"Gmail account: {profile.get('emailAddress')}")
        print(f"Messages total: {profile.get('messagesTotal')}")
        print(f"Threads total: {profile.get('threadsTotal')}")
        
        # Check if watch info file exists
        if os.path.exists('gmail_watch_info.json'):
            with open('gmail_watch_info.json', 'r') as f:
                watch_info = json.load(f)
            
            print(f"\nLast watch setup:")
            print(f"History ID: {watch_info.get('historyId')}")
            print(f"Expiration: {watch_info.get('expiration')}")
            print(f"Topic: {watch_info.get('topic')}")
        else:
            print("\nNo previous watch setup found.")
        
    except Exception as e:
        print(f"❌ Error checking watch status: {e}")

def main():
    """Main function to set up Gmail watch."""
    print("🔧 Gmail Watch Setup for Trade Alert System")
    print("=" * 50)
    
    # Check environment configuration
    print(f"Project ID: {GOOGLE_PROJECT_ID}")
    print(f"Pub/Sub Topic: {PUBSUB_TOPIC}")
    print(f"Gmail Credentials: {GMAIL_CREDENTIALS_FILE}")
    print(f"Google Credentials: {GOOGLE_CREDENTIALS_FILE}")
    print()
    
    # Check current status first
    print("📊 Checking current Gmail watch status...")
    check_watch_status()
    print()
    
    # Ask user if they want to proceed
    response = input("Do you want to set up a new Gmail watch? (y/N): ")
    if response.lower() != 'y':
        print("Setup cancelled.")
        return
    
    # Set up the watch
    try:
        setup_gmail_watch()
        print("\n🎉 Setup complete! Your Gmail is now configured to send notifications to Pub/Sub.")
        print("\nNext steps:")
        print("1. Test the setup by sending an email to your Gmail")
        print("2. Check your Pub/Sub subscription for messages")
        print("3. Deploy your webhook endpoint to handle the messages")
        
    except Exception as e:
        print(f"\n❌ Setup failed: {e}")
        print("\nTroubleshooting tips:")
        print("1. Verify your Google Cloud project is set correctly")
        print("2. Ensure the Pub/Sub topic exists")
        print("3. Check that your credentials have the right permissions")
        print("4. Make sure Gmail API is enabled in your project")

if __name__ == "__main__":
    main()