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

from ...proto.service_vfs_protocol import ServiceVFSProtocol, EntryType


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
        return False, "Mounting not supported"
    
    def unmount(self, path: PurePosixPath) -> bool:
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
        
        Path formats:
        - / - Root directory
        - /tag - Tags directory
        - /tag/{tag_name} - Link to tree
        - /branch - Branches directory
        - /branch/{branch_name} - Link to tree
        - /tree - Trees directory
        - /tree/{ref}/path/to/file - File or directory in a specific tree
        - /{ref}/path/to/file - Legacy format (still supported)
        
        Args:
            path: Path to get info for
            
        Returns:
            Path information
        """
        parts = path.parts
        if not parts:
            # Root path
            return {
                'type': 'directory',
                'path': str(path),
                'size': 0,
                'mtime': time.time(),
                'is_git_root': True
            }
        
        # Handle special directories: tag, branch, tree
        if parts[0] == 'tag':
            if len(parts) == 1:
                # Tags directory
                return {
                    'type': 'directory',
                    'path': str(path),
                    'size': 0,
                    'mtime': time.time(),
                    'description': 'Repository tags'
                }
            elif len(parts) == 2:
                # Specific tag - this is a link
                tag_name = parts[1]
                # Convert underscores back to slashes if needed
                original_tag_name = tag_name.replace('_', '/')
                
                # Check if tag exists
                try:
                    ref = self._repo.lookup_reference(f"refs/tags/{original_tag_name}")
                    target_commit = self._repo[ref.target]
                    return {
                        'type': 'link',
                        'path': str(path),
                        'target': f"tree/{original_tag_name}",
                        'size': 0,
                        'mtime': target_commit.commit_time,
                        'ref_type': 'tag',
                        'commit_hash': str(target_commit.id)
                    }
                except KeyError:
                    raise FileNotFoundError(f"Tag not found: {tag_name}")
            else:
                raise ValueError(f"Invalid tag path: {path}")
                
        elif parts[0] == 'branch':
            if len(parts) == 1:
                # Branches directory
                return {
                    'type': 'directory',
                    'path': str(path),
                    'size': 0,
                    'mtime': time.time(),
                    'description': 'Repository branches'
                }
            elif len(parts) == 2:
                # Specific branch - this is a link
                branch_name = parts[1]
                # Convert underscores back to slashes if needed
                original_branch_name = branch_name.replace('_', '/')
                
                # Check if branch exists
                try:
                    ref = self._repo.lookup_reference(f"refs/heads/{original_branch_name}")
                    target_commit = self._repo[ref.target]
                    return {
                        'type': 'link',
                        'path': str(path),
                        'target': f"tree/{original_branch_name}",
                        'size': 0,
                        'mtime': target_commit.commit_time,
                        'ref_type': 'branch',
                        'commit_hash': str(target_commit.id)
                    }
                except KeyError:
                    raise FileNotFoundError(f"Branch not found: {branch_name}")
            else:
                raise ValueError(f"Invalid branch path: {path}")
                
        elif parts[0] == 'tree':
            if len(parts) == 1:
                # Trees directory
                return {
                    'type': 'directory',
                    'path': str(path),
                    'size': 0,
                    'mtime': time.time(),
                    'description': 'Repository trees by commit hash'
                }
            else:
                # Specific tree (commit/branch/tag)
                ref = parts[1]
                file_path = PurePosixPath(*parts[2:]) if len(parts) > 2 else PurePosixPath('.')
                
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
        
        # Legacy format support: ref/path/to/file
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
    
    def list(self, path: PurePosixPath, option: Dict[str, Any]) -> List[Tuple[PurePosixPath, EntryType]]:
        """List contents of a directory.
        
        Args:
            path: Directory path to list
            option: Listing options
            
        Returns:
            List of tuples containing (path, entry_type)
        """
        parts = path.parts
        
        if not parts:
            # Root path - list available top-level directories
            return [
                (PurePosixPath('tag'), EntryType.DIR),
                (PurePosixPath('branch'), EntryType.DIR),
                (PurePosixPath('tree'), EntryType.DIR)
            ]
        
        # Handle special directories: tag, branch, tree
        if parts[0] == 'tag':
            if len(parts) == 1:
                # List all tags
                result = []
                for tag_name in [ref[10:] for ref in self._repo.references if ref.startswith('refs/tags/')]:
                    # Replace slashes with underscores in tag names
                    safe_tag_name = tag_name.replace('/', '_')
                    result.append((PurePosixPath(safe_tag_name), EntryType.LINK))
                return result
            else:
                # This is a specific tag, which should be a link to tree
                raise ValueError(f"Tags are links to trees, not directories: {path}")
                
        elif parts[0] == 'branch':
            if len(parts) == 1:
                # List all branches
                result = []
                for branch_name in self._repo.branches:
                    # Replace slashes with underscores in branch names
                    safe_branch_name = branch_name.replace('/', '_')
                    result.append((PurePosixPath(safe_branch_name), EntryType.LINK))
                return result
            else:
                # This is a specific branch, which should be a link to tree
                raise ValueError(f"Branches are links to trees, not directories: {path}")
                
        elif parts[0] == 'tree':
            if len(parts) == 1:
                # List all commits (this could be expensive, so we'll just show recent ones)
                result = []
                # Get recent commits (limit to 20)
                for commit in list(self._repo.walk(self._repo.head.target, pygit2.GIT_SORT_TIME))[:20]:
                    # Short commit hash as directory name
                    result.append((PurePosixPath(str(commit.id)[:10]), EntryType.DIR))
                return result
            else:
                # This is a specific tree (commit/branch/tag)
                ref = parts[1]
                file_path = PurePosixPath(*parts[2:]) if len(parts) > 2 else PurePosixPath('.')
                
                try:
                    commit = self._resolve_commit(ref)
                    entry = self._get_tree_entry(commit, file_path)
                    
                    if entry is None or not isinstance(entry, pygit2.Tree):
                        raise ValueError(f"Path is not a directory: {path}")
                    
                    result = []
                    for item in entry:
                        entry_type = EntryType.DIR if item.filemode == pygit2.GIT_FILEMODE_TREE else EntryType.FILE
                        result.append((PurePosixPath(item.name), entry_type))
                    
                    return result
                except Exception as e:
                    raise ValueError(f"Error listing git path {path}: {e}")
        
        # Legacy format support: ref/path/to/file
        ref = parts[0]
        file_path = PurePosixPath(*parts[1:]) if len(parts) > 1 else PurePosixPath('.')
        
        try:
            commit = self._resolve_commit(ref)
            entry = self._get_tree_entry(commit, file_path)
            
            if entry is None or not isinstance(entry, pygit2.Tree):
                raise ValueError(f"Path is not a directory: {path}")
            
            result = []
            for item in entry:
                entry_type = EntryType.DIR if item.filemode == pygit2.GIT_FILEMODE_TREE else EntryType.FILE
                result.append((PurePosixPath(item.name), entry_type))
            
            return result
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
        if len(parts) < 1:
            raise ValueError(f"Invalid git path: {path}")
        
        # Handle special directories: tag, branch, tree
        if parts[0] == 'tag':
            if len(parts) != 2:
                raise ValueError(f"Invalid tag path: {path}")
            
            tag_name = parts[1]
            # Convert underscores back to slashes if needed
            original_tag_name = tag_name.replace('_', '/')
            
            # Check if tag exists
            try:
                self._repo.lookup_reference(f"refs/tags/{original_tag_name}")
                # Return the link target as bytes
                return f"tree/{original_tag_name}".encode('utf-8')
            except KeyError:
                raise FileNotFoundError(f"Tag not found: {tag_name}")
                
        elif parts[0] == 'branch':
            if len(parts) != 2:
                raise ValueError(f"Invalid branch path: {path}")
            
            branch_name = parts[1]
            # Convert underscores back to slashes if needed
            original_branch_name = branch_name.replace('_', '/')
            
            # Check if branch exists
            try:
                self._repo.lookup_reference(f"refs/heads/{original_branch_name}")
                # Return the link target as bytes
                return f"tree/{original_branch_name}".encode('utf-8')
            except KeyError:
                raise FileNotFoundError(f"Branch not found: {branch_name}")
                
        elif parts[0] == 'tree':
            if len(parts) < 3:
                raise ValueError(f"Invalid tree path: {path}")
            
            ref = parts[1]
            file_path = PurePosixPath(*parts[2:])
            
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
        
        # Legacy format support: ref/path/to/file
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