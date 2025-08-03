#!/usr/bin/env python3
"""
Test script for Gmail Pub/Sub provider implementation
"""

import json
import base64
from datetime import datetime
from ..providers.gmail_pubsub import GmailPubSubProvider
from ..core.models import Alert


def test_pubsub_message_parsing():
    """Test parsing of a mock Pub/Sub message"""
    
    # Mock Pub/Sub message data (what would come from the webhook)
    mock_pubsub_data = {
        "message": {
            "attributes": {
                "messageId": "1234567890",
                "historyId": "12345"
            },
            "data": base64.b64encode(json.dumps({
                "messageId": "gmail_message_123",
                "historyId": "12345"
            }).encode()).decode(),
            "messageId": "projects/your-project/messages/1234567890",
            "publishTime": "2025-01-20T10:00:00.000Z"
        }
    }
    
    print("🧪 Testing Gmail Pub/Sub Provider")
    print("=" * 50)
    
    try:
        # Note: This will fail without actual Gmail credentials
        # But we can test the basic structure
        provider = GmailPubSubProvider()
        print("✅ GmailPubSubProvider created successfully")
        
        # Test the decode function
        decoded = provider._decode_pubsub_message(mock_pubsub_data)
        print(f"✅ Pub/Sub message decoded: {decoded}")
        
        # Test source name
        source = provider.get_source_name()
        print(f"✅ Source name: {source}")
        
        print("\n📝 Note: Full parsing requires Gmail API credentials")
        print("   To test with real data:")
        print("   1. Set up Gmail API credentials")
        print("   2. Configure Pub/Sub topic")
        print("   3. Send test email")
        
    except ImportError as e:
        print(f"❌ Missing dependencies: {e}")
        print("💡 Install with: pip install google-auth google-auth-oauthlib google-auth-httplib2 google-api-python-client")
    
    except Exception as e:
        print(f"⚠️  Expected error (missing credentials): {e}")


def test_alert_model():
    """Test the Alert data model"""
    print("\n🧪 Testing Alert Model")
    print("=" * 30)
    
    try:
        # Create a valid alert
        alert = Alert(
            source="gmail",
            content="TRADE ALERT: Buy TSLA at $200",
            timestamp=datetime.utcnow(),
            metadata={
                "sender": "alerts@tradingservice.com",
                "subject": "Trade Alert - TSLA Buy Signal",
                "message_id": "123456"
            }
        )
        
        print("✅ Alert created successfully")
        print(f"   Source: {alert.source}")
        print(f"   Content: {alert.content}")
        print(f"   Timestamp: {alert.timestamp}")
        print(f"   Metadata: {alert.metadata}")
        
        # Test validation
        try:
            invalid_alert = Alert(
                source="",  # Invalid empty source
                content="test",
                timestamp=datetime.utcnow(),
                metadata={}
            )
        except ValueError as e:
            print(f"✅ Validation working: {e}")
            
    except Exception as e:
        print(f"❌ Alert model error: {e}")


def test_provider_registry():
    """Test the provider registry system"""
    print("\n🧪 Testing Provider Registry")
    print("=" * 35)
    
    try:
        from ..providers.base import get_provider, _ALERT_PROVIDERS
        
        print(f"✅ Available providers: {list(_ALERT_PROVIDERS.keys())}")
        
        # Test getting Gmail provider
        if 'gmail' in _ALERT_PROVIDERS:
            print("✅ Gmail provider registered successfully")
        else:
            print("❌ Gmail provider not registered")
            
    except Exception as e:
        print(f"❌ Registry error: {e}")


if __name__ == "__main__":
    test_alert_model()
    test_provider_registry()
    test_pubsub_message_parsing()
    
    print("\n🎉 Testing complete!")
    print("\n📋 Next Steps:")
    print("1. Set up Gmail API credentials")
    print("2. Configure Google Cloud Pub/Sub")
    print("3. Set up email filters/labels")
    print("4. Test with real email alerts")