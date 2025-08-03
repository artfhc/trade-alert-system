#!/usr/bin/env python3
"""
Trade Alert Webhook Server Startup Script

This script starts the FastAPI webhook server that handles Gmail Pub/Sub notifications.
"""

import sys
import os
import logging
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from tradeflow.web.server import run_server
from tradeflow.config import validate_config, HOST, PORT, DEBUG, ENVIRONMENT

def main():
    """Main function to start the webhook server"""
    print("🚀 Trade Alert Webhook Server")
    print("=" * 50)
    
    try:
        # Validate configuration
        print("🔧 Validating configuration...")
        validate_config()
        print("✅ Configuration valid")
        
        print(f"🌐 Server will start on: http://{HOST}:{PORT}")
        print(f"🔍 Environment: {ENVIRONMENT}")
        print(f"🐛 Debug mode: {DEBUG}")
        print()
        
        print("📋 Available endpoints:")
        print(f"  • GET  /health       - Health check")
        print(f"  • GET  /status       - System status")
        print(f"  • POST /webhook/gmail - Gmail Pub/Sub webhook")
        print(f"  • POST /manual-trade  - Manual trade testing")
        print()
        
        if DEBUG:
            print("🔍 Debug mode enabled - server will auto-reload on code changes")
            print("📖 API docs available at: http://localhost:8000/docs")
            print()
        
        print("🎯 Ready to receive Gmail notifications!")
        print("📧 Make sure your Gmail watch is set up and Pub/Sub is configured")
        print()
        print("Press Ctrl+C to stop the server")
        print("=" * 50)
        
        # Start the server
        run_server()
        
    except KeyboardInterrupt:
        print("\n🛑 Server stopped by user")
    except Exception as e:
        print(f"❌ Failed to start server: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()