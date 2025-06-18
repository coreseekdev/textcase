"""New VFS Client with optional zerorpc support.

This module provides a VFS client that can work with different backends
(zerorpc or direct calls) based on availability.
"""

import threading
from typing import Optional, Any, Dict, List, Tuple, Union
from pathlib import PurePosixPath, Path

from ..proto.service_vfs_protocol import EntryType
from ..service.error_result import is_error_result, error_result_from_dict, ResultOrError

# Try to import zerorpc, but make it optional
try:
    import zerorpc
    ZERORPC_AVAILABLE = True
except ImportError:
    ZERORPC_AVAILABLE = False


class VFSClientException(Exception):
    """Exception for VFS client errors.
    
    This exception reconstructs server-side exceptions on the client side.
    """
    
    def __init__(self, exception_type: str, message: str, traceback_str: str = None):
        self.exception_type = exception_type
        self.original_message = message
        self.traceback_str = traceback_str
        super().__init__(f"{exception_type}: {message}")
    
    @classmethod
    def from_server_exception(cls, server_exception) -> 'VFSClientException':
        """Create client exception from server exception.
        
        Args:
            server_exception: Server-side VFSServerException
            
        Returns:
            VFSClientException instance
        """
        if hasattr(server_exception, 'exception_type'):
            return cls(
                server_exception.exception_type,
                server_exception.original_message,
                getattr(server_exception, 'traceback_str', None)
            )
        else:
            # Fallback for regular exceptions
            return cls(
                type(server_exception).__name__,
                str(server_exception),
                None
            )


