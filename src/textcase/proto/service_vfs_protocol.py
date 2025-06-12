"""VFS service protocol definition.

This module defines the protocol interface for VFS services.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any


class ServiceVFSProtocol(ABC):
    """Protocol interface for VFS services.
    
    This protocol defines the interface that all VFS service
    implementations must follow.
    """
    
    @abstractmethod
    def name(self) -> str:
        """Get the name of the VFS service.
        
        Returns:
            Service name
        """
        ...
    
    # Path resolution methods
    @abstractmethod
    def resolve_path(self, path: str) -> Dict[str, Any]:
        """Resolve a path to VFS and remaining path info.
        
        Args:
            path: Path string to resolve
            
        Returns:
            Dict with VFS name and remaining path
        """
        ...
    
    # Mount management
    @abstractmethod
    def mount(self, path: str, local_path: str) -> Dict[str, Any]:
        """Mount a local path at the given VFS path.
        
        Args:
            path: VFS mount point
            local_path: Local file system path
            
        Returns:
            Success status and message
        """
        ...
    
    @abstractmethod
    def unmount(self, path: str) -> Dict[str, Any]:
        """Unmount a VFS at the given path.
        
        Args:
            path: VFS mount point to unmount
            
        Returns:
            Success status and message
        """
        ...
    
    @abstractmethod
    def mounts(self) -> Dict[str, Any]:
        """Get list of mount points.
        
        Returns:
            List of mount point paths
        """
        ...
    
    # File system operations
    @abstractmethod
    def info(self, path: str) -> Dict[str, Any]:
        """Get information about a path.
        
        Args:
            path: Path to get info for
            
        Returns:
            Path information
        """
        ...
    
    @abstractmethod
    def list(self, path: str, option: Optional[str] = None) -> Dict[str, Any]:
        """List contents of a directory.
        
        Args:
            path: Directory path to list
            option: JSON string with listing options
            
        Returns:
            List of directory contents
        """
        ...
    
    @abstractmethod
    def get(self, path: str) -> Dict[str, Any]:
        """Get file contents.
        
        Args:
            path: File path to read
            
        Returns:
            File contents (base64 encoded for binary safety)
        """
        ...
    
    @abstractmethod
    def get_text(self, path: str, encoding: str = 'utf-8') -> Dict[str, Any]:
        """Get file contents as text.
        
        Args:
            path: File path to read
            encoding: Text encoding to use
            
        Returns:
            File contents as text
        """
        ...
    
    @abstractmethod
    def put(self, path: str, content: str, encoding: str = 'base64') -> Dict[str, Any]:
        """Put file contents.
        
        Args:
            path: File path to write
            content: File content (base64 encoded or text)
            encoding: Content encoding ('base64' or 'text')
            
        Returns:
            Success status
        """
        ...
    
    # Edit operations
    @abstractmethod
    def patch(self, path: str, start: int, end: int, content: str, 
              session_id: Optional[str] = None, encoding: str = 'text') -> Dict[str, Any]:
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
    def commit(self, op_id: Optional[str] = None, session_id: Optional[str] = None) -> Dict[str, Any]:
        """Commit patches.
        
        Args:
            op_id: Optional operation ID
            session_id: Optional session ID
            
        Returns:
            Commit status and message
        """
        ...
    
    @abstractmethod
    def abort(self, op_id: Optional[str] = None, session_id: Optional[str] = None) -> Dict[str, Any]:
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
    def create_session(self, session_name: Optional[str] = None) -> Dict[str, Any]:
        """Create a new edit session.
        
        Args:
            session_name: Optional name for the session
            
        Returns:
            Session ID and info
        """
        ...
    
    @abstractmethod
    def list_sessions(self) -> Dict[str, Any]:
        """List all active sessions.
        
        Returns:
            List of active sessions
        """
        ...
    
    @abstractmethod
    def close_session(self, session_id: str) -> Dict[str, Any]:
        """Close a session (abort all its operations).
        
        Args:
            session_id: Session ID to close
            
        Returns:
            Close status and message
        """
        ...