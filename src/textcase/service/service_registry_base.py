"""Base service registry implementation with optional backend support.

This module provides a flexible service registry that can work with different
backends (zerorpc/gevent, asyncio, or direct function calls) based on availability.
"""

import logging
import atexit
import uuid
from pathlib import Path
from typing import Dict, Optional, Any, Union, Protocol, runtime_checkable
from abc import ABC, abstractmethod

from .services import get_service_factory
from ..core.config import ConfigService
from ..proto.service_registry_protocol import ServiceRegistry


@runtime_checkable
class ServiceBackend(Protocol):
    """Protocol for service backend implementations."""
    
    def start_service(self, service_name: str, service_instance: Any, endpoint: str) -> Any:
        """Start a service with the given instance and endpoint.
        
        Returns:
            Service handle or endpoint for client connections
        """
        ...
    
    def stop_service(self, service_name: str, service_handle: Any) -> None:
        """Stop a service given its handle."""
        ...
    
    def is_service_running(self, service_name: str, service_handle: Any) -> bool:
        """Check if a service is running."""
        ...
    
    def create_client(self, endpoint: str) -> Any:
        """Create a client for the given endpoint."""
        ...


class ServiceInfo:
    """Container for service information."""
    
    def __init__(self, service_instance: Any, service_handle: Any, endpoint: str, backend: ServiceBackend):
        self.service_instance = service_instance
        self.service_handle = service_handle
        self.endpoint = endpoint
        self.backend = backend


class BaseServiceRegistry(ServiceRegistry):
    """Base service registry with pluggable backends."""
    
    _instance = None
    
    def __new__(cls, config: Optional[Union[Path, ConfigService]] = None, backend: Optional[ServiceBackend] = None):
        if cls._instance is None:
            cls._instance = super(ServiceRegistry, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self, config: Optional[Union[Path, ConfigService]] = None, backend: Optional[ServiceBackend] = None):
        if hasattr(self, '_initialized') and self._initialized:
            return
            
        self._services: Dict[str, ServiceInfo] = {}
        self._backend = backend or self._get_default_backend()
        
        # 初始化 config_service
        if isinstance(config, ConfigService):
            self._config_service = config
        elif config is not None:
            self._config_service = ConfigService(config)
        else:
            self._config_service = ConfigService(None)
            
        self._initialized = True
        
        # Ensure cleanup on program exit
        atexit.register(self.stop_all_services)
    
    def _get_default_backend(self) -> ServiceBackend:
        """Get the default backend based on available dependencies."""
        # Try zerorpc/gevent backend first
        try:
            from .backends.zerorpc_backend import ZeroRPCBackend
            return ZeroRPCBackend()
        except ImportError:
            logging.warning("zerorpc/gevent not available, falling back to direct backend")
        
        # Fall back to direct backend
        from .backends.direct_backend import DirectBackend
        return DirectBackend()
    
    def _generate_endpoint(self, service_name: str) -> str:
        """Generate a unique endpoint for a service."""
        if hasattr(self._backend, 'generate_endpoint'):
            return self._backend.generate_endpoint(service_name)
        return f"direct://{service_name}-{uuid.uuid4().hex}"
    
    def get_service(self, service_name: str, endpoint: Optional[str] = None) -> Any:
        """Get or create a service.
        
        For 'config' service, returns ConfigService instance directly.
        For other services, returns service endpoint or instance.
        """
        # Special handling for config service
        if service_name == 'config':
            return self._config_service
            
        if service_name in self._services:
            service_info = self._services[service_name]
            return service_info.endpoint
            
        # Create a new service
        if endpoint is None:
            endpoint = self._generate_endpoint(service_name)
        
        # Create service instance if factory is provided
        service_factory = get_service_factory(service_name)
        if not service_factory:
            logging.warning(f"No factory found for service '{service_name}'")
            return None
        
        service_instance = service_factory(service_name, self)
        
        # Start the service using the backend
        try:
            service_handle = self._backend.start_service(service_name, service_instance, endpoint)
            
            # Create service info
            service_info = ServiceInfo(service_instance, service_handle, endpoint, self._backend)
            self._services[service_name] = service_info
            
            logging.info(f"Started service '{service_name}' on {endpoint}")
            return endpoint
            
        except Exception as e:
            logging.error(f"Failed to start service '{service_name}': {e}")
            raise
    
    def stop_service(self, service_name: str, timeout: float = 2.0) -> None:
        """Stop a specific service."""
        if service_name not in self._services:
            return
            
        service_info = self._services[service_name]
        
        try:
            service_info.backend.stop_service(service_name, service_info.service_handle)
            logging.info(f"Stopped service '{service_name}'")
        except Exception as e:
            logging.error(f"Error stopping service '{service_name}': {e}")
            raise
        finally:
            if service_name in self._services:
                del self._services[service_name]
    
    def stop_all_services(self) -> None:
        """Stop all registered services."""
        # Create a list of service names to avoid modifying dict during iteration
        service_names = list(self._services.keys())
    
        for service_name in service_names:
            try:
                self.stop_service(service_name)
            except Exception as e:
                logging.error(f"Error stopping service '{service_name}': {e}")
    
    def is_service_running(self, service_name: str) -> bool:
        """Check if a service is running."""
        if service_name not in self._services:
            return False
        
        service_info = self._services[service_name]
        return service_info.backend.is_service_running(service_name, service_info.service_handle)
    
    def create_client(self, endpoint: str) -> Any:
        """Create a client for the given endpoint."""
        return self._backend.create_client(endpoint)
    
    @property
    def config_service(self) -> ConfigService:
        return self._config_service
    
    @property
    def backend_type(self) -> str:
        """Get the backend type name."""
        return type(self._backend).__name__