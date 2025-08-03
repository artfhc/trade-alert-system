"""
FastAPI webhook server for handling Gmail Pub/Sub notifications
"""

import json
import logging
import asyncio
from datetime import datetime
from typing import Dict, Any, Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
import uvicorn

from ..providers.gmail_pubsub import GmailPubSubProvider
from ..config import (
    HOST, PORT, DEBUG, ENVIRONMENT,
    GMAIL_CREDENTIALS_FILE, GMAIL_SENDER_WHITELIST,
    WEBHOOK_SECRET
)

# Configure logging
logging.basicConfig(
    level=logging.INFO if not DEBUG else logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Global variables for providers
gmail_provider: Optional[GmailPubSubProvider] = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    # Startup
    logger.info("🚀 Starting Trade Alert Webhook Server")
    global gmail_provider
    
    try:
        # Initialize Gmail provider
        gmail_provider = GmailPubSubProvider(
            credentials_file=GMAIL_CREDENTIALS_FILE,
            sender_whitelist=GMAIL_SENDER_WHITELIST
        )
        logger.info("✅ Gmail provider initialized")
        logger.info("⚠️  Trade flow orchestrator not implemented yet - will log alerts only")
        
    except Exception as e:
        logger.error(f"❌ Failed to initialize services: {e}")
        raise
    
    yield
    
    # Shutdown
    logger.info("🛑 Shutting down Trade Alert Webhook Server")

# Create FastAPI application
app = FastAPI(
    title="Trade Alert Webhook Server",
    description="Webhook server for processing Gmail Pub/Sub trade alerts",
    version="1.0.0",
    lifespan=lifespan
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if DEBUG else [],
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

# Add trusted host middleware for production
if ENVIRONMENT == "production":
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=["*"])

# Request logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = datetime.utcnow()
    
    # Log request
    logger.info(f"📥 {request.method} {request.url.path} from {request.client.host}")
    
    response = await call_next(request)
    
    # Log response
    process_time = (datetime.utcnow() - start_time).total_seconds()
    logger.info(f"📤 {request.method} {request.url.path} -> {response.status_code} ({process_time:.3f}s)")
    
    return response

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "service": "trade-alert-webhook",
        "version": "1.0.0"
    }

@app.get("/status")
async def system_status():
    """System status endpoint"""
    gmail_status = "connected" if gmail_provider and gmail_provider.gmail_service else "disconnected"
    
    return {
        "status": "running",
        "timestamp": datetime.utcnow().isoformat(),
        "services": {
            "gmail_provider": gmail_status,
            "trade_flow": "not_implemented"
        },
        "environment": ENVIRONMENT,
        "debug": DEBUG
    }

async def process_trade_alert(alert_data: Dict[str, Any]):
    """Background task to process trade alert"""
    try:
        logger.info("🔄 Processing trade alert in background")
        
        if not gmail_provider:
            raise ValueError("Gmail provider not initialized")
        
        # Parse the alert
        alert = gmail_provider.parse_alert(alert_data)
        logger.info(f"✅ Alert parsed: {alert.content[:100]}...")
        
        # TODO: Process with trade flow (not implemented yet)
        logger.info("📝 Alert received and parsed successfully")
        logger.info(f"📧 From: {alert.metadata.get('sender', 'unknown')}")
        logger.info(f"📃 Subject: {alert.metadata.get('subject', 'unknown')}")
        logger.warning("⚠️ Trade flow not implemented yet - alert logged only")
        
    except Exception as e:
        logger.error(f"❌ Error processing trade alert: {e}")

@app.post("/webhook/gmail")
async def gmail_webhook(request: Request, background_tasks: BackgroundTasks):
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
        
        # Validate that we have required components
        if not gmail_provider:
            logger.error("❌ Gmail provider not initialized")
            raise HTTPException(status_code=500, detail="Gmail provider not initialized")
        
        # Add to background processing queue
        background_tasks.add_task(process_trade_alert, data)
        
        # Return success response to Pub/Sub
        return {
            "status": "success",
            "message": "Gmail notification received and queued for processing",
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
async def manual_trade(request: Request, background_tasks: BackgroundTasks):
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
        
        # Process as background task
        background_tasks.add_task(process_trade_alert, mock_pubsub_data)
        
        return {
            "status": "success", 
            "message": "Manual trade queued for processing",
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

def run_server():
    """Run the webhook server"""
    logger.info(f"🌐 Starting webhook server on {HOST}:{PORT}")
    uvicorn.run(
        "tradeflow.web.server:app",
        host=HOST,
        port=PORT,
        reload=DEBUG,
        log_level="info" if not DEBUG else "debug"
    )

if __name__ == "__main__":
    run_server()