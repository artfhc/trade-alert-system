"""
FastAPI webhook server for handling Gmail Pub/Sub notifications
"""

import json
import logging
import asyncio
from datetime import datetime
from typing import Dict, Any, Optional

from fastapi import FastAPI, Request, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
import uvicorn

from ..providers.gmail_pubsub import GmailPubSubProvider
from ..logging.google_sheets import GoogleSheetsLogger, LLMParsingLogger
from ..parsers.email_llm import EmailLLMParser
from ..version import get_version
from ..config import (
    HOST, PORT, DEBUG, ENVIRONMENT,
    GMAIL_CREDENTIALS_FILE, GMAIL_TOKEN_FILE, GMAIL_SENDER_WHITELIST,
    WEBHOOK_SECRET, GOOGLE_CREDENTIALS_FILE, GOOGLE_SHEETS_DOC_ID, 
    GOOGLE_SHEETS_WORKSHEET, GOOGLE_SHEETS_LLM_WORKSHEET
)

# Configure logging
logging.basicConfig(
    level=logging.INFO if not DEBUG else logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Global variables for providers
gmail_provider: Optional[GmailPubSubProvider] = None
sheets_logger: Optional[GoogleSheetsLogger] = None
llm_logger: Optional[LLMParsingLogger] = None
email_parser: Optional[EmailLLMParser] = None

# Create FastAPI application
app = FastAPI(
    title="Trade Alert Webhook Server",
    description="Webhook server for processing Gmail Pub/Sub trade alerts",
    version="1.0.0"
)

@app.on_event("startup")
async def startup_event():
    """Application startup event"""
    logger.info(f"🚀 Starting Trade Alert Webhook Server v{get_version()}")
    global gmail_provider, sheets_logger, llm_logger, email_parser
    
    try:
        # Initialize Gmail provider
        gmail_provider = GmailPubSubProvider(
            credentials_file=GMAIL_CREDENTIALS_FILE,
            token_file=GMAIL_TOKEN_FILE,
            sender_whitelist=GMAIL_SENDER_WHITELIST
        )
        logger.info("✅ Gmail provider initialized")
        
        # Initialize Google Sheets logger
        sheets_logger = GoogleSheetsLogger(
            credentials_file=GOOGLE_CREDENTIALS_FILE,
            spreadsheet_id=GOOGLE_SHEETS_DOC_ID,
            worksheet_name=GOOGLE_SHEETS_WORKSHEET
        )
        logger.info("✅ Google Sheets logger initialized")
        
        # Initialize LLM Parsing logger
        llm_logger = LLMParsingLogger(
            credentials_file=GOOGLE_CREDENTIALS_FILE,
            spreadsheet_id=GOOGLE_SHEETS_DOC_ID,
            worksheet_name=GOOGLE_SHEETS_LLM_WORKSHEET
        )
        logger.info("✅ LLM Parsing logger initialized")
        
        # Initialize Email LLM Parser
        try:
            email_parser = EmailLLMParser()
            logger.info("✅ Email LLM Parser initialized")
        except Exception as parser_error:
            logger.warning(f"⚠️ Email LLM Parser initialization failed: {parser_error}")
            logger.warning("📝 Emails will be processed without LLM parsing")
            email_parser = None
        
        logger.info("⚠️  Trade flow orchestrator not implemented yet - will log alerts with LLM parsing")
        
    except Exception as e:
        logger.error(f"❌ Failed to initialize services: {e}")
        raise

@app.on_event("shutdown")
async def shutdown_event():
    """Application shutdown event"""
    logger.info("🛑 Shutting down Trade Alert Webhook Server")

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

@app.get("/")
async def root():
    """Root endpoint with API information"""
    return {
        "service": "Trade Alert Webhook Server",
        "version": get_version(),
        "status": "running",
        "timestamp": datetime.utcnow().isoformat(),
        "endpoints": {
            "health": "/health",
            "status": "/status", 
            "gmail_webhook": "/webhook/gmail",
            "manual_trade": "/manual-trade",
            "api_docs": "/docs",
            "openapi": "/openapi.json"
        },
        "description": "Automated trading system webhook for Gmail Pub/Sub notifications"
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "service": "trade-alert-webhook",
        "version": get_version()
    }

@app.get("/status")
async def system_status():
    """System status endpoint"""
    gmail_status = "connected" if gmail_provider and gmail_provider.gmail_service else "disconnected"
    gmail_auth_note = ""
    
    if gmail_provider and not gmail_provider.gmail_service:
        gmail_auth_note = "Gmail authentication required for full functionality"
    
    # Check Email LLM Parser status
    llm_parser_status = "available" if email_parser else "not_available"
    llm_parser_note = ""
    
    if not email_parser:
        llm_parser_note = "Email LLM Parser not initialized - requires OPENAI_API_KEY or ANTHROPIC_API_KEY"
    else:
        # Check which LLM clients are available
        clients = []
        if hasattr(email_parser, 'openai_client') and email_parser.openai_client:
            clients.append("OpenAI")
        if hasattr(email_parser, 'anthropic_client') and email_parser.anthropic_client:
            clients.append("Anthropic")
        
        if clients:
            llm_parser_note = f"Available LLM clients: {', '.join(clients)}"
        else:
            llm_parser_note = "No LLM clients available"
    
    return {
        "status": "running",
        "timestamp": datetime.utcnow().isoformat(),
        "services": {
            "gmail_provider": gmail_status,
            "gmail_note": gmail_auth_note,
            "email_llm_parser": llm_parser_status,
            "llm_parser_note": llm_parser_note,
            "trade_flow": "not_implemented"
        },
        "environment": ENVIRONMENT,
        "debug": DEBUG,
        "notes": [
            "Webhook server is running and can receive Pub/Sub notifications",
            "Gmail authentication is optional for basic webhook functionality",
            "Email LLM Parser provides intelligent trade alert classification",
            "Trade flow orchestrator not implemented yet"
        ]
    }

async def process_trade_alert(alert_data: Dict[str, Any]):
    """Background task to process trade alert"""
    alert = None
    whitelist_status = "unknown"
    
    try:
        logger.info("🔄 Processing trade alert in background")
        
        if not gmail_provider:
            if sheets_logger:
                sheets_logger.log_email_alert(
                    alert=None,
                    raw_data=alert_data,
                    whitelist_status="unknown",
                    processing_status="error",
                    error_message="Gmail provider not initialized in background task"
                )
            raise ValueError("Gmail provider not initialized")
        
        # Parse the alert
        alert = gmail_provider.parse_alert(alert_data)
        logger.info(f"✅ Alert parsed: {alert.content[:100]}...")
        
        # Determine whitelist status
        sender = alert.metadata.get('sender', '')
        if not GMAIL_SENDER_WHITELIST:
            whitelist_status = "no_whitelist"
        elif gmail_provider.validate_sender(sender):
            whitelist_status = "allowed"
        else:
            whitelist_status = "blocked"
        
        # Log the parsed alert with whitelist status
        if sheets_logger:
            sheets_logger.log_email_alert(
                alert=alert,
                raw_data=alert_data,
                whitelist_status=whitelist_status,
                processing_status="parsed",
                error_message=None
            )
        
        # Check if sender is whitelisted (if whitelist is configured)
        if whitelist_status == "blocked":
            logger.warning(f"🚫 Sender {sender} not in whitelist - skipping processing")
            if sheets_logger:
                sheets_logger.log_email_alert(
                    alert=alert,
                    raw_data=alert_data,
                    whitelist_status=whitelist_status,
                    processing_status="blocked",
                    error_message=f"Sender '{sender}' not in configured whitelist"
                )
            return
        
        # Process with Email LLM Parser
        llm_parse_result = None
        llm_error = None
        llm_provider = "none"
        processing_time_ms = 0
        
        if email_parser:
            try:
                logger.info("🧠 Processing email with LLM Parser")
                
                # Track processing time
                import time
                start_time = time.time()
                
                llm_parse_result = email_parser.parse_email(alert.content)
                
                # Calculate processing time
                processing_time_ms = (time.time() - start_time) * 1000
                
                # Determine which LLM provider was used
                if llm_parse_result.raw_response:
                    if hasattr(email_parser, 'anthropic_client') and email_parser.anthropic_client:
                        llm_provider = "Anthropic"
                    elif hasattr(email_parser, 'openai_client') and email_parser.openai_client:
                        llm_provider = "OpenAI"
                else:
                    llm_provider = "failed"
                
                if llm_parse_result.error:
                    llm_error = f"LLM parsing failed: {llm_parse_result.error}"
                    logger.error(f"❌ {llm_error}")
                else:
                    logger.info(f"✅ LLM Classification: {'Trading Alert' if llm_parse_result.is_trading_alert else 'Non-Trading Email'}")
                    logger.info(f"⏱️  Processing Time: {processing_time_ms:.1f}ms with {llm_provider}")
                    
                    if llm_parse_result.is_trading_alert and llm_parse_result.trades:
                        logger.info(f"📈 Found {len(llm_parse_result.trades)} trade(s):")
                        for i, trade in enumerate(llm_parse_result.trades, 1):
                            logger.info(f"  {i}. {trade['ticker']}: {trade['action']}")
                            if trade.get('price'):
                                logger.info(f"     Price: ${trade['price']}")
                            if trade.get('target_allocation'):
                                logger.info(f"     Target Allocation: {trade['target_allocation']}")
                    else:
                        logger.info("📧 Email classified as non-trading content")
                
                # Log LLM parsing result to dedicated worksheet
                if llm_logger:
                    llm_logger.log_llm_parsing_result(
                        alert=alert,
                        llm_parse_result=llm_parse_result,
                        llm_provider=llm_provider,
                        processing_time_ms=processing_time_ms,
                        error_message=llm_error
                    )
                        
            except Exception as e:
                llm_error = f"LLM parsing exception: {str(e)}"
                logger.error(f"❌ {llm_error}")
                
                # Log the exception to LLM logger
                if llm_logger:
                    llm_logger.log_llm_parsing_result(
                        alert=alert,
                        llm_parse_result=None,
                        llm_provider="error",
                        processing_time_ms=processing_time_ms,
                        error_message=llm_error
                    )
        else:
            llm_error = "Email LLM Parser not available"
            logger.warning("⚠️ Email LLM Parser not initialized - skipping LLM processing")
            
            # Log that LLM parser is not available
            if llm_logger:
                llm_logger.log_llm_parsing_result(
                    alert=alert,
                    llm_parse_result=None,
                    llm_provider="not_available",
                    processing_time_ms=0,
                    error_message=llm_error
                )
        
        # TODO: Process with trade flow orchestrator (not implemented yet)
        logger.info("📝 Alert received and parsed successfully")
        logger.info(f"📧 From: {alert.metadata.get('sender', 'unknown')}")
        logger.info(f"📃 Subject: {alert.metadata.get('subject', 'unknown')}")
        logger.info(f"🔒 Whitelist Status: {whitelist_status}")
        logger.warning("⚠️ Trade flow orchestrator not implemented yet - alert logged only")
        
        # Determine processing status and error message
        if llm_error:
            processing_status = "llm_error"
            error_message = llm_error
        elif llm_parse_result and llm_parse_result.is_trading_alert:
            processing_status = "parsed_trading_alert"
            error_message = "Trade flow orchestrator not implemented yet"
        elif llm_parse_result:
            processing_status = "parsed_non_trading"
            error_message = "Non-trading email - no action required"
        else:
            processing_status = "processing"
            error_message = "Trade flow not implemented yet"
        
        # Log successful processing with LLM results
        if sheets_logger:
            # Add LLM parsing results to alert metadata for logging
            enhanced_metadata = alert.metadata.copy()
            if llm_parse_result:
                enhanced_metadata.update({
                    'llm_is_trading_alert': llm_parse_result.is_trading_alert,
                    'llm_trades_count': len(llm_parse_result.trades) if llm_parse_result.trades else 0,
                    'llm_raw_response': llm_parse_result.raw_response[:500] if llm_parse_result.raw_response else None  # Truncate for logging
                })
                if llm_parse_result.trades:
                    enhanced_metadata['llm_tickers'] = [trade['ticker'] for trade in llm_parse_result.trades]
                    enhanced_metadata['llm_actions'] = [trade['action'] for trade in llm_parse_result.trades]
            
            # Create enhanced alert object with LLM metadata
            from ..core.models import Alert
            enhanced_alert = Alert(
                source=alert.source,
                content=alert.content,
                timestamp=alert.timestamp,
                metadata=enhanced_metadata
            )
            
            sheets_logger.log_email_alert(
                alert=enhanced_alert,
                raw_data=alert_data,
                whitelist_status=whitelist_status,
                processing_status=processing_status,
                error_message=error_message
            )
        
    except Exception as e:
        error_msg = f"Error processing trade alert: {e}"
        logger.error(f"❌ {error_msg}")
        
        # Log the error
        if sheets_logger:
            sheets_logger.log_email_alert(
                alert=alert,
                raw_data=alert_data,
                whitelist_status=whitelist_status,
                processing_status="error",
                error_message=error_msg
            )

@app.post("/webhook/gmail")
async def gmail_webhook(request: Request, background_tasks: BackgroundTasks):
    """
    Gmail Pub/Sub webhook endpoint
    
    This endpoint receives push notifications from Google Cloud Pub/Sub
    when new emails arrive in the monitored Gmail account.
    """
    data = None
    message_id = "unknown"
    
    try:
        # Get request data
        data = await request.json()
        
        logger.info("📧 Received Gmail Pub/Sub notification")
        logger.info(f"Pub/Sub data: {json.dumps(data, indent=2)}")
        
        # Validate Pub/Sub message format
        if "message" not in data:
            # Log the failed message immediately
            if sheets_logger:
                sheets_logger.log_email_alert(
                    alert=None,
                    raw_data=data,
                    whitelist_status="unknown",
                    processing_status="error",
                    error_message="Invalid Pub/Sub message format"
                )
            raise HTTPException(status_code=400, detail="Invalid Pub/Sub message format")
        
        message = data["message"]
        message_id = message.get("messageId", "unknown")
        publish_time = message.get("publishTime", "unknown")
        
        logger.info(f"📨 Message ID: {message_id}, Published: {publish_time}")
        
        # LOG IMMEDIATELY - This ensures we capture every message regardless of processing outcome
        if sheets_logger:
            sheets_logger.log_email_alert(
                alert=None,
                raw_data=data,
                whitelist_status="pending_validation",
                processing_status="received",
                error_message=None
            )
        
        # Validate that we have required components
        if not gmail_provider:
            if sheets_logger:
                sheets_logger.log_email_alert(
                    alert=None,
                    raw_data=data,
                    whitelist_status="unknown",
                    processing_status="error",
                    error_message="Gmail provider not initialized"
                )
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
        # Log JSON decode error
        if sheets_logger:
            sheets_logger.log_email_alert(
                alert=None,
                raw_data={"error": "Invalid JSON in request body"},
                whitelist_status="unknown",
                processing_status="error", 
                error_message="Invalid JSON in request body"
            )
        logger.error("❌ Invalid JSON in request body")
        raise HTTPException(status_code=400, detail="Invalid JSON")
    
    except Exception as e:
        # Log any other errors
        if sheets_logger:
            sheets_logger.log_email_alert(
                alert=None,
                raw_data=data or {"error": "No data available"},
                whitelist_status="unknown",
                processing_status="error",
                error_message=str(e)
            )
        logger.error(f"❌ Error processing Gmail webhook: {e}")
        # Return 200 to acknowledge message and prevent retries for permanent failures
        # Only return 500 for truly retryable errors (network issues, temporary failures)
        return JSONResponse(
            status_code=200, 
            content={"status": "error", "message": f"Processed with error: {str(e)}"}
        )

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