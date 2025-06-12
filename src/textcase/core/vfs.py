from abc import ABC, abstractmethod
from pathlib import PurePosixPath
from typing import Dict, List, Optional, Tuple, Any
import os
import subprocess
import json
from datetime import datetime


class VFS(ABC):
    """Virtual File System interface."""
    
    @abstractmethod
    def name(self) -> str:
        """Get the name of the VFS."""
        pass
    
    @abstractmethod
    def readonly(self) -> bool:
        """Check if the VFS is read-only."""
        pass
    
    @abstractmethod
    def info(self, path: PurePosixPath) -> Dict[str, Any]:
        """Get information about a path."""
        pass
    
    @abstractmethod
    def list(self, path: PurePosixPath, option: Optional[Dict] = None) -> List[PurePosixPath]:
        """List contents of a directory."""
        pass
    
    @abstractmethod
    def get(self, path: PurePosixPath) -> bytes:
        """Get file contents."""
        pass
    
    @abstractmethod
    def patch(self, path: PurePosixPath, range_: Tuple[int, int], data: bytes, session_id: Optional[str] = None) -> str:
        """Apply a patch to a file."""
        pass
    
    @abstractmethod
    def put(self, path: PurePosixPath, data: bytes) -> None:
        """Put file contents."""
        pass
    
    @abstractmethod
    def commit(self, op_id: Optional[str] = None, session_id: Optional[str] = None) -> Tuple[bool, str]:
        """Commit patches."""
        pass
    
    @abstractmethod
    def abort(self, op_id: Optional[str] = None, session_id: Optional[str] = None) -> Tuple[bool, str]:
        """Abort patches."""
        pass


class EditSession:
    """Edit session for managing operations."""
    
    def __init__(self, session_id: str, timeout: Optional[int] = None):
        self.session_id = session_id
        self.operations: List[Dict] = []
        self.created_at = datetime.now()
        self.timeout = timeout


class EditManager:
    """Manager for edit operations and sessions."""
    
    def __init__(self, patches_dir: str):
        self.patches_dir = patches_dir
        self.sessions: Dict[str, EditSession] = {}
        self.operations: Dict[str, Dict] = {}
        os.makedirs(patches_dir, exist_ok=True)
    
    def create_session(self, timeout: Optional[int] = None) -> EditSession:
        """Create a new edit session."""
        session = EditSession(session_id, timeout)
        self.sessions[session_id] = session
        return session
    
    def add_operation(self, op_id: str, operation: Dict, session_id: Optional[str] = None) -> None:
        """Add an operation to a session or standalone."""
        self.operations[op_id] = operation
        if session_id and session_id in self.sessions:
            self.sessions[session_id].operations.append(operation)
    
    def get_operations(self, session_id: Optional[str] = None, op_id: Optional[str] = None) -> List[Dict]:
        """Get operations by session or operation ID."""
        if op_id:
            if op_id in self.operations:
                # Find session containing this operation
                for session in self.sessions.values():
                    for op in session.operations:
                        if op.get('op_id') == op_id:
                            return session.operations
                return [self.operations[op_id]]
            return []
        
        if session_id and session_id in self.sessions:
            return self.sessions[session_id].operations
        
        # Return all operations if no specific session/op requested
        return list(self.operations.values())
    
    def clear_operations(self, session_id: Optional[str] = None, op_id: Optional[str] = None) -> None:
        """Clear operations by session or operation ID."""
        if op_id and op_id in self.operations:
            # Find and remove from session
            for session in self.sessions.values():
                session.operations = [op for op in session.operations if op.get('op_id') != op_id]
            del self.operations[op_id]
        
        if session_id and session_id in self.sessions:
            for op in self.sessions[session_id].operations:
                op_id = op.get('op_id')
                if op_id and op_id in self.operations:
                    del self.operations[op_id]
            self.sessions[session_id].operations.clear()


