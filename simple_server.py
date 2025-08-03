#!/usr/bin/env python3
"""
Simple test server to verify Render deployment works
"""

import os
from fastapi import FastAPI
import uvicorn

app = FastAPI(title="Trade Alert Test Server")

@app.get("/")
def read_root():
    return {"message": "Trade Alert Server is running!", "status": "ok"}

@app.get("/health")
def health():
    return {"status": "healthy"}

@app.get("/test")
def test():
    return {
        "message": "Test endpoint working",
        "python_version": os.sys.version,
        "environment": os.environ.get("ENVIRONMENT", "unknown")
    }

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)