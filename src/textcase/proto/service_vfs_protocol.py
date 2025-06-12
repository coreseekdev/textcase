"""VFS service protocol definition.

This module defines the protocol interface for VFS services.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any, Protocol, BinaryIO, Tuple
from pathlib import PosixPath, PurePosixPath
from enum import Enum

class EntryType(Enum):
    """Enumeration for file system entry types."""
    FILE = "file"
    DIR = "dir"

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
    def list(self, path: PurePosixPath, option: Dict[str, Any]) -> List[Tuple[PosixPath, EntryType]]:
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
    def commit(self, message: str, op_id: Optional[OperationId] = None, session_id: Optional[SessionId] = None) -> Dict[str, Any]:
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
    

class ChangeOperation(Protocol):
    """Protocol for change operations in the edit manager.
    
    This protocol defines the interface for operations that can be
    serialized to a changeset file.
    """
    
    @property
    def operation_type(self) -> str:
        """Get the type of operation.
        
        Returns:
            Operation type (e.g., 'session_create', 'patch', 'write')
        """
        ...
    
    @property
    def timestamp(self) -> float:
        """Get the timestamp of the operation.
        
        Returns:
            Operation timestamp
        """
        ...
    
    def serialize(self) -> bytes:
        """Serialize the operation to bytes.
        
        Returns:
            Serialized operation
        """
        ...
    
    @classmethod
    def deserialize(cls, data: bytes) -> 'ChangeOperation':
        """Deserialize bytes to an operation.
        
        Args:
            data: Serialized operation
            
        Returns:
            Deserialized operation
        """
        ...


class EditManagerProtocol(ABC):
    """Protocol interface for edit manager.
    
    This protocol defines the interface for managing edit operations
    and serializing them to a changeset file.
    """
    
    @abstractmethod
    def initialize(self, changeset_path: str) -> bool:
        """Initialize the edit manager with a changeset file.
        
        Args:
            changeset_path: Path to the changeset file
            
        Returns:
            Success status
        """
        ...
    
    @abstractmethod
    def create_session(self, metadata: Optional[Dict[str, Any]] = None) -> ServiceVFSProtocol.SessionId:
        """Create a new edit session.
        
        Args:
            metadata: Optional metadata for the session
            
        Returns:
            Session ID
        """
        ...
    
    @abstractmethod
    def commit_session(self, session_id: ServiceVFSProtocol.SessionId) -> bool:
        """Commit an edit session.
        
        Args:
            session_id: Session ID to commit
            
        Returns:
            Success status
        """
        ...
    
    @abstractmethod
    def rollback_session(self, session_id: ServiceVFSProtocol.SessionId) -> bool:
        """Rollback an edit session.
        
        Args:
            session_id: Session ID to rollback
            
        Returns:
            Success status
        """
        ...
    
    @abstractmethod
    def record_patch(self, 
                    session_id: ServiceVFSProtocol.SessionId, 
                    file_path: str, 
                    range: Tuple[int, int], 
                    content: bytes) -> ServiceVFSProtocol.OperationId:
        """Record a patch operation.
        
        Args:
            session_id: Session ID
            file_path: Full path of the file to patch
            range: Start and end positions of the range
            content: Replacement content
            
        Returns:
            Operation ID
        """
        ...
    
    @abstractmethod
    def record_write(self, 
                    session_id: ServiceVFSProtocol.SessionId, 
                    file_path: str, 
                    content: bytes) -> ServiceVFSProtocol.OperationId:
        """Record a write operation.
        
        Args:
            session_id: Session ID
            file_path: Full path of the file to write
            content: File content
            
        Returns:
            Operation ID
        """
        ...
    
    @abstractmethod
    def get_session_operations(self, session_id: ServiceVFSProtocol.SessionId) -> List[ChangeOperation]:
        """Get all operations in a session.
        
        Args:
            session_id: Session ID
            
        Returns:
            List of operations
        """
        ...
    
    @abstractmethod
    def get_operation(self, operation_id: ServiceVFSProtocol.OperationId) -> Optional[ChangeOperation]:
        """Get an operation by ID.
        
        Args:
            operation_id: Operation ID
            
        Returns:
            Operation or None if not found
        """
        ...
    
    @abstractmethod
    def flush(self) -> bool:
        """Flush all changes to the changeset file.
        
        Returns:
            Success status
        """
        ...
    
    @abstractmethod
    def close(self) -> bool:
        """Close the edit manager and release resources.
        
        Returns:
            Success status
        """
        ...
    