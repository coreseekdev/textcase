"""Git VFS implementation using pygit2.

This module provides a git file system implementation that uses pygit2
to access git repositories and provides read-only access to git trees.
"""

from pathlib import PurePosixPath
from typing import Dict, List, Optional, Tuple, Any
import os
import time

try:
    import pygit2
except ImportError:
    pygit2 = None

from ...proto.service_vfs_protocol import ServiceVFSProtocol


class GitVFS(ServiceVFSProtocol):
    """Git file system implementation using pygit2.
    
    This class provides read-only access to git repositories,
    supporting access by branch, tag, or commit hash.
    """
    
    def __init__(self, repo_path: str):
        """Initialize the git file system VFS.
        
        Args:
            repo_path: Path to the git repository
        """
        if pygit2 is None:
            raise ImportError("pygit2 is required for GitVFS")
            
        self.repo_path = repo_path
        self._repo = pygit2.Repository(repo_path)
        self._name = f"git:{repo_path}"
        self._mounts = {}
    
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
        # Check for mounted VFS
        for mount_path, vfs in self._mounts.items():
            if str(path).startswith(mount_path + '/'):
                remaining = PurePosixPath(str(path)[len(mount_path)+1:])
                return vfs.resolve_path(remaining)
        
        return self, path
    
    def mount(self, path: PurePosixPath, vfs: 'ServiceVFSProtocol') -> Tuple[bool, str]:
        """Mount a VFS at the given path."""
        mount_path = str(path)
        if mount_path in self._mounts:
            return False, f"Path {mount_path} already mounted"
        
        self._mounts[mount_path] = vfs
        return True, f"Mounted {vfs.name()} at {mount_path}"
    
    def unmount(self, path: PurePosixPath) -> bool:
        """Unmount a VFS at the given path."""
        mount_path = str(path)
        if mount_path in self._mounts:
            del self._mounts[mount_path]
            return True
        return False
    
    def mounts(self) -> Dict[str, 'ServiceVFSProtocol']:
        """Get list of mount points."""
        return self._mounts.copy()
    
    def readonly(self) -> bool:
        """Check if the VFS is read-only."""
        return True  # Git VFS is always read-only
    
    def _resolve_commit(self, ref: str) -> pygit2.Commit:
        """Resolve a reference (branch, tag, or commit hash) to a commit.
        
        Args:
            ref: Reference to resolve
            
        Returns:
            Commit object
        """
        try:
            # Try to resolve as a reference first (branch/tag)
            try:
                reference = self._repo.lookup_reference(f"refs/heads/{ref}")
                return self._repo[reference.target]
            except KeyError:
                try:
                    reference = self._repo.lookup_reference(f"refs/tags/{ref}")
                    return self._repo[reference.target]
                except KeyError:
                    # Try as direct commit hash
                    return self._repo[ref]
        except (KeyError, ValueError) as e:
            raise ValueError(f"Cannot resolve reference '{ref}': {e}")
    
    def _get_tree_entry(self, commit: pygit2.Commit, path: PurePosixPath) -> Optional[Any]:
        """Get a tree entry from a commit at the given path.
        
        Args:
            commit: Commit object
            path: Path within the tree
            
        Returns:
            Tree entry or None if not found
        """
        if str(path) == '.' or str(path) == '':
            return commit.tree
        
        try:
            return commit.tree[str(path)]
        except KeyError:
            return None
    
    def info(self, path: PurePosixPath) -> Dict[str, Any]:
        """Get information about a path.
        
        Path format: ref/path/to/file
        where ref can be branch name, tag name, or commit hash
        
        Args:
            path: Path to get info for
            
        Returns:
            Path information
        """
        parts = path.parts
        if not parts:
            # Root path - list available refs
            return {
                'type': 'directory',
                'path': str(path),
                'size': 0,
                'mtime': time.time(),
                'is_git_root': True
            }
        
        ref = parts[0]
        file_path = PurePosixPath(*parts[1:]) if len(parts) > 1 else PurePosixPath('.')
        
        try:
            commit = self._resolve_commit(ref)
            entry = self._get_tree_entry(commit, file_path)
            
            if entry is None:
                raise FileNotFoundError(f"Path not found: {path}")
            
            if isinstance(entry, pygit2.Tree):
                return {
                    'type': 'directory',
                    'path': str(path),
                    'size': len(entry),
                    'mtime': commit.commit_time,
                    'commit_hash': str(commit.id),
                    'ref': ref
                }
            else:
                return {
                    'type': 'file',
                    'path': str(path),
                    'size': entry.filemode,
                    'mtime': commit.commit_time,
                    'commit_hash': str(commit.id),
                    'ref': ref
                }
        except Exception as e:
            raise ValueError(f"Error accessing git path {path}: {e}")
    
    def list(self, path: PurePosixPath, option: Dict[str, Any]) -> Dict[str, Any]:
        """List contents of a directory.
        
        Args:
            path: Directory path to list
            option: Listing options
            
        Returns:
            Dictionary with directory contents
        """
        parts = path.parts
        
        if not parts:
            # Root path - list available refs
            refs = []
            
            # List branches
            for branch_name in self._repo.branches:
                refs.append({
                    'name': branch_name,
                    'type': 'directory',
                    'ref_type': 'branch'
                })
            
            # List tags
            for tag_name in [ref[10:] for ref in self._repo.references if ref.startswith('refs/tags/')]:
                refs.append({
                    'name': tag_name,
                    'type': 'directory',
                    'ref_type': 'tag'
                })
            
            return {
                'items': refs,
                'path': str(path),
                'total': len(refs)
            }
        
        ref = parts[0]
        file_path = PurePosixPath(*parts[1:]) if len(parts) > 1 else PurePosixPath('.')
        
        try:
            commit = self._resolve_commit(ref)
            entry = self._get_tree_entry(commit, file_path)
            
            if entry is None or not isinstance(entry, pygit2.Tree):
                raise ValueError(f"Path is not a directory: {path}")
            
            items = []
            for item in entry:
                item_info = {
                    'name': item.name,
                    'type': 'directory' if item.filemode == pygit2.GIT_FILEMODE_TREE else 'file',
                    'size': 0 if item.filemode == pygit2.GIT_FILEMODE_TREE else len(self._repo[item.id].data),
                    'mtime': commit.commit_time
                }
                items.append(item_info)
            
            return {
                'items': items,
                'path': str(path),
                'total': len(items)
            }
        except Exception as e:
            raise ValueError(f"Error listing git path {path}: {e}")
    
    def get(self, path: PurePosixPath) -> bytes:
        """Get file contents.
        
        Args:
            path: File path to read
            
        Returns:
            File contents
        """
        parts = path.parts
        if len(parts) < 2:
            raise ValueError(f"Invalid git path: {path}")
        
        ref = parts[0]
        file_path = PurePosixPath(*parts[1:])
        
        try:
            commit = self._resolve_commit(ref)
            entry = self._get_tree_entry(commit, file_path)
            
            if entry is None:
                raise FileNotFoundError(f"File not found: {path}")
            
            if isinstance(entry, pygit2.Tree):
                raise ValueError(f"Path is a directory, not a file: {path}")
            
            blob = self._repo[entry.id]
            return blob.data
        except Exception as e:
            raise ValueError(f"Error reading git file {path}: {e}")
    
    def get_text(self, path: PurePosixPath, encoding: str = 'utf-8') -> Optional[str]:
        """Get file contents as text.
        
        Args:
            path: File path to read
            encoding: Text encoding to use
            
        Returns:
            File contents as text
        """
        try:
            content = self.get(path)
            return content.decode(encoding)
        except UnicodeDecodeError:
            return None
    
    def put(self, path: PurePosixPath, content: bytes, create_if_missing: bool = False) -> bool:
        """Put file contents (not supported for git VFS).
        
        Args:
            path: File path to write
            content: File content
            create_if_missing: Create file if it doesn't exist
            
        Returns:
            Always False (git VFS is read-only)
        """
        return False
    
    def patch(self, path: PurePosixPath, range: Tuple[int, int], content: bytes, 
              session_id: Optional[ServiceVFSProtocol.SessionId] = None) -> ServiceVFSProtocol.OperationId:
        """Apply a patch to a file (not supported for git VFS)."""
        raise NotImplementedError("Git VFS is read-only")
    
    def commit(self, op_id: Optional[ServiceVFSProtocol.OperationId] = None, 
               session_id: Optional[ServiceVFSProtocol.SessionId] = None) -> Dict[str, Any]:
        """Commit patches (not supported for git VFS)."""
        raise NotImplementedError("Git VFS is read-only")
    
    def abort(self, op_id: Optional[ServiceVFSProtocol.OperationId] = None, 
              session_id: Optional[ServiceVFSProtocol.SessionId] = None) -> Dict[str, Any]:
        """Abort patches (not supported for git VFS)."""
        raise NotImplementedError("Git VFS is read-only")
    
    def create_session(self) -> ServiceVFSProtocol.SessionId:
        """Create a new edit session (not supported for git VFS)."""
        raise NotImplementedError("Git VFS is read-only")
    
    def list_sessions(self) -> List[ServiceVFSProtocol.SessionId]:
        """List all active sessions (not supported for git VFS)."""
        return []
    
    def close_session(self, session_id: ServiceVFSProtocol.SessionId) -> bool:
        """Close an edit session (not supported for git VFS)."""
        return False