class LocalFS(VFS):
    """Local file system implementation."""
    
    def __init__(self, root_path: str, edit_manager: Optional[EditManager] = None):
        self.root_path = os.path.abspath(root_path)
        self.edit_manager = edit_manager
        self._name = f"local:{root_path}"
    
    def name(self) -> str:
        return self._name
    
    def readonly(self) -> bool:
        return False
    
    def _resolve_path(self, path: PurePosixPath) -> str:
        """Resolve a VFS path to a local file system path."""
        # Convert PurePosixPath to relative path and join with root
        rel_path = str(path).lstrip('/')
        return os.path.join(self.root_path, rel_path)
    
    def info(self, path: PurePosixPath) -> Dict[str, Any]:
        """Get information about a path."""
        local_path = self._resolve_path(path)
        if not os.path.exists(local_path):
            raise FileNotFoundError(f"Path not found: {path}")
        
        stat = os.stat(local_path)
        return {
            'type': 'directory' if os.path.isdir(local_path) else 'file',
            'size': stat.st_size,
            'modified': stat.st_mtime,
            'created': stat.st_ctime,
            'path': str(path)
        }
    
    def list(self, path: PurePosixPath, option: Optional[Dict] = None) -> List[PurePosixPath]:
        """List contents of a directory."""
        local_path = self._resolve_path(path)
        if not os.path.isdir(local_path):
            raise NotADirectoryError(f"Not a directory: {path}")
        
        items = []
        for item in os.listdir(local_path):
            item_path = path / item
            items.append(item_path)
        
        # Apply sorting/filtering options if provided
        if option:
            # Simple sorting by name for now
            if option.get('sort') == 'name':
                items.sort(key=lambda p: str(p))
        
        return items
    
    def get(self, path: PurePosixPath) -> bytes:
        """Get file contents with patches applied."""
        local_path = self._resolve_path(path)
        if not os.path.isfile(local_path):
            raise FileNotFoundError(f"File not found: {path}")
        
        with open(local_path, 'rb') as f:
            content = f.read()
        
        # Apply patches if edit manager is available
        if self.edit_manager:
            content = self._apply_patches(path, content)
        
        return content
    
    def _apply_patches(self, path: PurePosixPath, content: bytes) -> bytes:
        """Apply patches to content."""
        # Get all operations for this path
        operations = self.edit_manager.get_operations()
        path_ops = [op for op in operations if op.get('path') == str(path)]
        
        # Sort by range start position
        path_ops.sort(key=lambda op: op.get('range', [0, 0])[0])
        
        # Apply patches in order
        for op in path_ops:
            if op.get('type') == 'patch':
                range_ = op.get('range', [0, 0])
                patch_data = op.get('data', b'')
                if isinstance(patch_data, str):
                    patch_data = patch_data.encode('utf-8')
                
                # Apply the patch
                start, end = range_
                content = content[:start] + patch_data + content[end:]
        
        return content
    
    def patch(self, path: PurePosixPath, range_: Tuple[int, int], data: bytes, session_id: Optional[str] = None) -> str:
        """Apply a patch to a file."""
        if not self.edit_manager:
            raise RuntimeError("Edit manager not available")
        
        import uuid
        op_id = str(uuid.uuid4())
        
        operation = {
            'op_id': op_id,
            'type': 'patch',
            'path': str(path),
            'range': range_,
            'data': data,
            'timestamp': datetime.now().isoformat()
        }
        
        self.edit_manager.add_operation(op_id, operation, session_id)
        return op_id
    
    def put(self, path: PurePosixPath, data: bytes) -> None:
        """Put file contents."""
        local_path = self._resolve_path(path)
        os.makedirs(os.path.dirname(local_path), exist_ok=True)
        
        with open(local_path, 'wb') as f:
            f.write(data)
    
    def commit(self, op_id: Optional[str] = None, session_id: Optional[str] = None) -> Tuple[bool, str]:
        """Commit patches to actual files."""
        if not self.edit_manager:
            return False, "Edit manager not available"
        
        try:
            operations = self.edit_manager.get_operations(session_id, op_id)
            
            # Group operations by path
            path_ops = {}
            for op in operations:
                path = op.get('path')
                if path not in path_ops:
                    path_ops[path] = []
                path_ops[path].append(op)
            
            # Apply operations to each file
            for path_str, ops in path_ops.items():
                path = PurePosixPath(path_str)
                local_path = self._resolve_path(path)
                
                if os.path.exists(local_path):
                    with open(local_path, 'rb') as f:
                        content = f.read()
                    
                    # Apply patches
                    content = self._apply_patches(path, content)
                    
                    with open(local_path, 'wb') as f:
                        f.write(content)
            
            # Clear the operations
            self.edit_manager.clear_operations(session_id, op_id)
            
            return True, "Committed successfully"
        
        except Exception as e:
            return False, f"Commit failed: {str(e)}"
    
    def abort(self, op_id: Optional[str] = None, session_id: Optional[str] = None) -> Tuple[bool, str]:
        """Abort patches."""
        if not self.edit_manager:
            return False, "Edit manager not available"
        
        try:
            self.edit_manager.clear_operations(session_id, op_id)
            return True, "Aborted successfully"
        except Exception as e:
            return False, f"Abort failed: {str(e)}"


