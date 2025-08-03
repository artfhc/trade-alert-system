#!/usr/bin/env python3
"""
Flask-based webhook server for Gmail Pub/Sub notifications
Compatible with all Python versions on Render
"""

import os
import json
import logging
from datetime import datetime
from flask import Flask, request, jsonify

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Create Flask app
app = Flask(__name__)

@app.route('/')
def home():
    return jsonify({
        "message": "Trade Alert Webhook Server is running!",
        "status": "ok",
        "timestamp": datetime.utcnow().isoformat()
    })

@app.route('/health')
def health():
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "service": "trade-alert-webhook",
        "version": "1.0.0"
    })

@app.route('/status')
def status():
    return jsonify({
        "status": "running",
        "timestamp": datetime.utcnow().isoformat(),
        "services": {
            "gmail_provider": "not_implemented",
            "trade_flow": "not_implemented"
        },
        "environment": os.environ.get("ENVIRONMENT", "development"),
        "python_version": os.sys.version,
        "port": os.environ.get("PORT", "8000")
    })

@app.route('/webhook/gmail', methods=['POST'])
def gmail_webhook():
    """Gmail Pub/Sub webhook endpoint"""
    try:
        # Get request data
        data = request.get_json()
        
        logger.info("📧 Received Gmail Pub/Sub notification")
        
        if not data or "message" not in data:
            logger.error("❌ Invalid Pub/Sub message format")
            return jsonify({"error": "Invalid Pub/Sub message format"}), 400
        
        message = data["message"]
        message_id = message.get("messageId", "unknown")
        publish_time = message.get("publishTime", "unknown")
        
        logger.info(f"📨 Message ID: {message_id}, Published: {publish_time}")
        
        # TODO: Process the alert when Gmail provider is implemented
        logger.info("⚠️ Alert processing not implemented yet - logging only")
        
        # Return success response to Pub/Sub
        return jsonify({
            "status": "success",
            "message": "Gmail notification received and logged",
            "messageId": message_id,
            "timestamp": datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        logger.error(f"❌ Error processing Gmail webhook: {e}")
        return jsonify({"error": f"Internal server error: {str(e)}"}), 500

@app.route('/manual-trade', methods=['POST'])
def manual_trade():
    """Manual trade submission endpoint for testing"""
    try:
        data = request.get_json()
        logger.info("🧪 Received manual trade request")
        
        # Create mock Pub/Sub message format
        mock_message = {
            "message": {
                "data": data.get("data", ""),
                "messageId": f"manual_{datetime.utcnow().timestamp()}",
                "publishTime": datetime.utcnow().isoformat()
            }
        }
        
        logger.info(f"📝 Mock message created: {mock_message}")
        
        return jsonify({
            "status": "success",
            "message": "Manual trade logged (processing not implemented yet)",
            "timestamp": datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        logger.error(f"❌ Error processing manual trade: {e}")
        return jsonify({"error": str(e)}), 500

@app.errorhandler(404)
def not_found(error):
    return jsonify({
        "error": "Not Found",
        "message": f"Endpoint not found",
        "timestamp": datetime.utcnow().isoformat()
    }), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({
        "error": "Internal Server Error",
        "message": "An unexpected error occurred",
        "timestamp": datetime.utcnow().isoformat()
    }), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8000))
    debug = os.environ.get('DEBUG', 'false').lower() == 'true'
    
    logger.info(f"🚀 Starting Flask webhook server on port {port}")
    logger.info(f"🔍 Debug mode: {debug}")
    
    app.run(host='0.0.0.0', port=port, debug=debug)