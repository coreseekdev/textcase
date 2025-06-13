"""VFS Service implementation for service registry.

This module provides a VFS service that can be registered with
the service registry and accessed via zerorpc.
"""

import logging
from typing import Dict, Any, Optional

from ..service.vfs_server import VFSServer


logger = logging.getLogger(__name__)


class VFSService:
    """VFS Service for service registry.
    
    This service wraps the VFS server and provides a standardized
    interface for the service registry system.
    """
    
    def __init__(self, repo_path: str, **kwargs):
        """Initialize VFS service.
        
        Args:
            repo_path: Path to the repository
            **kwargs: Additional service configuration
        """
        self.repo_path = repo_path
        self.config = kwargs
        self._server = None
        logger.info(f"VFS Service initialized for repo: {repo_path}")
    
    def start(self) -> None:
        """Start the VFS service."""
        if self._server is None:
            self._server = VFSServer(self.repo_path)
            logger.info(f"VFS Service started for repo: {self.repo_path}")
    
    def stop(self) -> None:
        """Stop the VFS service."""
        if self._server is not None:
            self._server = None
            logger.info(f"VFS Service stopped for repo: {self.repo_path}")
    
    def get_server(self) -> VFSServer:
        """Get the VFS server instance.
        
        Returns:
            VFS server instance
            
        Raises:
            RuntimeError: If service is not started
        """
        if self._server is None:
            raise RuntimeError("VFS Service not started")
        return self._server
    
    def health_check(self) -> Dict[str, Any]:
        """Perform health check.
        
        Returns:
            Health status information
        """
        try:
            if self._server is None:
                return {
                    'status': 'stopped',
                    'repo_path': self.repo_path,
                    'healthy': False
                }
            
            # Try to get service name to verify it's working
            name = self._server.name()
            
            return {
                'status': 'running',
                'repo_path': self.repo_path,
                'service_name': name,
                'healthy': True
            }
        except Exception as e:
            logger.error(f"VFS Service health check failed: {e}")
            return {
                'status': 'error',
                'repo_path': self.repo_path,
                'error': str(e),
                'healthy': False
            }
    
    def get_info(self) -> Dict[str, Any]:
        """Get service information.
        
        Returns:
            Service information
        """
        return {
            'service_type': 'vfs',
            'repo_path': self.repo_path,
            'config': self.config,
            'running': self._server is not None
        }


def create_vfs_service(repo_path: str, **kwargs) -> VFSService:
    """Create a VFS service instance.
    
    Args:
        repo_path: Path to the repository
        **kwargs: Additional service configuration
        
    Returns:
        VFS service instance
    """
    return VFSService(repo_path, **kwargs)