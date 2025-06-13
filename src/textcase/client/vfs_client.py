"""VFS Client for connecting to VFS services.

This module provides a client interface for VFS operations that connects
to VFS services through the service registry, hiding internal methods
like resolve_path, mount, unmount, mounts and session management.
"""

import threading
import zerorpc
from typing import Optional, Any, Dict, List, Tuple, Union
from pathlib import PurePosixPath
from ..proto.service_vfs_protocol import EntryType


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
        # self.endpoint = service_registry.get_service(
        #    "vfs",
        #    endpoint=endpoint,
        #)
        self.endpoint = endpoint
        self.client = zerorpc.Client(connect_to=self.endpoint)
    
    def _handle_rpc_exception(self, func, *args, **kwargs):
        """Handle RPC exceptions and convert server exceptions to client exceptions.
        
        Args:
            func: RPC function to call
            *args: Function arguments
            **kwargs: Function keyword arguments
            
        Returns:
            Function result
            
        Raises:
            VFSClientException: If server returns a VFSServerException
        """
        try:
            return func(*args, **kwargs)
        except Exception as e:
            # Check if this is a server-side VFSServerException
            if hasattr(e, 'exception_type') and hasattr(e, 'original_message'):
                raise VFSClientException.from_server_exception(e)
            else:
                # For other exceptions, wrap them as client exceptions
                raise VFSClientException(
                    type(e).__name__,
                    str(e),
                    None
                )
    
    def name(self) -> str:
        """Get the name of the VFS service.
        
        Returns:
            Service name
        """
        return self._handle_rpc_exception(self.client.name)
    
    def readonly(self) -> bool:
        """Check if the VFS is read-only.
        
        Returns:
            True if read-only, False otherwise
        """
        return self._handle_rpc_exception(self.client.readonly)
    
    def info(self, path: Union[str, PurePosixPath]) -> Dict[str, Any]:
        """Get information about a path.
        
        Args:
            path: Path to get info for (string or PurePosixPath)
            
        Returns:
            Path information
        """
        path_str = str(path) if isinstance(path, PurePosixPath) else path
        return self._handle_rpc_exception(self.client.info, path_str)
    
    def list(self, path: Union[str, PurePosixPath], option: Optional[Dict[str, Any]] = None) -> List[Tuple[PurePosixPath, EntryType]]:
        """List contents of a directory.
        
        Args:
            path: Directory path to list (string or PurePosixPath)
            option: Optional listing options
            
        Returns:
            List of (PurePosixPath, EntryType) tuples
        """
        if option is None:
            option = {}
        path_str = str(path) if isinstance(path, PurePosixPath) else path
        
        # Get string tuples from server and convert to proper types
        result = self._handle_rpc_exception(self.client.list, path_str, option)
        
        # Convert string tuples to (PurePosixPath, EntryType) tuples
        converted_result = []
        for path_str, entry_type_str in result:
            posix_path = PurePosixPath(path_str)
            entry_type = EntryType(entry_type_str)
            converted_result.append((posix_path, entry_type))
        
        return converted_result
    
    def get(self, path: Union[str, PurePosixPath]) -> bytes:
        """Get file contents.
        
        Args:
            path: File path to read (string or PurePosixPath)
            
        Returns:
            File contents as bytes
        """
        path_str = str(path) if isinstance(path, PurePosixPath) else path
        return self._handle_rpc_exception(self.client.get, path_str)
    
    def get_text(self, path: Union[str, PurePosixPath], encoding: str = 'utf-8') -> Optional[str]:
        """Get file contents as text.
        
        Args:
            path: File path to read (string or PurePosixPath)
            encoding: Text encoding to use
            
        Returns:
            File contents as text, or None if failed
        """
        path_str = str(path) if isinstance(path, PurePosixPath) else path
        return self._handle_rpc_exception(self.client.get_text, path_str, encoding)
    
    def put(self, path: Union[str, PurePosixPath], content: bytes, create_if_missing: bool = False) -> bool:
        """Put file contents.
        
        Args:
            path: File path to write (string or PurePosixPath)
            content: File content as bytes
            create_if_missing: Create file if it doesn't exist
            
        Returns:
            Success status
        """
        path_str = str(path) if isinstance(path, PurePosixPath) else path
        return self._handle_rpc_exception(self.client.put, path_str, content, create_if_missing)
    
    def patch(self, path: Union[str, PurePosixPath], range_tuple: Tuple[int, int], content: bytes, 
              session_id: Optional[str] = None) -> str:
        """Apply a patch to a file.
        
        Args:
            path: File path to patch (string or PurePosixPath)
            range_tuple: (start, end) position tuple
            content: Replacement content
            session_id: Optional session ID
            
        Returns:
            Operation ID
        """
        path_str = str(path) if isinstance(path, PurePosixPath) else path
        return self._handle_rpc_exception(self.client.patch, path_str, range_tuple, content, session_id)
    
    def commit(self, message: str, op_id: Optional[str] = None, session_id: Optional[str] = None) -> Dict[str, Any]:
        """Commit patches.
        
        Args:
            message: Commit message
            op_id: Optional operation ID
            session_id: Optional session ID
            
        Returns:
            Commit status and message
        """
        return self._handle_rpc_exception(self.client.commit, message, op_id, session_id)
    
    def abort(self, op_id: Optional[str] = None, session_id: Optional[str] = None) -> Dict[str, Any]:
        """Abort patches.
        
        Args:
            op_id: Optional operation ID
            session_id: Optional session ID
            
        Returns:
            Abort status and message
        """
        return self._handle_rpc_exception(self.client.abort, op_id, session_id)
    
    def create_session(self) -> str:
        """Create a new edit session.
        
        Returns:
            Session ID
        """
        return self._handle_rpc_exception(self.client.create_session)
    
    def list_sessions(self) -> List[str]:
        """List all active sessions.
        
        Returns:
            List of active session IDs
        """
        return self._handle_rpc_exception(self.client.list_sessions)


# For backward compatibility
def get_vfs_client(endpoint: str = "inproc://vfs") -> VFSClient:
    """Get a VFS RPC client instance.
    
    Args:
        endpoint: RPC endpoint to connect to
        
    Returns:
        VFS client instance
        
    Raises:
        VFSClientException: If connection fails
    """
    try:
        return VFSClient(endpoint)
    except Exception as e:
        if isinstance(e, VFSClientException):
            raise
        else:
            raise VFSClientException(
                type(e).__name__,
                str(e),
                None
            )