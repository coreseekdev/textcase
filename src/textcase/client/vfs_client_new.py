"""New VFS Client with optional zerorpc support.

This module provides a VFS client that can work with different backends
(zerorpc or direct calls) based on availability.
"""

import threading
from typing import Optional, Any, Dict, List, Tuple, Union
from pathlib import PurePosixPath, Path

from ..proto.service_vfs_protocol import EntryType
from ..service.error_result import ErrorResult, is_error_result, ResultOrError

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
    def mount_point(self) -> PurePosixPath:
        """Get the root path of the VFS service.
        
        Returns:
            Root path as PurePosixPath
        """
        result = self._handle_rpc_exception(self.client.mount_point)
        return PurePosixPath(result)
    
    def info(self, path: Union[str, PurePosixPath]) -> Dict[str, Any]:
        """Get information about a path.
        
        Args:
            path: Path to get info for
            
        Returns:
            Dictionary containing path information
        """
        path_str = str(path)
        return self._handle_rpc_exception(self.client.info, path_str)
    
    def list(self, path: Union[str, PurePosixPath] = '/', option: Optional[Dict[str, Any]] = None) -> List[Tuple[PurePosixPath, EntryType]]:
        """List contents of a directory.
        
        Args:
            path: Directory path to list (string or PurePosixPath)
            option: Optional listing options
            
        Returns:
            List of (PurePosixPath, EntryType) tuples
        """
        if option is None:
            option = {}
        
        # 确保路径是POSIX风格
        if isinstance(path, str):
            # 将Windows风格路径转换为POSIX风格
            path = Path(path).as_posix()
        path_str = str(path)
        
        # Get string tuples from server and convert to proper types
        result = self._handle_rpc_exception(self.client.list, path_str, option)
        
        # Convert string tuples to (PurePosixPath, EntryType) tuples
        converted_result = []
        for path_str, entry_type_str in result:
            posix_path = PurePosixPath(path_str)
            entry_type = EntryType(entry_type_str)
            converted_result.append((posix_path, entry_type))
        
        return converted_result
    
    def get_text(self, path: Union[str, PurePosixPath], encoding: str = 'utf-8') -> str:
        """Get file contents as text.
        
        Args:
            path: Path to the file (string or PurePosixPath)
            encoding: Text encoding (default: utf-8)
            
        Returns:
            File contents as string
        """
        # 确保路径是POSIX风格
        if isinstance(path, str):
            # 将Windows风格路径转换为POSIX风格
            path = Path(path).as_posix()
        path_str = str(path)
        
        content = self._handle_rpc_exception(self.client.get, path_str)
        return content.decode(encoding) if content else ''
    
    def get(self, path: Union[str, PurePosixPath]) -> bytes:
        """Get file contents as bytes.
        
        Args:
            path: Path to the file (string or PurePosixPath)
            
        Returns:
            File contents as bytes
        """
        # 确保路径是POSIX风格
        if isinstance(path, str):
            # 将Windows风格路径转换为POSIX风格
            path = Path(path).as_posix()
        path_str = str(path)
        
        return self._handle_rpc_exception(self.client.get, path_str)
    

    
    def put(self, path: Union[str, PurePosixPath], content: bytes, create_if_missing: bool = False) -> bool:
        """Put file contents.
        
        Args:
            path: Path to write to (string or PurePosixPath)
            content: Content to write
            create_if_missing: Create file if it doesn't exist
            
        Returns:
            Success status
        """
        # 确保路径是POSIX风格
        if isinstance(path, str):
            # 将Windows风格路径转换为POSIX风格
            path = Path(path).as_posix()
        path_str = str(path)
        
        return self._handle_rpc_exception(self.client.put, path_str, content, create_if_missing)
    
    def remove(self, path: Union[str, PurePosixPath], force: bool = False) -> bool:
        """Remove a file or directory.
        
        Args:
            path: Path to remove (string or PurePosixPath)
            force: Force removal even if non-empty directory
            
        Returns:
            Success status
        """
        # 确保路径是POSIX风格
        if isinstance(path, str):
            # 将Windows风格路径转换为POSIX风格
            path = Path(path).as_posix()
        path_str = str(path)
        
        return self._handle_rpc_exception(self.client.remove, path_str, force)
    
    def mkdir(self, path: Union[str, PurePosixPath], parents: bool = False, exist_ok: bool = False) -> bool:
        """Create a directory.
        
        Args:
            path: Directory path to create (string or PurePosixPath)
            parents: Create parent directories if they don't exist
            exist_ok: Don't raise error if directory already exists
            
        Returns:
            Success status
        """
        # 确保路径是POSIX风格
        if isinstance(path, str):
            # 将Windows风格路径转换为POSIX风格
            path = Path(path).as_posix()
        path_str = str(path)
        
        return self._handle_rpc_exception(self.client.mkdir, path_str, parents, exist_ok)
    
    def to_vfs_path(self, local_path: Path) -> Optional[PurePosixPath]:
        """Convert a local file system path to a VFS path if possible.
        
        This method attempts to convert a path from the local file system
        to its equivalent path in the VFS. It handles mounted VFS instances
        by checking if the local path belongs to any mounted VFS and delegating
        the conversion if necessary.
        
        Args:
            local_path: Local file system path to convert
            
        Returns:
            Equivalent VFS path as PurePosixPath if conversion is possible,
            None if the path cannot be mapped to this VFS
        """
        path_str = local_path.as_posix()
        try:
            result = self._handle_rpc_exception(self.client.to_vfs_path, path_str)
            if result is not None:
                return PurePosixPath(result)
            return None
        except Exception as e:
            raise VFSClientException(
                type(e).__name__,
                str(e),
                None
            )