class GitRepoFS(VFS):
    """Git repository file system implementation."""
    
    def __init__(self, repo_path: str, edit_manager: Optional[EditManager] = None):
        self.repo_path = os.path.abspath(repo_path)
        self.edit_manager = edit_manager
        self._name = f"repo:{repo_path}"
        
        # Verify it's a git repository
        if not os.path.exists(os.path.join(repo_path, '.git')):
            raise ValueError(f"Not a git repository: {repo_path}")
    
    def name(self) -> str:
        return self._name
    
    def readonly(self) -> bool:
        return False
    
    def _resolve_path(self, path: PurePosixPath) -> str:
        """Resolve a VFS path to a local file system path."""
        rel_path = str(path).lstrip('/')
        return os.path.join(self.repo_path, rel_path)
    
    def _is_git_tree_path(self, path: PurePosixPath) -> Tuple[bool, Optional[str], Optional[PurePosixPath]]:
        """Check if path is accessing git tree view (.git/hash)."""
        parts = path.parts
        if len(parts) >= 2 and parts[0] == '.git':
            # This is a git tree access
            commit_hash = parts[1]
            remaining_path = PurePosixPath(*parts[2:]) if len(parts) > 2 else PurePosixPath('.')
            return True, commit_hash, remaining_path
        return False, None, None
    
    def _git_command(self, *args) -> str:
        """Execute a git command and return output."""
        cmd = ['git'] + list(args)
        result = subprocess.run(cmd, cwd=self.repo_path, capture_output=True, text=True)
        if result.returncode != 0:
            raise RuntimeError(f"Git command failed: {' '.join(cmd)}\n{result.stderr}")
        return result.stdout.strip()
    
    def info(self, path: PurePosixPath) -> Dict[str, Any]:
        """Get information about a path."""
        is_git_tree, commit_hash, tree_path = self._is_git_tree_path(path)
        
        if is_git_tree:
            # Git tree view
            try:
                # Check if it's a directory or file in the git tree
                output = self._git_command('ls-tree', commit_hash, str(tree_path))
                if output:
                    parts = output.split()
                    mode = parts[0]
                    obj_type = parts[1]
                    return {
                        'type': 'directory' if obj_type == 'tree' else 'file',
                        'mode': mode,
                        'commit': commit_hash,
                        'path': str(path)
                    }
                else:
                    raise FileNotFoundError(f"Path not found in git tree: {path}")
            except RuntimeError:
                raise FileNotFoundError(f"Path not found in git tree: {path}")
        else:
            # Regular file system access
            local_path = self._resolve_path(path)
            if not os.path.exists(local_path):
                raise FileNotFoundError(f"Path not found: {path}")
            
            stat = os.stat(local_path)
            return {
                'type': 'directory' if os.path.isdir(local_path) else 'file',
                'size': stat.st_size,
                'modified': stat.st_mtime,
                'created': stat.st_ctime,
                'path': str(path)
            }
    
    def list(self, path: PurePosixPath, option: Optional[Dict] = None) -> List[PurePosixPath]:
        """List contents of a directory."""
        is_git_tree, commit_hash, tree_path = self._is_git_tree_path(path)
        
        if is_git_tree:
            # Git tree view
            try:
                output = self._git_command('ls-tree', commit_hash, str(tree_path))
                items = []
                for line in output.split('\n'):
                    if line.strip():
                        parts = line.split('\t')
                        if len(parts) >= 2:
                            filename = parts[1]
                            item_path = path / filename
                            items.append(item_path)
                return items
            except RuntimeError:
                return []
        else:
            # Regular file system access
            local_path = self._resolve_path(path)
            if not os.path.isdir(local_path):
                raise NotADirectoryError(f"Not a directory: {path}")
            
            items = []
            for item in os.listdir(local_path):
                # Skip .git directory in regular listing
                if item == '.git':
                    continue
                item_path = path / item
                items.append(item_path)
            
            return items
    
    def get(self, path: PurePosixPath) -> bytes:
        """Get file contents."""
        is_git_tree, commit_hash, tree_path = self._is_git_tree_path(path)
        
        if is_git_tree:
            # Git tree view - get file from specific commit
            try:
                content = self._git_command('show', f'{commit_hash}:{tree_path}')
                return content.encode('utf-8')
            except RuntimeError:
                raise FileNotFoundError(f"File not found in git tree: {path}")
        else:
            # Regular file system access with patches
            local_path = self._resolve_path(path)
            if not os.path.isfile(local_path):
                raise FileNotFoundError(f"File not found: {path}")
            
            with open(local_path, 'rb') as f:
                content = f.read()
            
            # Apply patches if edit manager is available
            if self.edit_manager:
                content = self._apply_patches(path, content)
            
            return content
    
    def _apply_patches(self, path: PurePosixPath, content: bytes) -> bytes:
        """Apply patches to content (same as LocalFS)."""
        operations = self.edit_manager.get_operations()
        path_ops = [op for op in operations if op.get('path') == str(path)]
        path_ops.sort(key=lambda op: op.get('range', [0, 0])[0])
        
        for op in path_ops:
            if op.get('type') == 'patch':
                range_ = op.get('range', [0, 0])
                patch_data = op.get('data', b'')
                if isinstance(patch_data, str):
                    patch_data = patch_data.encode('utf-8')
                
                start, end = range_
                content = content[:start] + patch_data + content[end:]
        
        return content
    
    def patch(self, path: PurePosixPath, range_: Tuple[int, int], data: bytes, session_id: Optional[str] = None) -> str:
        """Apply a patch to a file (same as LocalFS)."""
        if not self.edit_manager:
            raise RuntimeError("Edit manager not available")
        
        import uuid
        op_id = str(uuid.uuid4())
        
        operation = {
            'op_id': op_id,
            'type': 'patch',
            'path': str(path),
            'range': range_,
            'data': data,
            'timestamp': datetime.now().isoformat()
        }
        
        self.edit_manager.add_operation(op_id, operation, session_id)
        return op_id
    
    def put(self, path: PurePosixPath, data: bytes) -> None:
        """Put file contents (only for regular files, not git tree)."""
        is_git_tree, _, _ = self._is_git_tree_path(path)
        if is_git_tree:
            raise RuntimeError("Cannot write to git tree view")
        
        local_path = self._resolve_path(path)
        os.makedirs(os.path.dirname(local_path), exist_ok=True)
        
        with open(local_path, 'wb') as f:
            f.write(data)
    
    def commit(self, op_id: Optional[str] = None, session_id: Optional[str] = None) -> Tuple[bool, str]:
        """Commit patches to actual files (same as LocalFS)."""
        if not self.edit_manager:
            return False, "Edit manager not available"
        
        try:
            operations = self.edit_manager.get_operations(session_id, op_id)
            
            # Group operations by path
            path_ops = {}
            for op in operations:
                path = op.get('path')
                if path not in path_ops:
                    path_ops[path] = []
                path_ops[path].append(op)
            
            # Apply operations to each file
            for path_str, ops in path_ops.items():
                path = PurePosixPath(path_str)
                
                # Skip git tree paths
                is_git_tree, _, _ = self._is_git_tree_path(path)
                if is_git_tree:
                    continue
                
                local_path = self._resolve_path(path)
                
                if os.path.exists(local_path):
                    with open(local_path, 'rb') as f:
                        content = f.read()
                    
                    # Apply patches
                    content = self._apply_patches(path, content)
                    
                    with open(local_path, 'wb') as f:
                        f.write(content)
            
            # Clear the operations
            self.edit_manager.clear_operations(session_id, op_id)
            
            return True, "Committed successfully"
        
        except Exception as e:
            return False, f"Commit failed: {str(e)}"
    
    def abort(self, op_id: Optional[str] = None, session_id: Optional[str] = None) -> Tuple[bool, str]:
        """Abort patches (same as LocalFS)."""
        if not self.edit_manager:
            return False, "Edit manager not available"
        
        try:
            self.edit_manager.clear_operations(session_id, op_id)
            return True, "Aborted successfully"
        except Exception as e:
            return False, f"Abort failed: {str(e)}"