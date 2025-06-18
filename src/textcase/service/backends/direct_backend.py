"""Direct backend implementation for service registry.

This module provides a direct function call backend for the service registry,
which doesn't require any external dependencies like zerorpc or gevent.
It's suitable for single-process applications or when RPC is not needed.
"""

import logging
import uuid
from typing import Any, Dict, Optional


class DirectClient:
    """Direct client that calls service methods directly."""
    
    def __init__(self, service_instance: Any):
        """Initialize with a service instance.
        
        Args:
            service_instance: The service instance to call methods on
        """
        self.service_instance = service_instance
    
    def __getattr__(self, name: str) -> Any:
        """Delegate attribute access to the service instance."""
        return getattr(self.service_instance, name)


class DirectBackend:
    """Direct backend for service registry.
    
    This backend provides direct function calls without RPC overhead.
    It's suitable for single-process applications.
    """
    
    def __init__(self):
        """Initialize the direct backend."""
        self._service_instances: Dict[str, Any] = {}
    
    def generate_endpoint(self, service_name: str) -> str:
        """Generate a unique endpoint for a service."""
        return f"direct://{service_name}-{uuid.uuid4().hex}"
    
    def start_service(self, service_name: str, service_instance: Any, endpoint: str) -> Dict[str, Any]:
        """Start a service with the given instance and endpoint.
        
        Args:
            service_name: Name of the service
            service_instance: Service instance to expose
            endpoint: Endpoint string for the service (not used in direct backend)
            
        Returns:
            Service handle containing the service instance
        """
        # Store the service instance
        self._service_instances[service_name] = service_instance
        
        logging.info(f"Started direct service '{service_name}'")
        
        # Return handle
        return {
            'service_instance': service_instance,
            'endpoint': endpoint
        }
    
    def stop_service(self, service_name: str, service_handle: Dict[str, Any]) -> None:
        """Stop a service given its handle.
        
        Args:
            service_name: Name of the service
            service_handle: Service handle returned by start_service
        """
        # Remove the service instance
        if service_name in self._service_instances:
            del self._service_instances[service_name]
        
        logging.info(f"Stopped direct service '{service_name}'")
    
    def is_service_running(self, service_name: str, service_handle: Dict[str, Any]) -> bool:
        """Check if a service is running.
        
        Args:
            service_name: Name of the service
            service_handle: Service handle returned by start_service
            
        Returns:
            True if the service is running, False otherwise
        """
        return service_name in self._service_instances
    
    def create_client(self, endpoint: str) -> DirectClient:
        """Create a client for the given endpoint.
        
        Args:
            endpoint: Endpoint string for the service
            
        Returns:
            DirectClient instance that calls methods directly
        """
        # Extract service name from endpoint
        if endpoint.startswith('direct://'):
            service_name = endpoint[9:].split('-')[0]  # Remove 'direct://' and UUID
        else:
            # Fallback: assume the endpoint is the service name
            service_name = endpoint
        
        if service_name in self._service_instances:
            return DirectClient(self._service_instances[service_name])
        else:
            raise ValueError(f"Service '{service_name}' not found")