"""Repository VFS implementation.

This module provides a repository file system implementation that combines
local file system access with git repository functionality.
"""

from pathlib import PurePosixPath
from typing import Dict, List, Optional, Tuple, Any
import os

from .local_vfs import LocalVFS
from .git_vfs import GitVFS
from ...proto.service_vfs_protocol import ServiceVFSProtocol


class RepoVFS(ServiceVFSProtocol):
    """Repository file system implementation of VFS service protocol.
    
    This class combines LocalVFS (for local work directory) and GitVFS
    (for git repository access) to provide unified access to git repositories.
    
    The .git/ path is automatically mounted to GitVFS, while other paths
    are forwarded to LocalVFS.
    """
    
    def __init__(self, repo_path: str):
        """Initialize the repository file system VFS.
        
        Args:
            repo_path: Root path of the git repository
        """
        self.repo_path = os.path.abspath(repo_path)
        self._name = f"repo:{self.repo_path}"
        
        # Verify it's a git repository
        if not os.path.exists(os.path.join(repo_path, '.git')):
            # 另一个可能的处理方案是日志中给出警告，failback to local_vfs
            raise ValueError(f"Not a git repository: {repo_path}")
        
        # Initialize components
        self._local_vfs = LocalVFS(repo_path)
        self._git_vfs = GitVFS(repo_path)
        
        # Auto-mount .git/ to GitVFS
        self._local_vfs.mount(PurePosixPath('.git'), self._git_vfs)
    
    def name(self) -> str:
        """Get the name of the VFS service."""
        return self._name
    
    def resolve_path(self, path: PurePosixPath) -> Tuple['ServiceVFSProtocol', PurePosixPath]:
        """Resolve a path to VFS and remaining path info.
        
        Args:
            path: Path to resolve
            
        Returns:
            Tuple with VFS service instance and remaining path
        """
        # Forward to LocalVFS which handles the .git mount
        return self._local_vfs.resolve_path(path)
    
    def mount(self, path: PurePosixPath, vfs: 'ServiceVFSProtocol') -> Tuple[bool, str]:
        """Mount a VFS at the given path.
        
        Args:
            path: VFS mount point
            vfs: VFS service instance
            
        Returns:
            Success status and message
        """
        return self._local_vfs.mount(path, vfs)
    
    def unmount(self, path: PurePosixPath) -> bool:
        """Unmount a VFS at the given path.
        
        Args:
            path: VFS mount point to unmount
            
        Returns:
            Success status
        """
        return self._local_vfs.unmount(path)
    
    def mounts(self) -> Dict[str, 'ServiceVFSProtocol']:
        """Get list of mount points.
        
        Returns:
            Dictionary of mount points
        """
        return self._local_vfs.mounts()
    
    def readonly(self) -> bool:
        """Check if the VFS is read-only."""
        return self._local_vfs.readonly()
    
    def info(self, path: PurePosixPath) -> Dict[str, Any]:
        """Get information about a path.
        
        Args:
            path: Path to get info for
            
        Returns:
            Path information
        """
        return self._local_vfs.info(path)
    
    def list(self, path: PurePosixPath, option: Dict[str, Any]) -> Dict[str, Any]:
        """List contents of a directory.
        
        Args:
            path: Directory path to list
            option: Listing options
            
        Returns:
            Dictionary with directory contents
        """
        return self._local_vfs.list(path, option)
    
    def get(self, path: PurePosixPath) -> bytes:
        """Get file contents.
        
        Args:
            path: File path to read
            
        Returns:
            File contents
        """
        return self._local_vfs.get(path)
    
    def get_text(self, path: PurePosixPath, encoding: str = 'utf-8') -> Optional[str]:
        """Get file contents as text.
        
        Args:
            path: File path to read
            encoding: Text encoding to use
            
        Returns:
            File contents as text
        """
        return self._local_vfs.get_text(path, encoding)
    
    def put(self, path: PurePosixPath, content: bytes, create_if_missing: bool = False) -> bool:
        """Put file contents.
        
        Args:
            path: File path to write
            content: File content
            create_if_missing: Create file if it doesn't exist
            
        Returns:
            Success status
        """
        return self._local_vfs.put(path, content, create_if_missing)
    
    def patch(self, path: PurePosixPath, range: Tuple[int, int], content: bytes, 
              session_id: Optional[ServiceVFSProtocol.SessionId] = None) -> ServiceVFSProtocol.OperationId:
        """Apply a patch to a file.
        
        Args:
            path: File path to patch
            range: Start and end positions of the range
            content: Replacement content
            session_id: Optional session ID
            
        Returns:
            Operation ID
        """
        return self._local_vfs.patch(path, range, content, session_id)
    
    def commit(self, op_id: Optional[ServiceVFSProtocol.OperationId] = None, 
               session_id: Optional[ServiceVFSProtocol.SessionId] = None) -> Dict[str, Any]:
        """Commit patches.
        
        Args:
            op_id: Optional operation ID
            session_id: Optional session ID
            
        Returns:
            Commit status and message
        """
        return self._local_vfs.commit(op_id, session_id)
    
    def abort(self, op_id: Optional[ServiceVFSProtocol.OperationId] = None, 
              session_id: Optional[ServiceVFSProtocol.SessionId] = None) -> Dict[str, Any]:
        """Abort patches.
        
        Args:
            op_id: Optional operation ID
            session_id: Optional session ID
            
        Returns:
            Abort status and message
        """
        return self._local_vfs.abort(op_id, session_id)
    
    def create_session(self) -> ServiceVFSProtocol.SessionId:
        """Create a new edit session.
        
        Returns:
            Session ID
        """
        return self._local_vfs.create_session()
    
    def list_sessions(self) -> List[ServiceVFSProtocol.SessionId]:
        """List all active sessions.
        
        Returns:
            List of active sessions
        """
        return self._local_vfs.list_sessions()
    
    def close_session(self, session_id: ServiceVFSProtocol.SessionId) -> bool:
        """Close an edit session.
        
        Args:
            session_id: Session ID to close
            
        Returns:
            Success status
        """
        return self._local_vfs.close_session(session_id)