from typing import Any, Dict, Callable, Optional

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
_service_factories: Dict[str, Callable[[str], Any]] = {
    "test": lambda service_name: TestService(),
    "default": lambda service_name: DefaultService()
}

def register_service(name: str, factory: Callable[[str], Any]) -> None:
    """Register a service factory.
    
    Args:
        name: Name of the service
        factory: Factory function that takes an endpoint and returns a service instance
    """
    _service_factories[name] = factory

def get_service_factory(name: str) -> Callable[[str], Any]:
    """Get a service factory by name.
    
    Args:
        name: Name of the service
        
    Returns:
        Factory function for the service
        
    Raises:
        KeyError: If no factory is registered for the name
    """
    return _service_factories[name]

def default_service_factory(service_name: str) -> Any:
    """Default service factory that creates service instances.
    
    Args:
        service_name: Name of the service to create
        
    Returns:
        A new service instance
    """
    factory = _service_factories.get(service_name, _service_factories["default"])
    print("get factory", service_name)
    return factory(service_name)