"""Local file system implementation of ServiceVFSProtocol.

This module provides a local file system implementation of the VFS service protocol.
"""

from abc import ABC, abstractmethod
from pathlib import Path, PurePosixPath
from typing import Dict, List, Optional, Tuple, Union, Any
import os
import uuid
from datetime import datetime

from ...proto.service_vfs_protocol import ServiceVFSProtocol, EntryType


class LocalVFS(ServiceVFSProtocol):
    """Local file system implementation of VFS service protocol.
    
    This class provides access to the local file system through the VFS service protocol.
    """
    
    def __init__(self, root_path: Path, mount_point: PurePosixPath, name: Optional[str] = None):
        """Initialize the local file system VFS.
        
        Args:
            root_path: Root path of the local file system
        """
        self.root_path = root_path.absolute()
        self._name = f"local:{self.root_path.as_posix()}" if name is None else name
        # Store mount_point as provided (PurePosixPath doesn't have absolute() method)
        self._mount_point: PurePosixPath = mount_point
        # Dictionary to store mount points: path -> VFS instance
        self._mounts: Dict[str, ServiceVFSProtocol] = {}
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
    
    def mount_point(self) -> PurePosixPath:
        """Get the root path of the VFS service.
        
        Returns:
            Root path
        """
        assert self._mount_point.is_absolute()
        return self._mount_point

    # Path resolution methods
    def resolve_path(self, path: PurePosixPath) -> Tuple[ServiceVFSProtocol, PurePosixPath]:
        """Resolve a path to VFS and remaining path info.
        
        Args:
            path: Path to resolve
            
        Returns:
            Tuple with VFS service instance and remaining path
        """
        # Store original path for processing
        original_path = path
        
        # Convert relative path to absolute path relative to mount_point
        if not path.is_absolute():
            # 相对路径，直接拼接
            path = self._mount_point / path
        
        # 仍然需要检查，避免访问 vfs 之外
        try:
            relative_path = path.relative_to(self._mount_point)
        except ValueError:
            # Path is outside mount_point, cannot resolve
            raise ValueError(f"Path {path} is outside VFS mount_point {self._mount_point}")
            
        # Find the longest matching mount point by comparing path parts
        best_mount_path = None
        best_mount_parts_count = 0
        
        # 注意：mount_point_str 是 self._mount_point 的相对路径
        for mount_point_str in self._mounts:
            mount_point_path = PurePosixPath(mount_point_str)
            
            # Check if the relative path starts with this mount point
            try:
                # Use relative_to to check if relative_path is under mount_point_path
                remaining = relative_path.relative_to(mount_point_path)
                # 不需要计算 best 了，因为如果 relative_to 成立，则 一定在当前的 vfs 下
                vfs = self._mounts[mount_point_str]
                return vfs.resolve_path(remaining)     # 跳出循环
            except ValueError:
                # relative_path is not under mount_point_path, continue
                continue
        # No mount point found, use this VFS
        return self, relative_path
    
        
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

        # 转为标准 Path
        local_path = Path(local_path) if isinstance(local_path, str) else local_path
        
        # 检查路径是否为绝对路径
        if not local_path.is_absolute():
            raise ValueError("Path must be absolute")
        
        # 检查路径是否在当前VFS的挂载点下
        if local_path.is_relative_to(self.root_path):
            # 在当前 root_path 下
            try:
                rel_path = local_path.relative_to(self.root_path)
                # 1. 得到 rel_path 后，需要检查是否在 mount point 下，如果在，则需要转 mounted vfs 处理
                for mount_point_str in self._mounts:
                    mount_point_path = self._mount_point.joinpath(mount_point_str)
                    if mount_point_path in rel_path.parents:
                        # 当前的相对路径 rel_path 被 mounted vfs 覆盖，需要转由 mount vfs 处理
                        vfs = self._mounts[mount_point_str]
                        return vfs.to_vfs_path(rel_path)
                # 2. 不在 mount point 下， 则返回 rel_path
                return self.mount_point().joinpath(rel_path)
            except ValueError:
                # 不是当前 root_path 的子路径， 需要进一步询问 mount poing
                pass 
        
        # local_path 不在 root_path 下， 则需要进一步询问 mount point
        for mount_point_str in self._mounts:
            vfs = self._mounts[mount_point_str]
            vfs_path = vfs.to_vfs_path(local_path)
            if vfs_path is not None:
                # 找到匹配的路径，返回
                return vfs_path
                        
        # 如果没有找到匹配的路径，返回None
        return None
    
    def to_local_path(self, vfs_path: PurePosixPath) -> Optional[Path]:
        """Convert a VFS path to a local file system path if possible.
        
        This method attempts to convert a path from the VFS to its equivalent
        path in the local file system. It handles mounted VFS instances by
        checking if the VFS path belongs to any mounted VFS and delegating the
        conversion if necessary.
        
        Args:
            vfs_path: VFS path to convert
            
        Returns:
            Equivalent local file system path as Path if conversion is possible,
            None if the path cannot be mapped to this VFS
        """
        # 检查路径是否对应一个挂载点
        vfs, remaining_path = self.resolve_path(vfs_path)
        if vfs is not self:
            # 如果路径对应一个挂载点，委托给挂载的 VFS
            return vfs.to_local_path(remaining_path)
        
        # 否则，使用本地文件系统
        return self._resolve_local_path(remaining_path)

    # Mount management
    def mount(self, path: PurePosixPath, vfs: ServiceVFSProtocol) -> Tuple[bool, str]:
        """Mount a VFS at the given path.
        
        Args:
            path: VFS mount point (can be absolute or relative path)
            vfs: VFS service instance
            
        Returns:
            Success status and message
        """
        # Convert to relative path based on mount_point
        if not path.is_absolute():
            # 相对路径，需要转换为绝对路径
            path = self.mount_point.joinpath(path)
    
        # Check if absolute path is within mount_point
        try:
            rel_path = path.relative_to(self._mount_point)
        except ValueError:
            return False, f"Mount point {path} is outside VFS mount_point {self._mount_point}"
        
        mount_point_str = rel_path.as_posix()
        if mount_point_str in self._mounts:
            return False, f"Mount point {mount_point_str} already exists"
        
        # 进一步的，需要检查 mount_point_ptr 整个路径上任何一个 sub path 不是 mount point 
        # 并且，当前的 mount_point_ptr 也不是已经存在的 mount_point 的 prefix
        # 例如，已经存在 /a/b/c ，不能再挂载 /a/b/c/d
        for sub_path in rel_path.parents:
            if sub_path.as_posix() in self._mounts:
                return False, f"Mount point {mount_point_str} is a sub path of existing mount point {sub_path.as_posix()}"
            
        # 检查当前路径是否是其他已挂载路径的子路径
        for existing_mount in self._mounts:
            if existing_mount.startswith(mount_point_str):
                return False, f"Mount point {existing_mount} is a sub path of existing mount point {existing_mount}"

        self._mounts[mount_point_str] = vfs
        return True, f"Mounted {vfs.name()} at {mount_point_str}"
    
    def unmount(self, path: PurePosixPath) -> bool:
        """Unmount a VFS at the given path.
        
        Args:
            path: VFS mount point to unmount (can be absolute or relative path)
            
        Returns:
            Success status
        """
        # Convert to relative path based on mount_point
        if path.is_absolute():
            # Check if absolute path is within mount_point
            try:
                rel_path = path.relative_to(self._mount_point)
            except ValueError:
                return False  # Path is outside mount_point, cannot unmount
        else:
            rel_path = path
        
        mount_point_str = rel_path.as_posix()
        if mount_point_str in self._mounts:
            del self._mounts[mount_point_str]
            return True
        return False
    
    def mounts(self) -> Dict[str, ServiceVFSProtocol]:
        """Get list of mount points.
        
        Returns:
            Dictionary of mount points (as relative paths) and their VFS instances
        """
        return self._mounts
    
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
            path: VFS path (relative to this VFS)
            
        Returns:
            Local file system path
            
        Raises:
            PermissionError: If resolved path is outside root_path
        """
        # Ensure path is relative (should already be handled by resolve_path)
        if path.is_absolute():
           raise ValueError(f"Expected relative path, got absolute: {path}")
        
        # Convert PurePosixPath to local path using pathlib
        local_path = self.root_path / Path(*path.parts)
        
        # Check if the resolved path is within root_path
        try:
            local_path.resolve().relative_to(self.root_path.resolve())
        except ValueError:
            raise PermissionError(f"Access denied: {path} is outside the root path")
            
        return str(local_path)
    
    def info(self, path: PurePosixPath) -> Optional[Dict[str, Any]]:
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
        local_path = self._resolve_local_path(remaining_path)
        if not os.path.exists(local_path):
            # raise FileNotFoundError(f"Path not found: {path}")
            return None
        
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
        local_path = self._resolve_local_path(remaining_path)
        if not os.path.isdir(local_path):
            raise NotADirectoryError(f"Not a directory: {path}")
        
        items = []
        for item in os.listdir(local_path):
            item_path = remaining_path.joinpath(item)
            item_local_path = self._resolve_local_path(item_path)
            is_dir = os.path.isdir(item_local_path)
            
            items.append(
                (PurePosixPath(item), EntryType.DIR if is_dir else EntryType.FILE)
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
        local_path = self._resolve_local_path(remaining_path)
        
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
        local_path = self._resolve_local_path(remaining_path)
        
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
        local_path = self._resolve_local_path(remaining_path)
        
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
        local_path = self._resolve_local_path(remaining_path)
        
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
    
    def exists(self, path: PurePosixPath) -> bool:
        """Check if a path exists.
        
        Args:
            path: Path to check
            
        Returns:
            True if path exists, False otherwise
        """
        # 检查路径是否对应一个挂载点
        vfs, remaining_path = self.resolve_path(path)
        if vfs is not self:
            # 如果路径对应一个挂载点，委托给挂载的 VFS
            return vfs.exists(remaining_path)
        
        # 否则，使用本地文件系统
        try:
            local_path = self._resolve_local_path(remaining_path)
            return os.path.exists(local_path)
        except (PermissionError, ValueError):
            return False
    
    def is_file(self, path: PurePosixPath) -> bool:
        """Check if a path is a file.
        
        Args:
            path: Path to check
            
        Returns:
            True if path is a file, False otherwise
        """
        # 检查路径是否对应一个挂载点
        vfs, remaining_path = self.resolve_path(path)
        if vfs is not self:
            # 如果路径对应一个挂载点，委托给挂载的 VFS
            return vfs.is_file(remaining_path)
        
        # 否则，使用本地文件系统
        try:
            local_path = self._resolve_local_path(remaining_path)
            return os.path.isfile(local_path)
        except (PermissionError, ValueError):
            return False