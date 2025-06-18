"""Client interfaces for TextCase services.

This module provides client interfaces for connecting to TextCase services.
It dynamically selects the appropriate client implementation based on RPC availability."""

from typing import Optional, Any

# Try to import zerorpc to determine RPC availability
try:
    import zerorpc
    RPC_AVAILABLE = True
except ImportError:
    RPC_AVAILABLE = False

# Import both client implementations
from .vfs_client_new import VFSClientNew as VFSClientNew, VFSClientException as VFSClientExceptionRPC

# Export the exception types
VFSClientException = VFSClientExceptionRPC

def get_vfs_client(endpoint: str = "inproc://vfs", service_registry: Optional[Any] = None) -> Any:
    """Get a VFS client instance based on RPC availability and endpoint type.
    
    Args:
        endpoint: RPC endpoint to connect to
        service_registry: Optional service registry for direct backend
        
    Returns:
        VFS client instance (either VFSClient or VFSClientNew)
        
    Raises:
        VFSClientException: If connection fails
    """
    # If endpoint starts with 'direct://' or RPC is not available, use new client
    if endpoint.startswith('direct://') or not RPC_AVAILABLE:
        return VFSClientNew(endpoint, service_registry=service_registry)
    else:
        from .vfs_client import VFSClient as VFSClientRPC, VFSClientException as VFSClientExceptionRPC
        # Use traditional RPC client
        return VFSClientRPC(endpoint)

# For backward compatibility, provide VFSClient as an alias to get_vfs_client
def VFSClient(endpoint: str = "inproc://vfs", service_registry: Optional[Any] = None) -> Any:
    """Create a VFS client instance.
    
    This function dynamically selects the appropriate client implementation
    based on RPC availability and endpoint type.
    
    Args:
        endpoint: RPC endpoint to connect to
        service_registry: Optional service registry for direct backend
        
    Returns:
        VFS client instance
    """
    return get_vfs_client(endpoint, service_registry)

__all__ = ['VFSClient', 'VFSClientException', 'get_vfs_client']