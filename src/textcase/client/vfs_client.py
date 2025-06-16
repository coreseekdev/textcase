"""VFS Client for connecting to VFS services.

This module provides a client interface for VFS operations that connects
to VFS services through the service registry, hiding internal methods
like resolve_path, mount, unmount, mounts and session management.
"""

import threading
import zerorpc
from typing import Optional, Any, Dict, List, Tuple, Union
from pathlib import PurePosixPath, Path
from ..proto.service_vfs_protocol import EntryType
from ..service.error_result import ErrorResult, is_error_result, ResultOrError


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
            VFSClientException: If server returns a VFSServerException or ErrorResult
        """
        try:
            result = func(*args, **kwargs)
            
            # Check if the result is an ErrorResult
            if is_error_result(result):
                _, error_type, message, traceback_str = result
                # Reconstruct the original exception based on error type
                if error_type == 'FileNotFoundError':
                    original_exception = FileNotFoundError(message)
                    original_exception.server_traceback = traceback_str
                    raise original_exception
                elif error_type == 'PermissionError':
                    original_exception = PermissionError(message)
                    original_exception.server_traceback = traceback_str
                    raise original_exception
                elif error_type == 'ValueError':
                    original_exception = ValueError(message)
                    original_exception.server_traceback = traceback_str
                    raise original_exception
                else:
                    # For other exception types, create a VFSClientException
                    raise VFSClientException(
                        error_type, message, traceback_str
                    )
            
            return result
            
        except Exception as e:
            # Check if this is a zerorpc RemoteError with JSON exception info
            if type(e).__name__ == 'RemoteError':
                exception_type, message, traceback = e.args
                # Reconstruct the original exception
                if exception_type == 'FileNotFoundError':
                    original_exception = FileNotFoundError(message)
                    original_exception.server_traceback = traceback
                    raise original_exception
                elif exception_type == 'PermissionError':
                    original_exception = PermissionError(message)
                    original_exception.server_traceback = traceback
                    raise original_exception
                elif exception_type == 'ValueError':
                    original_exception = ValueError(message)
                    original_exception.server_traceback = traceback
                    raise original_exception
                else:
                    # For other exception types, create a VFSClientException
                    raise VFSClientException(
                        exception_type, message, traceback
                    )
            
            # Re-raise other exceptions as-is
            raise e

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
            path: Path to get info for (string or PurePosixPath)
            
        Returns:
            Path information
        """
        # 确保路径是POSIX风格
        if isinstance(path, str):
            # 将Windows风格路径转换为POSIX风格
            path = Path(path).as_posix()
        path_str = str(path)
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