from pathlib import PurePosixPath
from typing import Dict, List, Optional, Tuple
import os
# Using the new VFS implementation
from .vfs.local_vfs import LocalVFS
from .vfs.git_vfs import GitVFS
from .vfs.repo_vfs import RepoVFS


class VFSResolver:
    """VFS resolver that creates VFS instances based on path patterns."""
    
    def __init__(self):
        pass
    
    def create_vfs(self, path: str):
        """Create a VFS instance based on the path.
        
        Args:
            path: File system path
            
        Returns:
            VFS instance (LocalVFS, GitVFS, or RepoVFS)
        """
        abs_path = os.path.abspath(path)
        
        # Check if it's a git repository
        if self._is_git_repo(abs_path):
            return RepoVFS(abs_path)
        else:
            return LocalVFS(abs_path)
    
    def _is_git_repo(self, path: str) -> bool:
        """Check if a path is a git repository."""
        return os.path.exists(os.path.join(path, '.git'))


class PathResolver:
    """Path resolver that manages VFS mounts and resolves paths."""
    
    def __init__(self, root_path: str):
        self.root_path = os.path.abspath(root_path)
        self.mounts: Dict[str, object] = {}  # Using object as a generic type for VFS instances
        self.vfs_resolver = VFSResolver()
        
        # Create edit manager for the root path
        patches_dir = os.path.join(self.root_path, '.patches')
        self.edit_manager = EditManager(patches_dir)
        self.vfs_resolver.set_edit_manager(self.edit_manager)
        
        # Mount the root VFS
        root_vfs = self.vfs_resolver.create_vfs(self.root_path)
        self.mounts['/'] = root_vfs
    
    def resolve_path(self, path: PurePosixPath) -> Tuple[object, PurePosixPath]:
        """Resolve a path to a VFS and remaining path.
        
        Args:
            path: The path to resolve
            
        Returns:
            Tuple of (VFS instance, remaining path)
        """
        path_str = str(path)
        
        # Find the longest matching mount point
        best_mount = '/'
        for mount_point in self.mounts:
            if path_str.startswith(mount_point) and len(mount_point) > len(best_mount):
                best_mount = mount_point
        
        vfs = self.mounts[best_mount]
        
        # Calculate remaining path
        if best_mount == '/':
            remaining_path = path
        else:
            # Remove mount point prefix
            remaining_str = path_str[len(best_mount):].lstrip('/')
            remaining_path = PurePosixPath(remaining_str) if remaining_str else PurePosixPath('.')
        
        return vfs, remaining_path
    
    def mount(self, path: PurePosixPath, local_path: str) -> None:
        """Mount a VFS at the given path.
        
        Args:
            path: Mount point path
            local_path: Local file system path to mount
        """
        mount_point = str(path)
        if not mount_point.startswith('/'):
            mount_point = '/' + mount_point
        
        vfs = self.vfs_resolver.create_vfs(local_path)
        self.mounts[mount_point] = vfs
    
    def unmount(self, path: PurePosixPath) -> None:
        """Unmount a VFS at the given path.
        
        Args:
            path: Mount point path to unmount
        """
        mount_point = str(path)
        if not mount_point.startswith('/'):
            mount_point = '/' + mount_point
        
        if mount_point in self.mounts and mount_point != '/':
            del self.mounts[mount_point]
    
    def mounts_list(self) -> List[PurePosixPath]:
        """Get list of mount points.
        
        Returns:
            List of mount point paths
        """
        return [PurePosixPath(mount) for mount in self.mounts.keys()]
    
    def info(self, path: PurePosixPath) -> Dict:
        """Get information about a path."""
        vfs, remaining_path = self.resolve_path(path)
        return vfs.info(remaining_path)
    
    def list(self, path: PurePosixPath, option: Optional[Dict] = None) -> List[PurePosixPath]:
        """List contents of a directory."""
        vfs, remaining_path = self.resolve_path(path)
        items = vfs.list(remaining_path, option)
        
        # Convert relative paths back to absolute VFS paths
        base_path = path if str(path) != '.' else PurePosixPath('/')
        result = []
        for item in items:
            if str(remaining_path) == '.':
                # Direct listing from mount point
                result.append(base_path / item.name)
            else:
                # Listing from subdirectory
                result.append(base_path / item.relative_to(remaining_path))
        
        return result
    
    def get(self, path: PurePosixPath) -> bytes:
        """Get file contents."""
        vfs, remaining_path = self.resolve_path(path)
        return vfs.get(remaining_path)
    
    def patch(self, path: PurePosixPath, range_: Tuple[int, int], data: bytes, session_id: Optional[str] = None) -> str:
        """Apply a patch to a file."""
        vfs, remaining_path = self.resolve_path(path)
        return vfs.patch(remaining_path, range_, data, session_id)
    
    def put(self, path: PurePosixPath, data: bytes) -> None:
        """Put file contents."""
        vfs, remaining_path = self.resolve_path(path)
        vfs.put(remaining_path, data)
    
    def commit(self, op_id: Optional[str] = None, session_id: Optional[str] = None) -> Tuple[bool, str]:
        """Commit patches across all VFS instances."""
        results = []
        errors = []
        
        for vfs in self.mounts.values():
            try:
                success, message = vfs.commit(op_id, session_id)
                results.append(success)
                if not success:
                    errors.append(message)
            except Exception as e:
                results.append(False)
                errors.append(str(e))
        
        if all(results):
            return True, "All commits successful"
        else:
            return False, f"Some commits failed: {'; '.join(errors)}"
    
    def abort(self, op_id: Optional[str] = None, session_id: Optional[str] = None) -> Tuple[bool, str]:
        """Abort patches across all VFS instances."""
        results = []
        errors = []
        
        for vfs in self.mounts.values():
            try:
                success, message = vfs.abort(op_id, session_id)
                results.append(success)
                if not success:
                    errors.append(message)
            except Exception as e:
                results.append(False)
                errors.append(str(e))
        
        if all(results):
            return True, "All aborts successful"
        else:
            return False, f"Some aborts failed: {'; '.join(errors)}"