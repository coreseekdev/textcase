"""VFS service protocol definition.

This module defines the protocol interface for VFS services.
"""

from abc import ABC, abstractmethod
from ast import Tuple
from typing import Dict, List, Optional, Any
from pathlib import PurePosixPath

class ServiceVFSProtocol(ABC):
    """Protocol interface for VFS services.
    
    This protocol defines the interface that all VFS service
    implementations must follow.
    """
    
    # Type aliases as associated types
    SessionId = str
    OperationId = str
    
    @abstractmethod
    def name(self) -> str:
        """Get the name of the VFS service.
        
        Returns:
            Service name
        """
        ...

    # Path resolution methods
    @abstractmethod
    def resolve_path(self, path: PurePosixPath) -> Tuple['ServiceVFSProtocol', PurePosixPath]:
        """Resolve a path to VFS and remaining path info.
        
        Args:
            path: Path string to resolve
            
        Returns:
            Tuple with VFS service instance and remaining path
        """
        ...
    
    # Mount management
    @abstractmethod
    def mount(self, path: PurePosixPath, vfs: 'ServiceVFSProtocol') -> Tuple[bool, str]:
        """Mount a VFS at the given path.
        
        Args:
            path: VFS mount point
            vfs: VFS service instance
            
        Returns:
            Success status and message
        """
        ...
    
    @abstractmethod
    def unmount(self, path: PurePosixPath) -> bool:
        """Unmount a VFS at the given path.
        
        Args:
            path: VFS mount point to unmount
            
        Returns:
            Success status and message
        """
        ...
    
    @abstractmethod
    def mounts(self) -> Dict[str, 'ServiceVFSProtocol']:
        """Get list of mount points.
        
        Returns:
            List of mount point paths
        """
        ...
    
    # File system operations
    @abstractmethod
    def readonly(self) -> bool:
        """Check if the VFS is read-only."""
        pass

    @abstractmethod
    def info(self, path: PurePosixPath) -> Dict[str, Any]:
        """Get information about a path.
        
        Args:
            path: Path to get info for
            
        Returns:
            Path information
        """
        ...
    
    @abstractmethod
    def list(self, path: PurePosixPath, option: Dict[str, Any]) -> Dict[str, Any]:
        """List contents of a directory.
        
        Args:
            path: Directory path to list
            option: JSON string with listing options
            
        Returns:
            List of directory contents
        """
        ...
    
    @abstractmethod
    def get(self, path: PurePosixPath) -> bytes:
        """Get file contents.
        
        Args:
            path: File path to read
            
        Returns:
            File contents
        """
        ...
    
    @abstractmethod
    def get_text(self, path: PurePosixPath, encoding: str = 'utf-8') -> Optional[str]:
        """Get file contents as text.
        
        Args:
            path: File path to read
            encoding: Text encoding to use
            
        Returns:
            File contents as text
        """
        ...
    
    @abstractmethod
    def put(self, path: PurePosixPath, content: bytes, create_if_missing: bool = False) -> bool:
        """Put file contents.
        
        Args:
            path: File path to write
            content: File content
            create_if_missing: Create file if it doesn't exist
            
        Returns:
            Success status
        """
        ...
    
    # Edit operations
    @abstractmethod
    def patch(self, path: PurePosixPath, range: Tuple[int, int], content: bytes, 
              session_id: Optional[SessionId] = None) -> OperationId:
        """Apply a patch to a file.
        
        Args:
            path: File path to patch
            start: Start position of the range
            end: End position of the range
            content: Replacement content
            session_id: Optional session ID
            encoding: Content encoding ('base64' or 'text')
            
        Returns:
            Operation ID and status
        """
        ...
    
    @abstractmethod
    def commit(self, op_id: Optional[OperationId] = None, session_id: Optional[SessionId] = None) -> Dict[str, Any]:
        """Commit patches.
        
        Args:
            op_id: Optional operation ID
            session_id: Optional session ID
            
        Returns:
            Commit status and message
        """
        ...
    
    @abstractmethod
    def abort(self, op_id: Optional[OperationId] = None, session_id: Optional[SessionId] = None) -> Dict[str, Any]:
        """Abort patches.
        
        Args:
            op_id: Optional operation ID
            session_id: Optional session ID
            
        Returns:
            Abort status and message
        """
        ...
    
    # Session management
    @abstractmethod
    def create_session(self) -> SessionId:
        """Create a new edit session.
        
        Args:
            session_name: Optional name for the session
            
        Returns:
            Session ID and info
        """
        ...
    
    @abstractmethod
    def list_sessions(self) -> List[SessionId]:
        """List all active sessions.
        
        Returns:
            List of active sessions
        """
        ...
    