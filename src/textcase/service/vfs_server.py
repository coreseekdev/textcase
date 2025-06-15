"""VFS Server implementation for zerorpc.

This module provides a zerorpc-compatible VFS server that wraps
the existing VFS implementations and handles exception serialization
for proper client-side reconstruction.
"""

import json
import traceback
from pathlib import PurePosixPath, Path
from typing import Dict, List, Optional, Tuple, Any, Union

from ..core.vfs.repo_vfs import RepoVFS
from ..proto.service_vfs_protocol import ServiceVFSProtocol, EntryType
from ..proto.service_registry_protocol import ServiceRegistry

class VFSServerException(Exception):
    """Custom exception for VFS server errors.
    
    This exception carries the original exception type and message
    for proper reconstruction on the client side.
    """
    
    def __init__(self, exception_type: str, message: str, traceback_str: str = None):
        self.exception_type = exception_type
        self.original_message = message
        self.traceback_str = traceback_str
        super().__init__(f"{exception_type}: {message}")
    
    def to_dict(self) -> Dict[str, str]:
        """Convert exception to dictionary for serialization."""
        return {
            'exception_type': self.exception_type,
            'message': self.original_message,
            'traceback': self.traceback_str or ''
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, str]) -> 'VFSServerException':
        """Create exception from dictionary."""
        return cls(
            data['exception_type'],
            data['message'],
            data.get('traceback', '')
        )


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
    
    def _handle_exception(self, e: Exception) -> VFSServerException:
        """Convert exception to VFSServerException for serialization.
        
        Args:
            e: Original exception
            
        Returns:
            VFSServerException with original exception info
        """
        exception_type = type(e).__name__
        message = str(e)
        traceback_str = traceback.format_exc()
        
        return VFSServerException(exception_type, message, traceback_str)
    
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
        """Check if the VFS is read-only.
        
        Returns:
            True if read-only, False otherwise
        """
        try:
            return self._vfs.readonly()
        except Exception as e:
            raise self._handle_exception(e)
    
    def info(self, path: str) -> Dict[str, Any]:
        """Get information about a path.
        
        Args:
            path: Path to get info for
            
        Returns:
            Path information
        """
        try:
            posix_path = self._convert_path(path)
            return self._vfs.info(posix_path)
        except Exception as e:
            raise self._handle_exception(e)
    
    def list(self, path: str, option: Optional[Dict[str, Any]] = None) -> List[Tuple[str, str]]:
        """List contents of a directory.
        
        Args:
            path: Directory path to list
            option: Optional listing options
            
        Returns:
            List of (path, entry_type) tuples as strings
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
            raise self._handle_exception(e)
    
    def get(self, path: str) -> bytes:
        """Get file contents.
        
        Args:
            path: File path to read
            
        Returns:
            File contents as bytes
        """
        try:
            posix_path = self._convert_path(path)
            return self._vfs.get(posix_path)
        except Exception as e:
            raise self._handle_exception(e)
    
    def get_text(self, path: str, encoding: str = 'utf-8') -> Optional[str]:
        """Get file contents as text.
        
        Args:
            path: File path to read
            encoding: Text encoding to use
            
        Returns:
            File contents as text, or None if failed
        """
        try:
            posix_path = self._convert_path(path)
            return self._vfs.get_text(posix_path, encoding)
        except Exception as e:
            raise self._handle_exception(e)
    
    def put(self, path: str, content: bytes, create_if_missing: bool = False) -> bool:
        """Put file contents.
        
        Args:
            path: File path to write
            content: File content as bytes
            create_if_missing: Create file if it doesn't exist
            
        Returns:
            Success status
        """
        try:
            posix_path = self._convert_path(path)
            return self._vfs.put(posix_path, content, create_if_missing)
        except Exception as e:
            raise self._handle_exception(e)
    
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
        try:
            posix_path = self._convert_path(path)
            return self._vfs.patch(posix_path, range_tuple, content, session_id)
        except Exception as e:
            raise self._handle_exception(e)
    
    def commit(self, message: str, op_id: Optional[str] = None, session_id: Optional[str] = None) -> Dict[str, Any]:
        """Commit patches.
        
        Args:
            message: Commit message
            op_id: Optional operation ID
            session_id: Optional session ID
            
        Returns:
            Commit status and message
        """
        try:
            return self._vfs.commit(message, op_id, session_id)
        except Exception as e:
            raise self._handle_exception(e)
    
    def abort(self, op_id: Optional[str] = None, session_id: Optional[str] = None) -> Dict[str, Any]:
        """Abort patches.
        
        Args:
            op_id: Optional operation ID
            session_id: Optional session ID
            
        Returns:
            Abort status and message
        """
        try:
            return self._vfs.abort(op_id, session_id)
        except Exception as e:
            raise self._handle_exception(e)
    
    def create_session(self) -> str:
        """Create a new edit session.
        
        Returns:
            Session ID
        """
        try:
            return self._vfs.create_session()
        except Exception as e:
            raise self._handle_exception(e)
    
    def list_sessions(self) -> List[str]:
        """List all active sessions.
        
        Returns:
            List of active session IDs
        """
        try:
            return self._vfs.list_sessions()
        except Exception as e:
            raise self._handle_exception(e)
    
    def to_vfs_path(self, local_path: str) -> Optional[str]:
        """Convert a local file system path to a VFS path if possible.
        
        Args:
            local_path: Local file system path to convert
            
        Returns:
            Equivalent VFS path as string if conversion is possible,
            None if the path cannot be mapped to this VFS
        """
        try:
            from pathlib import Path
            result = self._vfs.to_vfs_path(Path(local_path))
            return str(result) if result is not None else None
        except Exception as e:
            raise self._handle_exception(e)
    
    def resolve_path(self, path: str) -> Tuple[str, str]:
        """Resolve a path to VFS and remaining path info.
        
        Args:
            path: Path to resolve
            
        Returns:
            Tuple with VFS service name and remaining path as strings
        """
        try:
            posix_path = self._convert_path(path)
            vfs, remaining_path = self._vfs.resolve_path(posix_path)
            return (vfs.name(), str(remaining_path))
        except Exception as e:
            raise self._handle_exception(e)
    
    def mount(self, path: str, vfs_name: str) -> Tuple[bool, str]:
        """Mount a VFS at the given path.
        
        Args:
            path: VFS mount point
            vfs_name: Name of VFS service to mount
            
        Returns:
            Success status and message
        """
        try:
            # Note: This is a simplified implementation
            # In a real scenario, you'd need to resolve vfs_name to actual VFS instance
            posix_path = self._convert_path(path)
            # For now, return not implemented
            return (False, "Mount operation not implemented in server")
        except Exception as e:
            raise self._handle_exception(e)
    
    def unmount(self, path: str) -> bool:
        """Unmount a VFS at the given path.
        
        Args:
            path: VFS mount point to unmount
            
        Returns:
            Success status
        """
        try:
            posix_path = self._convert_path(path)
            return self._vfs.unmount(posix_path)
        except Exception as e:
            raise self._handle_exception(e)
    
    def list_mounts(self) -> Dict[str, str]:
        """Get list of mount points.
        
        Returns:
            Dictionary of mount points (as strings) and their VFS service names
        """
        try:
            mounts = self._vfs.list_mounts()
            # Convert to string keys and VFS names
            result = {}
            for mount_path, vfs_instance in mounts.items():
                result[str(mount_path)] = vfs_instance.name()
            return result
        except Exception as e:
            raise self._handle_exception(e)
    
    def mkdir(self, path: str, parents: bool = False, exist_ok: bool = False) -> bool:
        """Create a directory.
        
        Args:
            path: Directory path to create
            parents: Create parent directories if they don't exist
            exist_ok: Don't raise error if directory already exists
            
        Returns:
            Success status
        """
        try:
            posix_path = self._convert_path(path)
            return self._vfs.mkdir(posix_path, parents, exist_ok)
        except Exception as e:
            raise self._handle_exception(e)
    
    def remove(self, path: str) -> bool:
        """Remove a file or directory.
        
        Args:
            path: Path to remove
            
        Returns:
            Success status
        """
        try:
            posix_path = self._convert_path(path)
            return self._vfs.remove(posix_path)
        except Exception as e:
            raise self._handle_exception(e)
    
    def mount_point(self) -> str:
        """Get the mount point of this VFS.
        
        Returns:
            Mount point path as string
        """
        try:
            return str(self._vfs.mount_point())
        except Exception as e:
            raise self._handle_exception(e)

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
