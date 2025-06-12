"""Service registry module.

Provides ServiceRegistry protocol and its default implementation.
"""
from pathlib import Path

from ..proto.service_registry_protocol import ServiceRegistry
from .service_registry_impl import ServiceRegistryImpl

# Export the protocol and implementation
__all__ = ['ServiceRegistry', 'ServiceRegistryImpl']

# For backward compatibility, provide a factory function
def create_service_registry(config_file: Path) -> ServiceRegistry:
    """Create a new ServiceRegistry instance.
    
    Returns:
        ServiceRegistry implementation instance
    """
    return ServiceRegistryImpl(config_file)