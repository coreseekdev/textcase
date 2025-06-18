"""New service registry implementation with optional zerorpc/gevent support.

This module provides a service registry that automatically selects the best
available backend (zerorpc/gevent or direct calls) based on installed dependencies.
"""

from pathlib import Path
from typing import Optional, Union

from .service_registry_base import BaseServiceRegistry, ServiceBackend
from ..core.config import ConfigService
from ..proto.service_registry_protocol import ServiceRegistry


class ServiceRegistryNew(BaseServiceRegistry):
    """New service registry implementation with optional backend support.
    
    This implementation automatically selects the best available backend:
    1. ZeroRPC/gevent backend if available
    2. Direct backend as fallback
    """
    
    def __init__(self, config: Optional[Union[Path, ConfigService]] = None, backend: Optional[ServiceBackend] = None):
        """Initialize the service registry.
        
        Args:
            config: Configuration path or ConfigService instance
            backend: Optional backend to use (auto-detected if None)
        """
        super().__init__(config, backend)


# For backward compatibility, provide a factory function
def create_service_registry(config: Optional[Union[Path, ConfigService]] = None, backend_type: Optional[str] = None) -> ServiceRegistry:
    """Create a new ServiceRegistry instance.
    
    Args:
        config: Either a Path to config file or an existing ConfigService instance
        backend_type: Optional backend type ('zerorpc', 'direct', or None for auto-detection)
    
    Returns:
        ServiceRegistry implementation instance
    """
    backend = None
    if backend_type == 'direct':
        from .backends.direct_backend import DirectBackend
        backend = DirectBackend()
    elif backend_type == 'zerorpc':
        try:
            from .backends.zerorpc_backend import ZeroRPCBackend
            backend = ZeroRPCBackend()
        except ImportError:
            raise ImportError("zerorpc/gevent not available, cannot use zerorpc backend")
    
    return ServiceRegistryNew(config, backend)