"""Repository VFS implementation.

This module provides a repository file system implementation that combines
local file system access with git repository functionality.
"""

from pathlib import PurePosixPath, Path
from typing import Dict, List, Optional, Tuple, Union, Any
import os

from .local_vfs import LocalVFS
from .git_vfs import GitVFS
from ...proto.service_vfs_protocol import ServiceVFSProtocol, EntryType


class RepoVFS(ServiceVFSProtocol):
    """Repository file system implementation of VFS service protocol.
    
    This class combines LocalVFS (for local work directory) and GitVFS
    (for git repository access) to provide unified access to git repositories.
    
    The .git/ path is automatically mounted to GitVFS, while other paths
    are forwarded to LocalVFS.
    """
    
    def __init__(self, repo_path: Path, mount_point: PurePosixPath, name: Optional[str] = None):
        """Initialize the repository file system VFS.
        
        Args:
            repo_path: Root path of the git repository
        """
        self.repo_path = repo_path.absolute()
        self._mount_point = mount_point
        if name:
            self._name = name
        else:
            self._name = f"repo:{self.repo_path.as_posix()}"
        
        # Verify it's a git repository
        if not os.path.exists(os.path.join(repo_path, '.git')):
            # 另一个可能的处理方案是日志中给出警告，failback to local_vfs
            raise ValueError(f"Not a git repository: {repo_path}")
        
        # Initialize components
        self._local_vfs = LocalVFS(repo_path, self._mount_point)    # 实际的实现是转发，.git 
        git_mount_point = self._mount_point.joinpath('.git')
        self._git_vfs = GitVFS(repo_path, git_mount_point)
        
        # Auto-mount .git/ to GitVFS (both relative and absolute paths)
        self._local_vfs.mount(git_mount_point, self._git_vfs)  # 相对路径
    
    def name(self) -> str:
        """Get the name of the VFS service."""
        return self._name

    def mount_point(self) -> PurePosixPath:
        """Get the root path of the VFS service."""
        return self._mount_point

    def to_vfs_path(self, local_path: Union[str, Path]) -> Optional[PurePosixPath]:
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
            
        Raises:
            ValueError: If the path format is invalid
        """
        # 委托给LocalVFS处理
        return self._local_vfs.to_vfs_path(local_path)

    def to_local_path(self, vfs_path: PurePosixPath) -> Optional[Path]:
        return self._local_vfs.to_local_path(vfs_path)

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
    
    def info(self, path: PurePosixPath) -> Optional[Dict[str, Any]]:
        """Get information about a path.
        
        Args:
            path: Path to get info for
            
        Returns:
            Path information
        """
        return self._local_vfs.info(path)
    
    def list(self, path: PurePosixPath, option: Dict[str, Any]) -> List[Tuple[PurePosixPath, EntryType]]:
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
    
    def remove(self, path: PurePosixPath, force: bool = False) -> bool:
        """Remove a file or directory.
        
        Args:
            path: Path to remove
            force: Force removal (ignore non-existent files)
            
        Returns:
            Success status
            
        Raises:
            OSError: If directory is not empty and recursive=False
            PermissionError: If VFS is readonly
        """
        return self._local_vfs.remove(path, force)
    
    def mkdir(self, path: PurePosixPath, parents: bool = False, exist_ok: bool = False) -> bool:
        """Create a directory.
        
        Args:
            path: Directory path to create
            parents: Create parent directories if they don't exist
            exist_ok: Don't raise error if directory already exists
            
        Returns:
            Success status
            
        Raises:
            FileExistsError: If directory exists and exist_ok=False
            FileNotFoundError: If parent doesn't exist and parents=False
            PermissionError: If VFS is readonly
        """
        return self._local_vfs.mkdir(path, parents, exist_ok)
    
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
    
