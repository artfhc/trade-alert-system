#!/usr/bin/env python3
"""
Entry point for the trade alert system - Service Layer Architecture

This replaces the TODO-based placeholder with a clean implementation using
the new service layer architecture with dependency injection and pipeline processing.
"""

import sys
import os
import logging
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def main():
    """Main function - starts the service layer architecture server by default"""
    print("🚀 Trade Alert System - Service Layer Architecture")
    print("=" * 60)
    
    print("Starting server with new architecture...")
    print("  ✅ Dependency injection container")
    print("  ✅ Pipeline processing")
    print("  ✅ Service health monitoring") 
    print("  ✅ Clean separation of concerns")
    print()
    
    # Import and run the server
    from tradeflow.web.server import run_server
    run_server()

if __name__ == "__main__":
    main()