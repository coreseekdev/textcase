from typing import Any, Dict, Callable, Optional, TYPE_CHECKING
from .vfs_service import VFSService
from .config import ConfigService

if TYPE_CHECKING:
    from .service_registry import ServiceRegistry

class TestService:
    def hello(self):
        """Simple hello method for testing the RPC service"""
        return "hello world"

class DefaultService:
    """Default service implementation."""
    def name(self) -> str:
        """Get the name of the service."""
        return "DefaultService"

def create_vfs_service(service_name: str, service_registry: 'ServiceRegistry') -> VFSService:
    """Factory function to create VFS service instances.
    
    Args:
        service_name: Name of the service
        service_registry: ServiceRegistry instance for accessing other services
        
    Returns:
        VFSService instance
    """
    # Use current directory as default root path
    # VFS services should get their configuration from the service registry
    return VFSService('.')

def create_config_service(service_name: str, service_registry: 'ServiceRegistry') -> ConfigService:
    """Factory function to create Config service instances.
    
    Args:
        service_name: Name of the service
        service_registry: ServiceRegistry instance
        
    Returns:
        ConfigService instance from the registry
    """
    return service_registry.get_config_service()

# Service registry for mapping service names to factory functions
_service_factories: Dict[str, Callable[[str, 'ServiceRegistry'], Any]] = {
    "test": lambda service_name, service_registry: TestService(),
    "default": lambda service_name, service_registry: DefaultService(),
    "config": create_config_service,
    "vfs": create_vfs_service,
    "localfs": create_vfs_service,  # Alias for VFS service
    "git-repo": create_vfs_service  # Alias for VFS service
}

def register_service(name: str, factory: Callable[[str, 'ServiceRegistry'], Any]) -> None:
    """Register a service factory.
    
    Args:
        name: Name of the service
        factory: Factory function that takes service name and ServiceRegistry, returns a service instance
    """
    _service_factories[name] = factory

def get_service_factory(name: str) -> Callable[[str, 'ServiceRegistry'], Any]:
    """Get a service factory by name.
    
    Args:
        name: Name of the service
        
    Returns:
        Factory function for the service
        
    Raises:
        KeyError: If no factory is registered for the name
    """
    return _service_factories[name]

def default_service_factory(service_name: str, service_registry: 'ServiceRegistry') -> Any:
    """Default service factory that creates service instances.
    
    Args:
        service_name: Name of the service to create
        service_registry: ServiceRegistry instance
        
    Returns:
        A new service instance
    """
    factory = _service_factories.get(service_name, _service_factories["default"])
    print("get factory", service_name)
    return factory(service_name, service_registry)