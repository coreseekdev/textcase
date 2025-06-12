from pathlib import PurePosixPath
from typing import Dict, List, Optional, Tuple, Any
import json
import uuid
from .vfs_resolver import PathResolver


class VFSService:
    """VFS service that provides RPC interface for virtual file system operations."""
    
    def __init__(self, root_path: str):
        self.path_resolver = PathResolver(root_path)
        self.sessions: Dict[str, str] = {}  # session_id -> session_name mapping
    
    def name(self) -> str:
        """Get the name of the VFS service."""
        return "VFSService"
    
    # Path resolution methods
    def resolve_path(self, path: str) -> Dict[str, Any]:
        """Resolve a path to VFS and remaining path info.
        
        Args:
            path: Path string to resolve
            
        Returns:
            Dict with VFS name and remaining path
        """
        try:
            posix_path = PurePosixPath(path)
            vfs, remaining_path = self.path_resolver.resolve_path(posix_path)
            return {
                'success': True,
                'vfs_name': vfs.name(),
                'remaining_path': str(remaining_path)
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    # Mount management
    def mount(self, path: str, local_path: str) -> Dict[str, Any]:
        """Mount a local path at the given VFS path.
        
        Args:
            path: VFS mount point
            local_path: Local file system path
            
        Returns:
            Success status and message
        """
        try:
            posix_path = PurePosixPath(path)
            self.path_resolver.mount(posix_path, local_path)
            return {
                'success': True,
                'message': f'Mounted {local_path} at {path}'
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def unmount(self, path: str) -> Dict[str, Any]:
        """Unmount a VFS at the given path.
        
        Args:
            path: VFS mount point to unmount
            
        Returns:
            Success status and message
        """
        try:
            posix_path = PurePosixPath(path)
            self.path_resolver.unmount(posix_path)
            return {
                'success': True,
                'message': f'Unmounted {path}'
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def mounts(self) -> Dict[str, Any]:
        """Get list of mount points.
        
        Returns:
            List of mount point paths
        """
        try:
            mount_list = self.path_resolver.mounts_list()
            return {
                'success': True,
                'mounts': [str(mount) for mount in mount_list]
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    # File system operations
    def info(self, path: str) -> Dict[str, Any]:
        """Get information about a path.
        
        Args:
            path: Path to get info for
            
        Returns:
            Path information
        """
        try:
            posix_path = PurePosixPath(path)
            info_data = self.path_resolver.info(posix_path)
            return {
                'success': True,
                'info': info_data
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def list(self, path: str, option: Optional[str] = None) -> Dict[str, Any]:
        """List contents of a directory.
        
        Args:
            path: Directory path to list
            option: JSON string with listing options
            
        Returns:
            List of directory contents
        """
        try:
            posix_path = PurePosixPath(path)
            
            # Parse options if provided
            parsed_option = None
            if option:
                parsed_option = json.loads(option)
            
            items = self.path_resolver.list(posix_path, parsed_option)
            return {
                'success': True,
                'items': [str(item) for item in items]
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def get(self, path: str) -> Dict[str, Any]:
        """Get file contents.
        
        Args:
            path: File path to read
            
        Returns:
            File contents (base64 encoded for binary safety)
        """
        try:
            posix_path = PurePosixPath(path)
            content = self.path_resolver.get(posix_path)
            
            # Encode as base64 for safe transport
            import base64
            encoded_content = base64.b64encode(content).decode('ascii')
            
            return {
                'success': True,
                'content': encoded_content,
                'encoding': 'base64'
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def get_text(self, path: str, encoding: str = 'utf-8') -> Dict[str, Any]:
        """Get file contents as text.
        
        Args:
            path: File path to read
            encoding: Text encoding to use
            
        Returns:
            File contents as text
        """
        try:
            posix_path = PurePosixPath(path)
            content = self.path_resolver.get(posix_path)
            text_content = content.decode(encoding)
            
            return {
                'success': True,
                'content': text_content,
                'encoding': 'text'
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def put(self, path: str, content: str, encoding: str = 'base64') -> Dict[str, Any]:
        """Put file contents.
        
        Args:
            path: File path to write
            content: File content (base64 encoded or text)
            encoding: Content encoding ('base64' or 'text')
            
        Returns:
            Success status
        """
        try:
            posix_path = PurePosixPath(path)
            
            # Decode content based on encoding
            if encoding == 'base64':
                import base64
                data = base64.b64decode(content)
            elif encoding == 'text':
                data = content.encode('utf-8')
            else:
                raise ValueError(f"Unsupported encoding: {encoding}")
            
            self.path_resolver.put(posix_path, data)
            
            return {
                'success': True,
                'message': f'File written to {path}'
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    # Edit operations
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
        try:
            posix_path = PurePosixPath(path)
            
            # Decode content based on encoding
            if encoding == 'base64':
                import base64
                data = base64.b64decode(content)
            elif encoding == 'text':
                data = content.encode('utf-8')
            else:
                raise ValueError(f"Unsupported encoding: {encoding}")
            
            op_id = self.path_resolver.patch(posix_path, (start, end), data, session_id)
            
            return {
                'success': True,
                'op_id': op_id,
                'message': f'Patch applied to {path}'
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def commit(self, op_id: Optional[str] = None, session_id: Optional[str] = None) -> Dict[str, Any]:
        """Commit patches.
        
        Args:
            op_id: Optional operation ID
            session_id: Optional session ID
            
        Returns:
            Commit status and message
        """
        try:
            success, message = self.path_resolver.commit(op_id, session_id)
            return {
                'success': success,
                'message': message
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def abort(self, op_id: Optional[str] = None, session_id: Optional[str] = None) -> Dict[str, Any]:
        """Abort patches.
        
        Args:
            op_id: Optional operation ID
            session_id: Optional session ID
            
        Returns:
            Abort status and message
        """
        try:
            success, message = self.path_resolver.abort(op_id, session_id)
            return {
                'success': success,
                'message': message
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    # Session management
    def create_session(self, session_name: Optional[str] = None) -> Dict[str, Any]:
        """Create a new edit session.
        
        Args:
            session_name: Optional name for the session
            
        Returns:
            Session ID and info
        """
        try:
            session_id = str(uuid.uuid4())
            if not session_name:
                session_name = f"session_{session_id[:8]}"
            
            self.sessions[session_id] = session_name
            
            # Create session in edit manager
            self.path_resolver.edit_manager.create_session(session_id)
            
            return {
                'success': True,
                'session_id': session_id,
                'session_name': session_name
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def list_sessions(self) -> Dict[str, Any]:
        """List all active sessions.
        
        Returns:
            List of active sessions
        """
        try:
            sessions_info = []
            for session_id, session_name in self.sessions.items():
                sessions_info.append({
                    'session_id': session_id,
                    'session_name': session_name
                })
            
            return {
                'success': True,
                'sessions': sessions_info
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def close_session(self, session_id: str) -> Dict[str, Any]:
        """Close a session (abort all its operations).
        
        Args:
            session_id: Session ID to close
            
        Returns:
            Close status and message
        """
        try:
            if session_id in self.sessions:
                # Abort all operations in the session
                success, message = self.path_resolver.abort(session_id=session_id)
                
                # Remove from sessions
                del self.sessions[session_id]
                
                return {
                    'success': success,
                    'message': f'Session closed: {message}'
                }
            else:
                return {
                    'success': False,
                    'error': f'Session not found: {session_id}'
                }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }