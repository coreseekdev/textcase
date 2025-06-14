"""Local file system implementation of ServiceVFSProtocol.

This module provides a local file system implementation of the VFS service protocol.
"""

from abc import ABC, abstractmethod
from pathlib import Path, PurePosixPath
from typing import Dict, List, Optional, Tuple, Any
import os
import uuid
from datetime import datetime

from ...proto.service_vfs_protocol import ServiceVFSProtocol, EntryType


class LocalVFS(ServiceVFSProtocol):
    """Local file system implementation of VFS service protocol.
    
    This class provides access to the local file system through the VFS service protocol.
    """
    
    def __init__(self, root_path: str):
        """Initialize the local file system VFS.
        
        Args:
            root_path: Root path of the local file system
        """
        self.root_path = os.path.abspath(root_path)
        self._name = f"local:{self.root_path}"
        # Dictionary to store mount points: path -> VFS instance
        self.mounts: Dict[str, ServiceVFSProtocol] = {}
        # Dictionary to store edit sessions
        self.sessions: Dict[ServiceVFSProtocol.SessionId, Dict[str, Any]] = {}
        # Dictionary to store operations
        self.operations: Dict[ServiceVFSProtocol.OperationId, Dict[str, Any]] = {}
    
    def name(self) -> str:
        """Get the name of the VFS service.
        
        Returns:
            Service name
        """
        return self._name
    
    # Path resolution methods
    def resolve_path(self, path: PurePosixPath) -> Tuple[ServiceVFSProtocol, PurePosixPath]:
        """Resolve a path to VFS and remaining path info.
        
        Args:
            path: Path to resolve
            
        Returns:
            Tuple with VFS service instance and remaining path
        """
        path_parts = path.parts
        
        # Find the longest matching mount point by comparing path parts
        best_mount = ''
        best_mount_parts_count = 0
        
        for mount_point in self.mounts:
            mount_parts = PurePosixPath(mount_point).parts
            
            # Check if mount point parts match the beginning of path parts
            if len(mount_parts) <= len(path_parts):
                if mount_parts == path_parts[:len(mount_parts)]:
                    if len(mount_parts) > best_mount_parts_count:
                        best_mount = mount_point
                        best_mount_parts_count = len(mount_parts)
        
        if best_mount:
            vfs = self.mounts[best_mount]
            # Calculate remaining path from the unmatched parts
            mount_parts_count = len(PurePosixPath(best_mount).parts)
            remaining_parts = path_parts[mount_parts_count:]
            remaining_path = PurePosixPath(*remaining_parts) if remaining_parts else PurePosixPath('.')
            # 如果后续没有文件挂载，返回  vfs, remaining_path
            # 如果有其他文件挂载，进一步解析（递归）
            return vfs.resolve_path(remaining_path)
            # return vfs, remaining_path
        
        # No mount point found, use this VFS
        return self, path
    
    # Mount management
    def mount(self, path: PurePosixPath, vfs: ServiceVFSProtocol) -> Tuple[bool, str]:
        """Mount a VFS at the given path.
        
        Args:
            path: VFS mount point
            vfs: VFS service instance
            
        Returns:
            Success status and message
        """
        mount_point = path.as_posix()
        if mount_point in self.mounts:
            return False, f"Mount point {mount_point} already exists"
        
        self.mounts[mount_point] = vfs
        return True, f"Mounted {vfs.name()} at {mount_point}"
    
    def unmount(self, path: PurePosixPath) -> bool:
        """Unmount a VFS at the given path.
        
        Args:
            path: VFS mount point to unmount
            
        Returns:
            Success status
        """
        mount_point = path.as_posix()
        if mount_point in self.mounts:
            del self.mounts[mount_point]
            return True
        return False
    
    def mounts(self) -> Dict[str, ServiceVFSProtocol]:
        """Get list of mount points.
        
        Returns:
            Dictionary of mount points and their VFS instances
        """
        return self.mounts
    
    # File system operations
    def readonly(self) -> bool:
        """Check if the VFS is read-only.
        
        Returns:
            False as local file system is writable by default
        """
        return False
    
    def _resolve_local_path(self, path: PurePosixPath) -> str:
        """Resolve a VFS path to a local file system path.
        
        Args:
            path: VFS path
            
        Returns:
            Local file system path
            
        Raises:
            PermissionError: If resolved path is outside root_path
        """
        rel_path = path.as_posix().lstrip('/')
        local_path = os.path.join(self.root_path, rel_path)
        
        # Check if the resolved path is within root_path
        abs_path = os.path.abspath(local_path)
        abs_root = os.path.abspath(self.root_path)
        
        if not abs_path.startswith(abs_root):
            raise PermissionError(f"Access denied: {path} is outside the root path")
            
        return local_path
    
    def info(self, path: PurePosixPath) -> Dict[str, Any]:
        """Get information about a path.
        
        Args:
            path: Path to get info for
            
        Returns:
            Path information
        """
        # 检查路径是否对应一个挂载点
        vfs, remaining_path = self.resolve_path(path)
        if vfs is not self:
            # 如果路径对应一个挂载点，委托给挂载的 VFS
            return vfs.info(remaining_path)
        
        # 否则，使用本地文件系统
        local_path = self._resolve_local_path(path)
        if not os.path.exists(local_path):
            raise FileNotFoundError(f"Path not found: {path}")
        
        stat = os.stat(local_path)
        return {
            'type': 'directory' if os.path.isdir(local_path) else 'file',
            'size': stat.st_size,
            'modified': stat.st_mtime,
            'created': stat.st_ctime,
            'path': str(path),
            'is_dir': os.path.isdir(local_path),
            'is_file': os.path.isfile(local_path),
            'exists': True
        }
    
    def list(self, path: PurePosixPath, option: Dict[str, Any]) -> List[Tuple[PurePosixPath, EntryType]]:
        """List contents of a directory.
        
        Args:
            path: Directory path to list
            option: Listing options (sorting, filtering)
            
        Returns:
            Dictionary with directory contents
        """
        # 检查路径是否对应一个挂载点
        vfs, remaining_path = self.resolve_path(path)
        if vfs is not self:
            # 如果路径对应一个挂载点，委托给挂载的 VFS
            return vfs.list(remaining_path, option)
        
        # 否则，使用本地文件系统
        local_path = self._resolve_local_path(path)
        if not os.path.isdir(local_path):
            raise NotADirectoryError(f"Not a directory: {path}")
        
        items = []
        for item in os.listdir(local_path):
            item_path = path.joinpath(item)
            item_local_path = self._resolve_local_path(item_path)
            is_dir = os.path.isdir(item_local_path)
            
            items.append(
                (item_path, EntryType.DIR if is_dir else EntryType.FILE)
            )
        
        # Apply sorting if specified in options
        if option and 'sort' in option:
            sort_key = option['sort']
            if sort_key == 'name':
                items.sort(key=lambda x: x['name'])
            elif sort_key == 'type':
                items.sort(key=lambda x: x['type'])
        
        return items
    
    def get(self, path: PurePosixPath) -> bytes:
        """Get file contents.
        
        Args:
            path: File path to read
            
        Returns:
            File contents
            
        Raises:
            FileNotFoundError: If file not found
            PermissionError: If path is outside root_path
        """
        # 检查路径是否对应一个挂载点
        vfs, remaining_path = self.resolve_path(path)
        if vfs is not self:
            # 如果路径对应一个挂载点，委托给挂载的 VFS
            return vfs.get(remaining_path)
        
        # 否则，使用本地文件系统
        local_path = self._resolve_local_path(path)
        
        if not os.path.isfile(local_path):
            raise FileNotFoundError(f"File not found: {path}")
        
        with open(local_path, 'rb') as f:
            return f.read()
    
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
        """Put file contents.
        
        Args:
            path: File path to write
            content: File content
            create_if_missing: Create file if it doesn't exist
            
        Returns:
            Success status
            
        Raises:
            PermissionError: If path is outside root_path
        """
        # 检查路径是否对应一个挂载点
        vfs, remaining_path = self.resolve_path(path)
        if vfs is not self:
            # 如果路径对应一个挂载点，委托给挂载的 VFS
            return vfs.put(remaining_path, content, create_if_missing)
        
        # 否则，使用本地文件系统
        local_path = self._resolve_local_path(path)
        
        # Check if file exists and create_if_missing is False
        if not os.path.exists(local_path) and not create_if_missing:
            return False
        
        # Create parent directories if they don't exist
        parent_dir = os.path.dirname(local_path)
        os.makedirs(parent_dir, exist_ok=True)
        
        with open(local_path, 'wb') as f:
            f.write(content)
        
        return True
    
    def remove(self, path: PurePosixPath, force: bool = False) -> bool:
        """Remove a file or directory.
        
        Args:
            path: Path to remove
            force: Force removal (ignore non-existent files)
            recursive: Remove directories recursively
            
        Returns:
            Success status
            
        Raises:
            OSError: If directory is not empty and recursive=False
            PermissionError: If VFS is readonly
        """
        if self.readonly():
            raise PermissionError("Cannot remove files in readonly VFS")
        
        # 检查路径是否对应一个挂载点
        vfs, remaining_path = self.resolve_path(path)
        if vfs is not self:
            # 如果路径对应一个挂载点，委托给挂载的 VFS
            return vfs.remove(remaining_path, force)
        
        # 否则，使用本地文件系统
        local_path = self._resolve_local_path(path)
        
        if not os.path.exists(local_path):
            if force:
                return True  # Ignore non-existent files when force=True
            else:
                raise FileNotFoundError(f"Path not found: {path}")
        
        try:
            if os.path.isfile(local_path) or os.path.islink(local_path):
                os.remove(local_path)
            elif os.path.isdir(local_path):
                if force:
                    import shutil
                    shutil.rmtree(local_path)
                else:
                    os.rmdir(local_path)  # Will raise OSError if directory is not empty
            return True
        except OSError as e:
            raise e
    
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
        if self.readonly():
            raise PermissionError("Cannot create directories in readonly VFS")
        
        # 检查路径是否对应一个挂载点
        vfs, remaining_path = self.resolve_path(path)
        if vfs is not self:
            # 如果路径对应一个挂载点，委托给挂载的 VFS
            return vfs.mkdir(remaining_path, parents, exist_ok)
        
        # 否则，使用本地文件系统
        local_path = self._resolve_local_path(path)
        
        try:
            os.makedirs(local_path, exist_ok=exist_ok)
            return True
        except FileExistsError:
            if not exist_ok:
                raise FileExistsError(f"Directory already exists: {path}")
            return True
        except FileNotFoundError:
            if not parents:
                raise FileNotFoundError(f"Parent directory does not exist: {path}")
            # This shouldn't happen with os.makedirs, but just in case
            os.makedirs(local_path, exist_ok=exist_ok)
            return True
    
    # Edit operations - temporary implementations
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
        # Generate a unique operation ID
        op_id = str(uuid.uuid4())
        
        # Store the operation
        operation = {
            'op_id': op_id,
            'type': 'patch',
            'path': str(path),
            'range': range,
            'content': content,
            'session_id': session_id,
            'timestamp': datetime.now().isoformat()
        }
        
        self.operations[op_id] = operation
        
        # Add to session if session_id is provided
        if session_id:
            if session_id not in self.sessions:
                self.sessions[session_id] = {
                    'operations': []
                }
            self.sessions[session_id]['operations'].append(op_id)
        
        return op_id
    
    def commit(self, op_id: Optional[ServiceVFSProtocol.OperationId] = None, 
               session_id: Optional[ServiceVFSProtocol.SessionId] = None) -> Dict[str, Any]:
        """Commit patches.
        
        Args:
            op_id: Optional operation ID
            session_id: Optional session ID
            
        Returns:
            Commit status and message
        """
        # Temporary implementation
        return {
            'success': False,
            'message': 'Not implemented'
        }
    
    def abort(self, op_id: Optional[ServiceVFSProtocol.OperationId] = None, 
              session_id: Optional[ServiceVFSProtocol.SessionId] = None) -> Dict[str, Any]:
        """Abort patches.
        
        Args:
            op_id: Optional operation ID
            session_id: Optional session ID
            
        Returns:
            Abort status and message
        """
        # Temporary implementation
        return {
            'success': False,
            'message': 'Not implemented'
        }
    
    # Session management - temporary implementations
    def create_session(self) -> ServiceVFSProtocol.SessionId:
        """Create a new edit session.
        
        Returns:
            Session ID
        """
        session_id = str(uuid.uuid4())
        self.sessions[session_id] = {
            'operations': [],
            'created_at': datetime.now().isoformat()
        }
        return session_id
    
    def list_sessions(self) -> List[ServiceVFSProtocol.SessionId]:
        """List all active sessions.
        
        Returns:
            List of active sessions
        """
        return list(self.sessions.keys())
    
    def close_session(self, session_id: ServiceVFSProtocol.SessionId) -> bool:
        """Close an edit session.
        
        Args:
            session_id: Session ID to close
            
        Returns:
            Success status
        """
        if session_id in self.sessions:
            del self.sessions[session_id]
            return True
        return False