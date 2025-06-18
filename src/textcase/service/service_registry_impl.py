# src/textcase/core/service_registry.py
import logging
import atexit
import uuid
from pathlib import Path
from typing import Dict, Optional, Any, Callable, Union

# Optional imports for RPC functionality
try:
    import zerorpc
    import gevent
    from gevent import monkey
    # 确保 monkey patch
    monkey.patch_all()
    HAS_RPC_DEPS = True
except ImportError:
    gevent = None
    monkey = None
    zerorpc = None
    HAS_RPC_DEPS = False

from .services import get_service_factory
from ..core.config import ConfigService
from ..proto.service_registry_protocol import ServiceRegistry

class ServiceInfo:
    """Container for service information."""
    def __init__(self, server, service_greenlet, endpoint: str):
        self.server = server
        self.greenlet = service_greenlet
        self.endpoint = endpoint
        self.stop_event = gevent.event.Event() if gevent else None

class ServiceRegistryImpl(ServiceRegistry):
    """Singleton class to manage RPC services and their endpoints using gevent."""
    
    _instance = None
    
    def __new__(cls, config: Optional[Union[Path, ConfigService]] = None):
        if cls._instance is None:
            cls._instance = super(ServiceRegistry, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self, config: Optional[Union[Path, ConfigService]] = None):
        if hasattr(self, '_initialized') and self._initialized:            return
        
        if not HAS_RPC_DEPS:
            raise ImportError("ServiceRegistryImpl requires gevent and zerorpc. Install with: pip install textcase[rpc]")
            
        self._services: Dict[str, ServiceInfo] = {}
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

    def _generate_endpoint(self, service_name: str) -> str:
        """Generate a unique endpoint for a service."""
        return f"inproc://{service_name}-{uuid.uuid4().hex}"
        # return f"inproc://{service_name}"

    def _run_service(self, service_info: ServiceInfo) -> None:
        """Run the service in a gevent greenlet."""
        try:
            service_info.server.run()
        except Exception as e:
            logging.error(f"Service error: {e}")
            raise
        finally:
            service_info.stop_event.set()
    
    def get_service(self, 
                   service_name: str, 
                   endpoint: Optional[str] = None) -> Any:
        """Get or create a service.
        
        For 'config' service, returns ConfigService instance directly.
        For other services, returns RPC endpoint string.
        """            
        if service_name in self._services:
            return self._services[service_name].endpoint
            
        # Create a new service
        if endpoint is None:
            endpoint = self._generate_endpoint(service_name)
        
        # Create service instance if factory is provided
        service_factory = get_service_factory(service_name)
        if service_factory:
            service_instance = service_factory(service_name, self)
        else:
            # 没有照顾 service_name 对应服务的构建方式
            return None
        
        # Create and configure the server
        server = zerorpc.Server(service_instance)
        server.bind(endpoint)
        
        # Create service info
        service_info = ServiceInfo(server, None, endpoint)
        
        # Start the service in a greenlet
        service_greenlet = gevent.spawn(self._run_service, service_info)
        service_info.greenlet = service_greenlet
        self._services[service_name] = service_info
        
        # Give it a moment to start
        gevent.sleep(0.1)
        
        logging.info(f"Started service '{service_name}' on {endpoint}")
        return endpoint
    
    def stop_service(self, service_name: str, timeout: float = 2.0) -> None:
        """Stop a specific service."""
        if service_name not in self._services:
            return
            
        service_info = self._services[service_name]
        
        try:
            # Stop the server
            service_info.server.stop()
            
            # Wait for the greenlet to finish
            if service_info.greenlet and not service_info.greenlet.ready():
                service_info.greenlet.join(timeout=timeout)
                if not service_info.greenlet.ready():
                    logging.warning(f"Service greenlet for '{service_name}' did not stop gracefully")
            
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
        return service_name in self._services
    
    @property
    def config_service(self) -> ConfigService:
        return self._config_service

# For backward compatibility, provide a factory function
def create_service_registry(config: Optional[Union[Path, ConfigService]] = None, backend_type: Optional[str] = None) -> ServiceRegistry:
    """Create a new ServiceRegistry instance.
    
    Args:
        config: Either a Path to config file or an existing ConfigService instance
        backend_type: Optional backend type ('zerorpc', 'direct', or None for auto-detection)
    
    Returns:
        ServiceRegistry implementation instance
    """
    # If backend_type is specified, use the new registry with specific backend
    if backend_type is not None:
        from .service_registry_new import create_service_registry as create_new_registry
        return create_new_registry(config, backend_type)
    
    # Try to determine the best backend automatically
    if HAS_RPC_DEPS:
        # Use zerorpc backend (existing implementation)
        return ServiceRegistryImpl(config)
    else:
        # Fall back to direct backend
        from .service_registry_new import create_service_registry as create_new_registry
        return create_new_registry(config, 'direct')