"""
Dependency injection container for service layer architecture

Replaces global state with clean service management, lazy initialization,
and support for easy testing through service mocking.
"""

import logging
from typing import Dict, Any, Callable, Optional, TypeVar, Type
from threading import Lock

from .config import ServiceConfig

T = TypeVar('T')

logger = logging.getLogger(__name__)


class ServiceContainer:
    """
    Dependency injection container for managing service lifecycles
    
    Features:
    - Lazy initialization: Services created only when first requested
    - Factory pattern: Support for service factory functions
    - Health checking: Validate service health before returning
    - Thread-safe: Safe for concurrent access
    - Mocking support: Easy service replacement for testing
    """
    
    def __init__(self, config: ServiceConfig):
        self.config = config
        self._services: Dict[str, Any] = {}
        self._factories: Dict[str, Callable[[ServiceConfig], Any]] = {}
        self._lock = Lock()
        logger.info("ServiceContainer initialized")
    
    def register_factory(self, service_name: str, factory: Callable[[ServiceConfig], Any]) -> None:
        """Register a factory function for creating a service"""
        with self._lock:
            self._factories[service_name] = factory
            logger.debug(f"Registered factory for service: {service_name}")
    
    def register_singleton(self, service_name: str, instance: Any) -> None:
        """Register a pre-created service instance"""
        with self._lock:
            self._services[service_name] = instance
            logger.debug(f"Registered singleton for service: {service_name}")
    
    def get(self, service_name: str) -> Any:
        """
        Get a service instance, creating it if necessary
        
        Args:
            service_name: Name of the service to retrieve
            
        Returns:
            Service instance
            
        Raises:
            KeyError: If service is not registered
            RuntimeError: If service creation fails
        """
        with self._lock:
            # Return existing instance if available
            if service_name in self._services:
                service = self._services[service_name]
                if self._is_service_healthy(service):
                    return service
                else:
                    # Service unhealthy, recreate it
                    logger.warning(f"Service {service_name} is unhealthy, recreating...")
                    del self._services[service_name]
            
            # Create new instance using factory
            if service_name not in self._factories:
                available_services = list(self._factories.keys())
                raise KeyError(f"Service '{service_name}' not registered. Available: {available_services}")
            
            try:
                logger.info(f"Creating service: {service_name}")
                factory = self._factories[service_name]
                service = factory(self.config)
                
                # Health check new service
                if not self._is_service_healthy(service):
                    raise RuntimeError(f"Service {service_name} failed health check after creation")
                
                self._services[service_name] = service
                logger.info(f"Successfully created service: {service_name}")
                return service
                
            except Exception as e:
                logger.error(f"Failed to create service {service_name}: {e}")
                raise RuntimeError(f"Service creation failed for {service_name}: {e}")
    
    def get_optional(self, service_name: str) -> Optional[Any]:
        """
        Get a service instance, returning None if not available or creation fails
        
        Useful for optional services that may not be configured
        """
        logger.info(f"🔍 [ServiceContainer] Attempting to get optional service: {service_name}")
        try:
            service = self.get(service_name)
            logger.info(f"✅ [ServiceContainer] Successfully got service: {service_name}")
            return service
        except (KeyError, RuntimeError) as e:
            logger.info(f"⚠️ [ServiceContainer] Optional service {service_name} not available: {e}")
            return None
    
    def is_registered(self, service_name: str) -> bool:
        """Check if a service is registered (has a factory)"""
        return service_name in self._factories
    
    def is_available(self, service_name: str) -> bool:
        """Check if a service is available and healthy"""
        try:
            service = self.get(service_name)
            return self._is_service_healthy(service)
        except:
            return False
    
    def health_check(self) -> Dict[str, bool]:
        """Check health of all registered services"""
        health_status = {}
        
        for service_name in self._factories.keys():
            try:
                health_status[service_name] = self.is_available(service_name)
            except Exception as e:
                logger.error(f"Health check failed for {service_name}: {e}")
                health_status[service_name] = False
        
        return health_status
    
    def reset_service(self, service_name: str) -> None:
        """Force recreation of a service on next access"""
        with self._lock:
            if service_name in self._services:
                logger.info(f"Resetting service: {service_name}")
                del self._services[service_name]
    
    def shutdown(self) -> None:
        """Shutdown all services and clean up resources"""
        logger.info("Shutting down ServiceContainer")
        with self._lock:
            for service_name, service in self._services.items():
                try:
                    if hasattr(service, 'shutdown'):
                        service.shutdown()
                    elif hasattr(service, 'close'):
                        service.close()
                    logger.debug(f"Shutdown service: {service_name}")
                except Exception as e:
                    logger.error(f"Error shutting down service {service_name}: {e}")
            
            self._services.clear()
            logger.info("ServiceContainer shutdown complete")
    
    def _is_service_healthy(self, service: Any) -> bool:
        """Check if a service instance is healthy"""
        if service is None:
            return False
        
        # Check for custom health check method
        if hasattr(service, 'is_healthy'):
            try:
                return service.is_healthy()
            except Exception as e:
                logger.warning(f"Service health check failed: {e}")
                return False
        
        # Default: service is healthy if it exists
        return True
    
    def get_service_info(self) -> Dict[str, Dict[str, Any]]:
        """Get diagnostic information about all services"""
        info = {
            'registered_services': list(self._factories.keys()),
            'active_services': list(self._services.keys()),
            'health_status': self.health_check(),
            'config_summary': self.config.to_dict()
        }
        return info


class ServiceError(Exception):
    """Base exception for service layer errors"""
    pass


class ServiceNotFoundError(ServiceError):
    """Raised when a requested service is not registered"""
    pass


class ServiceCreationError(ServiceError):
    """Raised when service creation fails"""
    pass