"""ZeroRPC backend implementation for service registry.

This module provides a ZeroRPC-based backend for the service registry,
using gevent for concurrency. It requires zerorpc and gevent to be installed.
"""

import logging
import uuid
from typing import Any, Dict, Optional

# Import zerorpc and gevent, which are optional dependencies
try:
    import gevent
    from gevent import monkey
    import zerorpc
    from zerorpc import gevent_zmq
    
    # Apply monkey patching only when this backend is used
    monkey.patch_all()
    
    ZERORPC_AVAILABLE = True
except ImportError:
    ZERORPC_AVAILABLE = False


class ZeroRPCBackend:
    """ZeroRPC backend for service registry.
    
    This backend uses zerorpc and gevent to provide RPC services.
    """
    
    def __init__(self):
        """Initialize the ZeroRPC backend.
        
        Raises:
            ImportError: If zerorpc or gevent are not available
        """
        if not ZERORPC_AVAILABLE:
            raise ImportError("zerorpc and gevent are required for ZeroRPCBackend")
        
        self._service_greenlets: Dict[str, gevent.Greenlet] = {}
        self._service_servers: Dict[str, zerorpc.Server] = {}
        self._stop_events: Dict[str, gevent.event.Event] = {}
    
    def generate_endpoint(self, service_name: str) -> str:
        """Generate a unique endpoint for a service."""
        return f"inproc://{service_name}-{uuid.uuid4().hex}"
    
    def _run_service(self, service_name: str, server: zerorpc.Server, stop_event: gevent.event.Event) -> None:
        """Run the service in a gevent greenlet."""
        try:
            server.run()
        except Exception as e:
            logging.error(f"Service error: {e}")
            raise
        finally:
            stop_event.set()
    
    def start_service(self, service_name: str, service_instance: Any, endpoint: str) -> Dict[str, Any]:
        """Start a service with the given instance and endpoint.
        
        Args:
            service_name: Name of the service
            service_instance: Service instance to expose
            endpoint: Endpoint string for the service
            
        Returns:
            Service handle containing server, greenlet, and stop_event
        """
        # Create and configure the server
        server = zerorpc.Server(service_instance)
        server.bind(endpoint)
        
        # Create stop event
        stop_event = gevent.event.Event()
        
        # Start the service in a greenlet
        service_greenlet = gevent.spawn(self._run_service, service_name, server, stop_event)
        
        # Store references
        self._service_servers[service_name] = server
        self._service_greenlets[service_name] = service_greenlet
        self._stop_events[service_name] = stop_event
        
        # Give it a moment to start
        gevent.sleep(0.1)
        
        # Return handle
        return {
            'server': server,
            'greenlet': service_greenlet,
            'stop_event': stop_event
        }
    
    def stop_service(self, service_name: str, service_handle: Dict[str, Any], timeout: float = 2.0) -> None:
        """Stop a service given its handle.
        
        Args:
            service_name: Name of the service
            service_handle: Service handle returned by start_service
            timeout: Timeout for waiting for the service to stop
        """
        server = service_handle['server']
        greenlet = service_handle['greenlet']
        
        try:
            # Stop the server
            server.stop()
            
            # Wait for the greenlet to finish
            if greenlet and not greenlet.ready():
                greenlet.join(timeout=timeout)
                if not greenlet.ready():
                    logging.warning(f"Service greenlet for '{service_name}' did not stop gracefully")
        finally:
            # Clean up references
            if service_name in self._service_servers:
                del self._service_servers[service_name]
            if service_name in self._service_greenlets:
                del self._service_greenlets[service_name]
            if service_name in self._stop_events:
                del self._stop_events[service_name]
    
    def is_service_running(self, service_name: str, service_handle: Dict[str, Any]) -> bool:
        """Check if a service is running.
        
        Args:
            service_name: Name of the service
            service_handle: Service handle returned by start_service
            
        Returns:
            True if the service is running, False otherwise
        """
        greenlet = service_handle.get('greenlet')
        stop_event = service_handle.get('stop_event')
        
        if not greenlet or not stop_event:
            return False
        
        return not greenlet.ready() and not stop_event.is_set()
    
    def create_client(self, endpoint: str) -> zerorpc.Client:
        """Create a client for the given endpoint.
        
        Args:
            endpoint: Endpoint string for the service
            
        Returns:
            ZeroRPC client instance
        """
        client = zerorpc.Client()
        client.connect(endpoint)
        return client