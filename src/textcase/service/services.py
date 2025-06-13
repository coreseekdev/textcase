from typing import Any, Dict, Callable, Optional, TYPE_CHECKING
from ..core.vfs_service import VFSService, create_vfs_service
from ..core.config import ConfigService

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

# Service registry for mapping service names to factory functions
_service_factories: Dict[str, Callable[[str, 'ServiceRegistry'], Any]] = {
    "test": lambda service_name, service_registry: TestService(),
    "default": lambda service_name, service_registry: DefaultService(),
    "vfs": create_vfs_service,
}

def register_service(name: str, factory: Callable[[str, 'ServiceRegistry'], Any]) -> None:
    """Register a service factory.
    
    Args:
        name: Name of the service
        factory: Factory function that takes service name and ServiceRegistry, returns a service instance
    """
    _service_factories[name] = factory

def get_service_factory(name: str) -> Optional[Callable[[str, 'ServiceRegistry'], Any]]:
    """Get a service factory by name.
    
    Args:
        name: Name of the service
        
    Returns:
        Factory function for the service
        
    Raises:
        KeyError: If no factory is registered for the name
    """
    return _service_factories.get(name, None)

