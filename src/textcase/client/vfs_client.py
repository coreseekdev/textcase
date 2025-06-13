"""VFS Client for connecting to VFS services via ServiceRegistry.

This module provides a client interface for VFS operations that connects
to VFS services through the service registry, hiding internal methods
like resolve_path, mount, unmount, mounts and session management.
"""

import threading
import zerorpc
from typing import Optional, Any, Dict, List, Tuple
from pathlib import PurePosixPath
from ..core.service_registry import service_registry
from ..proto.service_vfs_protocol import EntryType


class VFSClient:
    """Client for VFS RPC service using ServiceRegistry.
    
    This client provides access to basic VFS operations while hiding
    internal methods like mount management and session operations.
    """
    
    _instance = None
    _lock = threading.Lock()

    def __new__(cls, endpoint: str = "inproc://vfs"):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(VFSClient, cls).__new__(cls)
                cls._instance._connect(endpoint)
            return cls._instance

    def _connect(self, endpoint: str):
        """Connect to the VFS RPC server."""
        # Get or create the VFS service
        self.endpoint = service_registry.get_service(
            "vfs",
            endpoint=endpoint,
        )
        self.client = zerorpc.Client(connect_to=self.endpoint)
    
    def name(self) -> str:
        """Get the name of the VFS service.
        
        Returns:
            Service name
        """
        return self.client.name()
    
    def readonly(self) -> bool:
        """Check if the VFS is read-only.
        
        Returns:
            True if read-only, False otherwise
        """
        return self.client.readonly()
    
    def info(self, path: str) -> Dict[str, Any]:
        """Get information about a path.
        
        Args:
            path: Path to get info for
            
        Returns:
            Path information
        """
        return self.client.info(path)
    
    def list(self, path: str, option: Optional[Dict[str, Any]] = None) -> List[Tuple[str, str]]:
        """List contents of a directory.
        
        Args:
            path: Directory path to list
            option: Optional listing options
            
        Returns:
            List of (path, entry_type) tuples
        """
        if option is None:
            option = {}
        return self.client.list(path, option)
    
    def get(self, path: str) -> bytes:
        """Get file contents.
        
        Args:
            path: File path to read
            
        Returns:
            File contents as bytes
        """
        return self.client.get(path)
    
    def get_text(self, path: str, encoding: str = 'utf-8') -> Optional[str]:
        """Get file contents as text.
        
        Args:
            path: File path to read
            encoding: Text encoding to use
            
        Returns:
            File contents as text, or None if failed
        """
        return self.client.get_text(path, encoding)
    
    def put(self, path: str, content: bytes, create_if_missing: bool = False) -> bool:
        """Put file contents.
        
        Args:
            path: File path to write
            content: File content as bytes
            create_if_missing: Create file if it doesn't exist
            
        Returns:
            Success status
        """
        return self.client.put(path, content, create_if_missing)
    
    def patch(self, path: str, range_tuple: Tuple[int, int], content: bytes, 
              session_id: Optional[str] = None) -> str:
        """Apply a patch to a file.
        
        Args:
            path: File path to patch
            range_tuple: (start, end) position tuple
            content: Replacement content
            session_id: Optional session ID
            
        Returns:
            Operation ID
        """
        return self.client.patch(path, range_tuple, content, session_id)


# For backward compatibility
def get_vfs_client(endpoint: str = "inproc://vfs") -> VFSClient:
    """Get a VFS RPC client instance.
    
    Args:
        endpoint: RPC endpoint to connect to
        
    Returns:
        VFS client instance
    """
    return VFSClient(endpoint)