"""Service registry protocol definition.

This module defines the protocol interface for service registries."""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, Callable, Protocol

from .service_config_protocol import ServiceConfigProtocol


class ServiceRegistry(Protocol):
    """Protocol for service registry implementations.
    
    Defines the interface for managing and accessing services in the system.
    """
    
    def get_service(self, 
                   service_name: str, 
                   endpoint: Optional[str] = None,
                   service_factory: Optional[Callable[[str, 'ServiceRegistry'], Any]] = None) -> Any:
        """Get or create a service.
        
        For 'config' service, returns ConfigService instance directly.
        For other services, returns RPC endpoint string.
        
        Args:
            service_name: Name of the service to get or create
            endpoint: Optional endpoint for RPC services
            service_factory: Optional factory function for creating services
            
        Returns:
            Service instance (for config) or endpoint string (for RPC services)
        """
        ...
    
    def stop_service(self, service_name: str, timeout: float = 2.0) -> None:
        """Stop a running service.
        
        Args:
            service_name: Name of the service to stop
            timeout: Maximum time to wait for service to stop
        """
        ...
    
    def stop_all_services(self, timeout: float = 5.0) -> None:
        """Stop all running services.
        
        Args:
            timeout: Maximum time to wait for all services to stop
        """
        ...
    
    def is_service_running(self, service_name: str) -> bool:
        """Check if a service is currently running.
        
        Args:
            service_name: Name of the service to check
            
        Returns:
            True if service is running, False otherwise
        """
        ...
    
    @property
    def config_service(self):
        """Get the configuration service instance.
        
        Returns:
            ConfigService instance or None if not set
        """
        ...
