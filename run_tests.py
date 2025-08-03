#!/usr/bin/env python3
"""
Test runner for the trade alert system
"""

import sys
import os

# Add the current directory to Python path so we can import tradeflow
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

if __name__ == "__main__":
    # Import and run the Gmail Pub/Sub tests
    from tradeflow.tests.test_gmail_pubsub import (
        test_alert_model, 
        test_provider_registry, 
        test_pubsub_message_parsing
    )
    
    print("🚀 Running Trade Alert System Tests")
    print("=" * 50)
    
    test_alert_model()
    test_provider_registry()
    test_pubsub_message_parsing()
    
    print("\n🎉 All tests complete!")
    print("\n📋 Next Steps:")
    print("1. Set up Gmail API credentials")
    print("2. Configure Google Cloud Pub/Sub")
    print("3. Set up email filters/labels")
    print("4. Test with real email alerts")