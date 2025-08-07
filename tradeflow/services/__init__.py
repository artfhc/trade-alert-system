"""
Service layer for trade alert processing

This module provides the service layer architecture with dependency injection,
replacing the monolithic global state approach with clean service management.
"""

from .container import ServiceContainer
from .config import ServiceConfig
from .factories import create_service_container

__all__ = [
    'ServiceContainer',
    'ServiceConfig', 
    'create_service_container'
]