class VFSClientNew:
    """New VFS Client with optional zerorpc support.
    
    This client automatically adapts to the available backend:
    - Uses zerorpc.Client if zerorpc is available and endpoint is RPC
    - Uses direct calls for direct:// endpoints
    """
    
    _instance = None
    _lock = threading.Lock()

    def __new__(cls, endpoint: str = "inproc://vfs", service_registry=None):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(VFSClientNew, cls).__new__(cls)
                cls._instance._connect(endpoint, service_registry)
            return cls._instance

    def _connect(self, endpoint: str, service_registry=None):
        """Connect to the VFS service.
        
        Args:
            endpoint: Service endpoint
            service_registry: Optional service registry for direct backend
        """
        self.endpoint = endpoint
        self.service_registry = service_registry
        
        # Determine the backend type based on endpoint and availability
        if endpoint.startswith('direct://') or not ZERORPC_AVAILABLE:
            # Use direct backend
            if service_registry is None:
                raise ValueError("Service registry required for direct backend")
            self.client = service_registry.create_client(endpoint)
            self.backend_type = 'direct'
        else:
            # Use zerorpc backend
            if not ZERORPC_AVAILABLE:
                raise ImportError("zerorpc is required for RPC endpoints")
            self.client = zerorpc.Client(connect_to=endpoint)
            self.backend_type = 'zerorpc'
    
    def _handle_rpc_exception(self, func, *args, **kwargs):
        """Handle RPC exceptions and convert server exceptions to client exceptions.
        
        Args:
            func: RPC function to call
            *args: Function arguments
            **kwargs: Function keyword arguments
            
        Returns:
            Function result
            
        Raises:
            VFSClientException: For server-side VFS errors
            FileNotFoundError: For file not found errors
            PermissionError: For permission errors
            ValueError: For value errors
        """
        try:
            result = func(*args, **kwargs)
            
            # Handle ErrorResult responses
            if is_error_result(result):
                # ErrorResult is now a tuple: ('ErrorResult', error_type, message, traceback_str)
                _, error_type, message, traceback_str = result
                
                # Convert to appropriate exception type
                if error_type == 'FileNotFoundError':
                    raise FileNotFoundError(message)
                elif error_type == 'PermissionError':
                    raise PermissionError(message)
                elif error_type == 'ValueError':
                    raise ValueError(message)
                else:
                    raise VFSClientException(
                        error_type,
                        message,
                        traceback_str
                    )
            
            return result
            
        except Exception as e:
            if self.backend_type == 'zerorpc' and ZERORPC_AVAILABLE:
                # Handle zerorpc.RemoteError
                if isinstance(e, zerorpc.RemoteError):
                    # Parse the remote error
                    error_name = e.name
                    error_msg = str(e)
                    
                    # Convert to appropriate exception type
                    if error_name == 'FileNotFoundError':
                        raise FileNotFoundError(error_msg)
                    elif error_name == 'PermissionError':
                        raise PermissionError(error_msg)
                    elif error_name == 'ValueError':
                        raise ValueError(error_msg)
                    else:
                        raise VFSClientException(error_name, error_msg)
            
            # Re-raise other exceptions as-is
            raise
    
    # VFS Interface Methods
    
    @property
    def name(self) -> str:
        """Get the VFS name."""
        return self._handle_rpc_exception(self.client.name)
    
    @property
    def readonly(self) -> bool:
        """Check if the VFS is read-only."""
        return self._handle_rpc_exception(self.client.readonly)
    
    @property
    def mount_point(self) -> str:
        """Get the mount point."""
        return self._handle_rpc_exception(self.client.mount_point)
    
    def info(self, path: Union[str, PurePosixPath]) -> Dict[str, Any]:
        """Get information about a path.
        
        Args:
            path: Path to get info for
            
        Returns:
            Dictionary containing path information
        """
        path_str = str(path)
        return self._handle_rpc_exception(self.client.info, path_str)
    
    def list(self, path: Union[str, PurePosixPath] = '/') -> List[Dict[str, Any]]:
        """List directory contents.
        
        Args:
            path: Directory path to list
            
        Returns:
            List of dictionaries containing entry information
        """
        path_str = str(path)
        result = self._handle_rpc_exception(self.client.list, path_str)
        
        # Convert tuple format to dictionary format
        if result and isinstance(result[0], (list, tuple)) and len(result[0]) == 2:
            # Server returns List[Tuple[str, str]], convert to List[Dict[str, Any]]
            return [
                {
                    'name': entry[0].split('/')[-1] if '/' in entry[0] else entry[0],
                    'path': entry[0],
                    'type': 'directory' if entry[1] == 'directory' else 'file'
                }
                for entry in result
            ]
        
        return result
    
    def get_text(self, path: Union[str, PurePosixPath], encoding: str = 'utf-8') -> str:
        """Get text content of a file.
        
        Args:
            path: File path
            encoding: Text encoding
            
        Returns:
            File content as string
        """
        path_str = str(path)
        return self._handle_rpc_exception(self.client.get_text, path_str, encoding)
    
    def get_bytes(self, path: Union[str, PurePosixPath]) -> bytes:
        """Get binary content of a file.
        
        Args:
            path: File path
            
        Returns:
            File content as bytes
        """
        path_str = str(path)
        return self._handle_rpc_exception(self.client.get_bytes, path_str)
    
    def exists(self, path: Union[str, PurePosixPath]) -> bool:
        """Check if a path exists.
        
        Args:
            path: Path to check
            
        Returns:
            True if path exists, False otherwise
        """
        path_str = str(path)
        return self._handle_rpc_exception(self.client.exists, path_str)
    
    def is_file(self, path: Union[str, PurePosixPath]) -> bool:
        """Check if a path is a file.
        
        Args:
            path: Path to check
            
        Returns:
            True if path is a file, False otherwise
        """
        path_str = str(path)
        return self._handle_rpc_exception(self.client.is_file, path_str)
    
    def is_dir(self, path: Union[str, PurePosixPath]) -> bool:
        """Check if a path is a directory.
        
        Args:
            path: Path to check
            
        Returns:
            True if path is a directory, False otherwise
        """
        path_str = str(path)
        return self._handle_rpc_exception(self.client.is_dir, path_str)
    
    def write_text(self, path: Union[str, PurePosixPath], content: str, encoding: str = 'utf-8') -> None:
        """Write text content to a file.
        
        Args:
            path: File path
            content: Text content to write
            encoding: Text encoding
        """
        path_str = str(path)
        return self._handle_rpc_exception(self.client.write_text, path_str, content, encoding)
    
    def write_bytes(self, path: Union[str, PurePosixPath], content: bytes) -> None:
        """Write binary content to a file.
        
        Args:
            path: File path
            content: Binary content to write
        """
        path_str = str(path)
        return self._handle_rpc_exception(self.client.write_bytes, path_str, content)
    
    def delete(self, path: Union[str, PurePosixPath]) -> None:
        """Delete a file or directory.
        
        Args:
            path: Path to delete
        """
        path_str = str(path)
        return self._handle_rpc_exception(self.client.delete, path_str)
    
    def mkdir(self, path: Union[str, PurePosixPath], parents: bool = False) -> None:
        """Create a directory.
        
        Args:
            path: Directory path to create
            parents: Create parent directories if they don't exist
        """
        path_str = str(path)
        return self._handle_rpc_exception(self.client.mkdir, path_str, parents)