"""VFS Server implementation for zerorpc.

This module provides a zerorpc-compatible VFS server that wraps
the existing VFS implementations and handles exception serialization
for proper client-side reconstruction.
"""

from pathlib import PurePosixPath, Path
from typing import Dict, List, Optional, Tuple, Any, Union

from ..core.vfs.repo_vfs import RepoVFS
from ..proto.service_vfs_protocol import ServiceVFSProtocol, EntryType
from ..proto.service_registry_protocol import ServiceRegistry
from .error_result import ResultOrError, error_result_from_exception

# VFSServerException removed - no longer needed with simplified exception handling


class VFSServer:
    """VFS Server wrapper for zerorpc compatibility.
    
    This server wraps VFS implementations and provides zerorpc-compatible
    interfaces while preserving exception information for client reconstruction.
    """
    
    def __init__(self, service_name: str, repo_path: Path):

        """Initialize VFS server.
        
        Args:
            repo_path: Path to the repository
        """
        self._name = service_name
        self.repo_path = repo_path
        self._vfs = RepoVFS(repo_path, PurePosixPath('/'))  # 作为 root vfs.
    

    
    def _convert_path(self, path: Union[str, PurePosixPath]) -> PurePosixPath:
        """Convert path to PurePosixPath if needed.
        
        Args:
            path: Path as string or PurePosixPath
            
        Returns:
            PurePosixPath object
        """
        if isinstance(path, str):
            return PurePosixPath(path)
        return path
    
    def _convert_entry_type(self, entry_type: EntryType) -> str:
        """Convert EntryType enum to string.
        
        Args:
            entry_type: EntryType enum value
            
        Returns:
            String representation
        """
        return entry_type.value
    
    def name(self) -> str:
        """Get the name of the VFS service.
        
        Returns:
            Service name
        """
        return self._name

    
    def readonly(self) -> bool:
        """Check if VFS is read-only.
        
        Returns:
            True if read-only, False otherwise
        """
        return self._vfs.readonly()
    
    def info(self, path: str) -> ResultOrError[Dict[str, Any]]:
        """Get information about a path.
        
        Args:
            path: Path to get info for
            
        Returns:
            Path information or ErrorResult if operation failed
        """
        try:
            posix_path = self._convert_path(path)
            return self._vfs.info(posix_path)
        except Exception as e:
            return error_result_from_exception(e)
    
    def list(self, path: str, option: Optional[Dict[str, Any]] = None) -> ResultOrError[List[Tuple[str, str]]]:
        """List contents of a directory.
        
        Args:
            path: Directory path to list
            option: Optional listing options
            
        Returns:
            List of (path, entry_type) tuples as strings or ErrorResult if operation failed
        """
        try:
            posix_path = self._convert_path(path)
            if option is None:
                option = {}
            
            entries = self._vfs.list(posix_path, option)
            
            # Convert results to string tuples
            result = []
            for entry_path, entry_type in entries:
                path_str = str(entry_path)
                type_str = self._convert_entry_type(entry_type)
                result.append((path_str, type_str))
            
            return result
        except Exception as e:
            return error_result_from_exception(e)
    
    def get(self, path: str) -> ResultOrError[bytes]:
        """Get file contents.
        
        Args:
            path: File path to read
            
        Returns:
            File contents as bytes or ErrorResult if operation failed
        """
        try:
            posix_path = self._convert_path(path)
            return self._vfs.get(posix_path)
        except Exception as e:
            return error_result_from_exception(e)
    
    def get_text(self, path: str, encoding: str = 'utf-8') -> ResultOrError[Optional[str]]:
        """Get file contents as text.
        
        Args:
            path: File path to read
            encoding: Text encoding to use
            
        Returns:
            File contents as text, None if failed, or ErrorResult if operation failed
        """
        try:
            posix_path = self._convert_path(path)
            return self._vfs.get_text(posix_path, encoding)
        except Exception as e:
            return error_result_from_exception(e)
    
    def put(self, path: str, content: bytes, create_if_missing: bool = False) -> ResultOrError[bool]:
        """Put file contents.
        
        Args:
            path: File path to write
            content: File content as bytes
            create_if_missing: Create file if it doesn't exist
            
        Returns:
            Success status or ErrorResult if operation failed
        """
        try:
            posix_path = self._convert_path(path)
            return self._vfs.put(posix_path, content, create_if_missing)
        except Exception as e:
            return error_result_from_exception(e)
    
    def patch(self, path: str, range_tuple: Tuple[int, int], content: bytes, 
              session_id: Optional[str] = None) -> ResultOrError[str]:
        """Apply a patch to a file.
        
        Args:
            path: File path to patch
            range_tuple: (start, end) position tuple
            content: Replacement content
            session_id: Optional session ID
            
        Returns:
            Operation ID or ErrorResult if operation failed
        """
        try:
            posix_path = self._convert_path(path)
            return self._vfs.patch(posix_path, range_tuple, content, session_id)
        except Exception as e:
            return error_result_from_exception(e)
    
    def commit(self, message: str, op_id: Optional[str] = None, session_id: Optional[str] = None) -> ResultOrError[Dict[str, Any]]:
        """Commit patches.
        
        Args:
            message: Commit message
            op_id: Optional operation ID
            session_id: Optional session ID
            
        Returns:
            Commit status and message or ErrorResult if operation failed
        """
        try:
            return self._vfs.commit(message, op_id, session_id)
        except Exception as e:
            return error_result_from_exception(e)
    
    def abort(self, op_id: Optional[str] = None, session_id: Optional[str] = None) -> ResultOrError[Dict[str, Any]]:
        """Abort patches.
        
        Args:
            op_id: Optional operation ID
            session_id: Optional session ID
            
        Returns:
            Abort status and message or ErrorResult if operation failed
        """
        try:
            return self._vfs.abort(op_id, session_id)
        except Exception as e:
            return error_result_from_exception(e)
    
    def create_session(self) -> ResultOrError[str]:
        """Create a new edit session.
        
        Returns:
            Session ID or ErrorResult if operation failed
        """
        try:
            return self._vfs.create_session()
        except Exception as e:
            return error_result_from_exception(e)
    
    def list_sessions(self) -> ResultOrError[List[str]]:
        """List all active sessions.
        
        Returns:
            List of active session IDs or ErrorResult if operation failed
        """
        try:
            return self._vfs.list_sessions()
        except Exception as e:
            return error_result_from_exception(e)
    
    def to_vfs_path(self, local_path: str) -> ResultOrError[Optional[str]]:
        """Convert a local file system path to a VFS path if possible.
        
        Args:
            local_path: Local file system path to convert
            
        Returns:
            Equivalent VFS path as string if conversion is possible,
            None if the path cannot be mapped to this VFS,
            or ErrorResult if operation failed
        """
        try:
            from pathlib import Path
            result = self._vfs.to_vfs_path(Path(local_path))
            return str(result) if result is not None else None
        except Exception as e:
            return error_result_from_exception(e)
    
    def resolve_path(self, path: str) -> ResultOrError[Tuple[str, str]]:
        """Resolve a path to VFS and remaining path info.
        
        Args:
            path: Path to resolve
            
        Returns:
            Tuple with VFS service name and remaining path as strings
            or ErrorResult if operation failed
        """
        try:
            posix_path = self._convert_path(path)
            vfs, remaining_path = self._vfs.resolve_path(posix_path)
            return (vfs.name(), str(remaining_path))
        except Exception as e:
            return error_result_from_exception(e)
    
    def mount(self, path: str, vfs_name: str) -> ResultOrError[Tuple[bool, str]]:
        """Mount a VFS at the given path.
        
        Args:
            path: VFS mount point
            vfs_name: Name of VFS service to mount
            
        Returns:
            Success status and message or ErrorResult if operation failed
        """
        try:
            # Note: This is a simplified implementation
            # In a real scenario, you'd need to resolve vfs_name to actual VFS instance
            posix_path = self._convert_path(path)
            # For now, return not implemented
            return (False, "Mount operation not implemented in server")
        except Exception as e:
            return error_result_from_exception(e)
    
    def unmount(self, path: str) -> ResultOrError[bool]:
        """Unmount a VFS at the given path.
        
        Args:
            path: VFS mount point to unmount
            
        Returns:
            Success status or ErrorResult if operation failed
        """
        try:
            posix_path = self._convert_path(path)
            return self._vfs.unmount(posix_path)
        except Exception as e:
            return error_result_from_exception(e)
    
    def list_mounts(self) -> ResultOrError[Dict[str, str]]:
        """Get list of mount points.
        
        Returns:
            Dictionary of mount points (as strings) and their VFS service names
            or ErrorResult if operation failed
        """
        try:
            mounts = self._vfs.list_mounts()
            # Convert to string keys and VFS names
            result = {}
            for mount_path, vfs_instance in mounts.items():
                result[str(mount_path)] = vfs_instance.name()
            return result
        except Exception as e:
            return error_result_from_exception(e)
    
    def mkdir(self, path: str, parents: bool = False, exist_ok: bool = False) -> ResultOrError[bool]:
        """Create a directory.
        
        Args:
            path: Directory path to create
            parents: Create parent directories if they don't exist
            exist_ok: Don't raise error if directory already exists
            
        Returns:
            Success status or ErrorResult if operation failed
        """
        try:
            posix_path = self._convert_path(path)
            return self._vfs.mkdir(posix_path, parents, exist_ok)
        except Exception as e:
            return error_result_from_exception(e)
    
    def remove(self, path: str) -> ResultOrError[bool]:
        """Remove a file or directory.
        
        Args:
            path: Path to remove
            
        Returns:
            Success status or ErrorResult if operation failed
        """
        try:
            posix_path = self._convert_path(path)
            return self._vfs.remove(posix_path)
        except Exception as e:
            return error_result_from_exception(e)
    
    def mount_point(self) -> ResultOrError[str]:
        """Get the mount point of this VFS.
        
        Returns:
            Mount point path as string or ErrorResult if operation failed
        """
        try:
            return str(self._vfs.mount_point())
        except Exception as e:
            return error_result_from_exception(e)

def create_vfs_service(service_name:str, service_registry: ServiceRegistry) -> VFSServer:
    """Create a VFS service instance.
    
    Args:
        repo_path: Path to the repository
        **kwargs: Additional service configuration
        
    Returns:
        VFS service instance
    """
    repo_path = service_registry.config_service.get("vfs.root_path", None)
    if repo_path is None:
        raise ValueError("VFS repo_path not set in config service")
    return VFSServer(service_name, Path(repo_path))
