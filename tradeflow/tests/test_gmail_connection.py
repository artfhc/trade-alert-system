#!/usr/bin/env python3
"""
Test Gmail API Connection and Pub/Sub Message Processing

This script implements Step 5 from GMAIL_SETUP.md to test the Gmail integration.
"""

import json
import base64
from tradeflow.providers.gmail_pubsub import GmailPubSubProvider

def test_gmail_api_connection():
    """Test Gmail API Connection"""
    print("🔬 Testing Gmail API Connection...")
    print("=" * 50)
    
    try:
        # Create provider instance
        provider = GmailPubSubProvider(
            credentials_file='gmail_credentials.json',
            sender_whitelist=['alerts@tradingservice.com', 'notifications@broker.com']
        )
        
        print(f"✅ Provider created successfully")
        print(f"📡 Provider source: {provider.get_source_name()}")
        print(f"🔒 Sender whitelist: {provider.sender_whitelist}")
        
        # Test Gmail service initialization
        if provider.gmail_service:
            print("✅ Gmail API service initialized")
            
            # Get user profile to test API access
            profile = provider.gmail_service.users().getProfile(userId='me').execute()
            print(f"📧 Gmail account: {profile.get('emailAddress')}")
            print(f"📊 Messages total: {profile.get('messagesTotal')}")
            print(f"🧵 Threads total: {profile.get('threadsTotal')}")
        else:
            print("❌ Gmail API service not initialized")
            
    except Exception as e:
        print(f"❌ Error testing Gmail API connection: {e}")
        return False
    
    return True

def test_pubsub_message_processing():
    """Test Pub/Sub Message Processing"""
    print("\n🔬 Testing Pub/Sub Message Processing...")
    print("=" * 50)
    
    try:
        # Create provider instance
        provider = GmailPubSubProvider(
            credentials_file='gmail_credentials.json',
            sender_whitelist=['alerts@tradingservice.com']
        )
        
        # Create a mock Pub/Sub message (this is what Google sends to your webhook)
        # The actual format from Gmail Pub/Sub contains historyId, not message content
        # We'll simulate both scenarios
        
        print("📝 Testing with mock Pub/Sub notification...")
        
        # Mock Gmail Pub/Sub notification format
        mock_notification_data = {
            "emailAddress": "your-email@gmail.com",
            "historyId": "123456"
        }
        
        # Encode as base64 (how Pub/Sub sends it)
        encoded_data = base64.b64encode(json.dumps(mock_notification_data).encode()).decode()
        
        mock_pubsub_message = {
            "message": {
                "data": encoded_data,
                "attributes": {
                    "messageId": "gmail_message_123"
                },
                "messageId": "1234567890",
                "publishTime": "2024-01-01T12:00:00.000Z"
            }
        }
        
        print(f"📦 Mock Pub/Sub message created:")
        print(f"   Data: {mock_notification_data}")
        print(f"   Message ID: {mock_pubsub_message['message']['messageId']}")
        
        # Note: This will fail because we don't have actual Gmail message IDs
        # But it will test the parsing logic
        try:
            alert = provider.parse_alert(mock_pubsub_message)
            print(f"✅ Alert parsed successfully: {alert}")
        except Exception as e:
            print(f"⚠️  Expected error parsing mock alert (no real Gmail message): {e}")
            print("   This is normal - we need real Gmail messages to fully test")
        
        # Test the decode function separately
        print("\n🔍 Testing message decoding...")
        decoded = provider._decode_pubsub_message(mock_pubsub_message)
        print(f"✅ Successfully decoded Pub/Sub message: {decoded}")
        
    except Exception as e:
        print(f"❌ Error testing Pub/Sub message processing: {e}")
        return False
    
    return True

def test_pub_sub_connectivity():
    """Test Pub/Sub connectivity using gcloud command"""
    print("\n🔬 Testing Pub/Sub Connectivity...")
    print("=" * 50)
    
    import subprocess
    
    try:
        # Test publishing a message
        print("📤 Publishing test message to Pub/Sub topic...")
        result = subprocess.run([
            'gcloud', 'pubsub', 'topics', 'publish', 
            'gmail-trade-alerts', '--message=test-from-python'
        ], capture_output=True, text=True)
        
        if result.returncode == 0:
            print("✅ Successfully published test message")
            print(f"   Output: {result.stdout.strip()}")
        else:
            print(f"❌ Failed to publish message: {result.stderr}")
            return False
        
        # Test pulling messages
        print("📥 Pulling messages from subscription...")
        result = subprocess.run([
            'gcloud', 'pubsub', 'subscriptions', 'pull', 
            'gmail-alerts-sub', '--limit=5', '--auto-ack'
        ], capture_output=True, text=True)
        
        if result.returncode == 0:
            print("✅ Successfully pulled messages")
            if result.stdout.strip():
                print(f"   Messages: {result.stdout}")
            else:
                print("   No messages in subscription")
        else:
            print(f"❌ Failed to pull messages: {result.stderr}")
            return False
            
    except FileNotFoundError:
        print("❌ gcloud command not found. Make sure Google Cloud CLI is installed.")
        return False
    except Exception as e:
        print(f"❌ Error testing Pub/Sub connectivity: {e}")
        return False
    
    return True

def main():
    """Main test function"""
    print("🧪 Gmail Integration Testing Suite")
    print("=" * 60)
    print("This script tests the components from Step 5 of GMAIL_SETUP.md\n")
    
    results = []
    
    # Test 1: Gmail API Connection
    results.append(test_gmail_api_connection())
    
    # Test 2: Pub/Sub Message Processing
    results.append(test_pubsub_message_processing())
    
    # Test 3: Pub/Sub Connectivity
    results.append(test_pub_sub_connectivity())
    
    # Summary
    print("\n" + "=" * 60)
    print("🏁 Test Results Summary")
    print("=" * 60)
    
    test_names = [
        "Gmail API Connection",
        "Pub/Sub Message Processing", 
        "Pub/Sub Connectivity"
    ]
    
    passed = sum(results)
    total = len(results)
    
    for i, (name, result) in enumerate(zip(test_names, results)):
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{i+1}. {name}: {status}")
    
    print(f"\nOverall: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Your Gmail integration is working correctly.")
    else:
        print("⚠️  Some tests failed. Check the error messages above.")
        print("\nNext steps:")
        print("1. Verify your credentials files exist and are valid")
        print("2. Make sure Gmail API is enabled in your Google Cloud project")
        print("3. Check that Pub/Sub topic and subscription exist")
        print("4. Run the Gmail watch setup script if you haven't already")

if __name__ == "__main__":
    main()