# For backward compatibility
def get_vfs_client(endpoint: str = "inproc://vfs", service_registry: Optional[Any] = None) -> VFSClientNew:
    """Get a VFS client instance.
    
    Args:
        endpoint: Service endpoint to connect to
        service_registry: Optional service registry for direct backend
        
    Returns:
        VFS client instance
        
    Raises:
        VFSClientException: If connection fails
    """
    try:
        return VFSClientNew(endpoint, service_registry)
    except Exception as e:
        if isinstance(e, VFSClientException):
            raise
        else:
            raise VFSClientException(
                type(e).__name__,
                str(e),
                None
            )
    
    def patch(self, path: Union[str, PurePosixPath], range_tuple: Tuple[int, int], content: bytes, create_if_missing: bool = False) -> bool:
        """Patch a file with new content in a specific range.
        
        Args:
            path: Path to the file to patch (string or PurePosixPath)
            range_tuple: (start, end) byte range to replace
            content: New content to insert
            create_if_missing: Create file if it doesn't exist
            
        Returns:
            Success status
        """
        # 确保路径是POSIX风格
        if isinstance(path, str):
            # 将Windows风格路径转换为POSIX风格
            path = Path(path).as_posix()
        path_str = str(path)
        
        return self._handle_rpc_exception(self.client.patch, path_str, range_tuple, content, create_if_missing)
    
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
    
    def to_local_path(self, vfs_path: Union[str, PurePosixPath]) -> Optional[Path]:
        """Convert a VFS path to a local file system path if possible.
        
        This method attempts to convert a path from the VFS to its equivalent
        path in the local file system. It handles mounted VFS instances by
        checking if the VFS path belongs to any mounted VFS and delegating the
        conversion if necessary.
        
        Args:
            vfs_path: VFS path to convert (string or PurePosixPath)
            
        Returns:
            Equivalent local file system path as Path if conversion is possible,
            None if the path cannot be mapped to this VFS
        """
        # 确保路径是POSIX风格
        if isinstance(vfs_path, str):
            # 将Windows风格路径转换为POSIX风格
            vfs_path = Path(vfs_path).as_posix()
        path_str = str(vfs_path)
        
        try:
            result = self._handle_rpc_exception(self.client.to_local_path, path_str)
            if result is not None:
                return Path(result)
            return None
        except Exception as e:
            raise VFSClientException(
                type(e).__name__,
                str(e),
                None
            )