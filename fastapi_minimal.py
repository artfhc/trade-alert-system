#!/usr/bin/env python3
"""
Minimal FastAPI webhook server for Gmail Pub/Sub notifications
Compatible with Python 3.13 and latest FastAPI/Pydantic versions
"""

import os
import json
import logging
from datetime import datetime
from typing import Dict, Any

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
import uvicorn

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Create FastAPI application
app = FastAPI(
    title="Trade Alert Webhook Server",
    description="Webhook server for processing Gmail Pub/Sub trade alerts",
    version="1.0.0"
)

@app.get("/")
async def root():
    return {
        "message": "Trade Alert Webhook Server is running!",
        "status": "ok",
        "timestamp": datetime.utcnow().isoformat()
    }

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "service": "trade-alert-webhook",
        "version": "1.0.0"
    }

@app.get("/status")
async def system_status():
    return {
        "status": "running",
        "timestamp": datetime.utcnow().isoformat(),
        "services": {
            "gmail_provider": "not_implemented",
            "trade_flow": "not_implemented"
        },
        "environment": os.environ.get("ENVIRONMENT", "development"),
        "debug": os.environ.get("DEBUG", "false").lower() == "true",
        "python_version": os.sys.version,
        "port": os.environ.get("PORT", "8000")
    }

@app.post("/webhook/gmail")
async def gmail_webhook(request: Request):
    """
    Gmail Pub/Sub webhook endpoint
    
    This endpoint receives push notifications from Google Cloud Pub/Sub
    when new emails arrive in the monitored Gmail account.
    """
    try:
        # Get request data
        data = await request.json()
        
        logger.info("📧 Received Gmail Pub/Sub notification")
        logger.debug(f"Pub/Sub data: {json.dumps(data, indent=2)}")
        
        # Validate Pub/Sub message format
        if "message" not in data:
            raise HTTPException(status_code=400, detail="Invalid Pub/Sub message format")
        
        message = data["message"]
        
        # Extract message attributes for logging
        message_id = message.get("messageId", "unknown")
        publish_time = message.get("publishTime", "unknown")
        
        logger.info(f"📨 Message ID: {message_id}, Published: {publish_time}")
        
        # TODO: Process the alert when Gmail provider is implemented
        logger.info("⚠️ Alert processing not implemented yet - logging only")
        
        # Return success response to Pub/Sub
        return {
            "status": "success",
            "message": "Gmail notification received and logged",
            "messageId": message_id,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except json.JSONDecodeError:
        logger.error("❌ Invalid JSON in request body")
        raise HTTPException(status_code=400, detail="Invalid JSON")
    
    except Exception as e:
        logger.error(f"❌ Error processing Gmail webhook: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.post("/manual-trade")
async def manual_trade(request: Request):
    """
    Manual trade submission endpoint for testing
    """
    try:
        data = await request.json()
        
        logger.info("🧪 Received manual trade request")
        
        # Create a mock Pub/Sub message format
        mock_pubsub_data = {
            "message": {
                "data": data.get("data", ""),
                "attributes": {
                    "messageId": f"manual_{datetime.utcnow().timestamp()}"
                },
                "messageId": f"manual_{datetime.utcnow().timestamp()}",
                "publishTime": datetime.utcnow().isoformat()
            }
        }
        
        logger.info(f"📝 Mock message created: {mock_pubsub_data}")
        
        return {
            "status": "success", 
            "message": "Manual trade logged (processing not implemented yet)",
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"❌ Error processing manual trade: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.exception_handler(404)
async def not_found_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=404,
        content={
            "error": "Not Found",
            "message": f"Endpoint {request.url.path} not found",
            "timestamp": datetime.utcnow().isoformat()
        }
    )

@app.exception_handler(500)
async def internal_error_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal Server Error",
            "message": "An unexpected error occurred",
            "timestamp": datetime.utcnow().isoformat()
        }
    )

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    host = os.environ.get("HOST", "0.0.0.0")
    debug = os.environ.get("DEBUG", "false").lower() == "true"
    
    logger.info(f"🚀 Starting FastAPI webhook server on {host}:{port}")
    logger.info(f"🔍 Debug mode: {debug}")
    
    uvicorn.run(
        app,
        host=host,
        port=port,
        reload=debug,
        log_level="info" if not debug else "debug"
    )