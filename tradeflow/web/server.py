"""
FastAPI webhook server - Service Layer Architecture (v2)

Clean implementation replacing the monolithic server.py with proper
separation of concerns, dependency injection, and pipeline processing.
"""

import json
import logging
from datetime import datetime
from typing import Dict, Any, Optional

from fastapi import FastAPI, Request, HTTPException, BackgroundTasks, Depends
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
import uvicorn

from ..services import ServiceContainer, create_service_container
from ..pipeline import ProcessingPipeline, create_default_pipeline
from ..version import get_version
from ..config import HOST, PORT, DEBUG, ENVIRONMENT

# Configure logging
logging.basicConfig(
    level=logging.INFO if not DEBUG else logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Global service container (initialized on startup)
service_container: Optional[ServiceContainer] = None
processing_pipeline: Optional[ProcessingPipeline] = None


# Dependency injection for FastAPI
def get_service_container() -> ServiceContainer:
    """FastAPI dependency for service container"""
    if service_container is None:
        raise HTTPException(status_code=503, detail="Service container not initialized")
    return service_container


def get_processing_pipeline() -> ProcessingPipeline:
    """FastAPI dependency for processing pipeline"""
    if processing_pipeline is None:
        raise HTTPException(status_code=503, detail="Processing pipeline not initialized")
    return processing_pipeline


# Create FastAPI application
app = FastAPI(
    title="Trade Alert Webhook Server",
    description="Service layer architecture for processing Gmail Pub/Sub trade alerts",
    version=get_version()
)


@app.on_event("startup")
async def startup_event():
    """Application startup - initialize services"""
    global service_container, processing_pipeline
    
    logger.info(f"🚀 Starting Trade Alert Webhook Server - v{get_version()}")
    
    try:
        # Initialize service container
        service_container = create_service_container()
        logger.info("✅ Service container initialized")
        
        # Validate service health
        health_status = service_container.health_check()
        healthy_services = [name for name, status in health_status.items() if status]
        unhealthy_services = [name for name, status in health_status.items() if not status]
        
        logger.info(f"✅ Healthy services: {', '.join(healthy_services) if healthy_services else 'None'}")
        if unhealthy_services:
            logger.warning(f"⚠️ Unhealthy services: {', '.join(unhealthy_services)}")
        
        # Initialize processing pipeline
        processing_pipeline = create_default_pipeline(service_container)
        logger.info("✅ Processing pipeline initialized")
        
        logger.info("🎯 Server startup completed successfully")
        
    except Exception as e:
        logger.error(f"❌ Failed to initialize services: {e}")
        raise


@app.on_event("shutdown")
async def shutdown_event():
    """Application shutdown - cleanup resources"""
    global service_container, processing_pipeline
    
    logger.info("🛑 Shutting down Trade Alert Webhook Server")
    
    if service_container:
        service_container.shutdown()
        service_container = None
    
    processing_pipeline = None
    logger.info("✅ Shutdown completed")


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
        "architecture": "service_layer",
        "status": "running",
        "timestamp": datetime.utcnow().isoformat(),
        "endpoints": {
            "health": "/health",
            "status": "/status",
            "services": "/services",
            "gmail_webhook": "/webhook/gmail",
            "manual_trade": "/manual-trade",
            "api_docs": "/docs",
            "openapi": "/openapi.json"
        },
        "description": "Clean service layer architecture with dependency injection and pipeline processing"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "service": "trade-alert-webhook",
        "version": get_version(),
        "architecture": "service_layer"
    }


@app.get("/services")
async def service_status(container: ServiceContainer = Depends(get_service_container)):
    """Service status and health check endpoint"""
    health_status = container.health_check()
    service_info = container.get_service_info()
    
    return {
        "timestamp": datetime.utcnow().isoformat(),
        "service_container": {
            "registered_services": service_info['registered_services'],
            "active_services": service_info['active_services'],
            "health_status": health_status
        },
        "overall_health": all(health_status.values()) if health_status else False,
        "architecture": "service_layer",
        "notes": [
            "Service layer architecture with dependency injection",
            "Pipeline processing with discrete handlers",
            "Comprehensive health monitoring and error handling"
        ]
    }


async def process_trade_alert_pipeline(
    raw_data: Dict[str, Any],
    pipeline: ProcessingPipeline
) -> None:
    """
    Process trade alert using the new pipeline architecture
    
    Replaces the monolithic 200+ line process_trade_alert() function
    with clean pipeline processing.
    """
    try:
        logger.info("🔄 Processing trade alert with pipeline architecture")
        
        # Process through pipeline
        context = await pipeline.process(raw_data)
        
        # Log final result
        if context.is_successful():
            logger.info("✅ Trade alert processed successfully")
        else:
            logger.warning(f"⚠️ Trade alert processing completed with status: {context.processing_status}")
            if context.error_message:
                logger.warning(f"Error: {context.error_message}")
        
    except Exception as e:
        logger.error(f"❌ Pipeline processing failed: {e}")


@app.post("/webhook/gmail")
async def gmail_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    pipeline: ProcessingPipeline = Depends(get_processing_pipeline)
):
    """
    Gmail Pub/Sub webhook endpoint - Service Layer Architecture
    
    Clean implementation using dependency injection and pipeline processing
    """
    try:
        # Get request data
        data = await request.json()
        
        logger.info("📧 Received Gmail Pub/Sub notification")
        
        # Validate Pub/Sub message format
        if "message" not in data:
            raise HTTPException(status_code=400, detail="Invalid Pub/Sub message format")
        
        message = data["message"]
        message_id = message.get("messageId", "unknown")
        publish_time = message.get("publishTime", "unknown")
        
        logger.info(f"📨 Message ID: {message_id}, Published: {publish_time}")
        
        # Process with pipeline in background
        background_tasks.add_task(process_trade_alert_pipeline, data, pipeline)
        
        # Return success response to Pub/Sub
        return {
            "status": "success",
            "message": "Gmail notification received and queued for pipeline processing",
            "messageId": message_id,
            "timestamp": datetime.utcnow().isoformat(),
            "architecture": "service_layer"
        }
        
    except json.JSONDecodeError:
        logger.error("❌ Invalid JSON in request body")
        raise HTTPException(status_code=400, detail="Invalid JSON")
    
    except Exception as e:
        logger.error(f"❌ Error processing Gmail webhook: {e}")
        # Return 200 to acknowledge message and prevent retries for permanent failures
        return JSONResponse(
            status_code=200,
            content={
                "status": "error",
                "message": f"Processed with error: {str(e)}",
                "architecture": "service_layer"
            }
        )


@app.post("/manual-trade")
async def manual_trade(
    request: Request,
    background_tasks: BackgroundTasks,
    pipeline: ProcessingPipeline = Depends(get_processing_pipeline)
):
    """
    Manual trade submission endpoint for testing
    """
    try:
        data = await request.json()
        
        logger.info("🧪 Received manual trade request")
        
        # Create mock Pub/Sub message format
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
        
        # Process with pipeline
        background_tasks.add_task(process_trade_alert_pipeline, mock_pubsub_data, pipeline)
        
        return {
            "status": "success",
            "message": "Manual trade queued for pipeline processing",
            "timestamp": datetime.utcnow().isoformat(),
            "architecture": "service_layer"
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
            "timestamp": datetime.utcnow().isoformat(),
            "architecture": "service_layer"
        }
    )


@app.exception_handler(500)
async def internal_error_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal Server Error",
            "message": "An unexpected error occurred",
            "timestamp": datetime.utcnow().isoformat(),
            "architecture": "service_layer"
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