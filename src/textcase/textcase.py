#!/usr/bin/env python3
"""
TextCase main module.

This module provides the main TextCase class and factory for creating
TextCase instances with proper configuration and service initialization.
"""

import os
from pathlib import Path
from typing import Optional, Dict, Any, Union
from weakref import WeakValueDictionary

from .core.config.config_service import ConfigService
from .core.config.config_vfs import setup_vfs_config
from .service.service_registry_impl import create_service_registry
from .scm.git import find_git_repo_root
from .client.vfs_client import VFSClient, VFSClientException



class TextCaseFactory:
    """Factory for creating TextCase instances.
    
    This factory uses ConfigService to initialize and configure
    TextCase instances with proper VFS and service registry setup.
    
    The factory maintains a weak reference cache to ensure the same
    repository path returns the same TextCase instance.
    """
    
    _instance_cache = WeakValueDictionary()
    
    def __init__(self, config_file: Optional[str] = None):
        """Initialize TextCase factory.
        
        Args:
            config_file: Optional path to configuration file
        """
        self.config_file = config_file
        self.config_service = ConfigService(config_file)
        
    def get(self, file_path: Union[str, Path]) -> 'TextCase':
        """Get a TextCase instance for the given file path.
        
        This method automatically locates the Git repository root from the given file path.
        If no Git repository is found up to the filesystem root, uses the file_path as repo_root_path.
        
        The method maintains a cache to ensure the same repository path
        returns the same TextCase instance.
        
        Args:
            file_path: Any file or directory path
            
        Returns:
            Configured TextCase instance
        """
        # Convert to absolute path
        abs_path = os.path.abspath(str(file_path))
        
        # If it's a file, get its directory
        if os.path.isfile(abs_path):
            search_path = os.path.dirname(abs_path)
        else:
            search_path = abs_path
            
        # Try to find Git repository root
        git_info = find_git_repo_root(search_path)
        
        if git_info and git_info.repo_root:
            # Use Git repository root
            repo_root_path = git_info.repo_root
        else:
            # No Git repository found, use the search path as repo root
            repo_root_path = search_path
            
        # Check cache first
        cache_key = (repo_root_path, self.config_file)
        if cache_key in self._instance_cache:
            return self._instance_cache[cache_key]
            
        # Create new instance and cache it
        instance = TextCase(repo_root_path, self.config_service)
        self._instance_cache[cache_key] = instance
        return instance
        
    def __repr__(self):
        """String representation of TextCaseFactory."""
        config_info = f"config_file='{self.config_file}'" if self.config_file else "config_file=None"
        return f"TextCaseFactory({config_info})"


class TextCase:
    """Main TextCase class.
    
    This class provides the main interface for TextCase functionality,
    holding VFS, configuration, and service registry instances.
    """
    
    def __init__(self, repo_root_path: str, config_service: ConfigService):
        """Initialize TextCase instance.
        
        Args:
            repo_root_path: Path to the repository root
            config_service: ConfigService instance
        """
        self.repo_root_path = os.path.abspath(repo_root_path)
        self._config_service = config_service
        
        # Setup VFS configuration
        self.vfs_config = setup_vfs_config(
            config_service=self._config_service,
            root_path=self.repo_root_path,
            load_env=self._config_service.get('vfs.load_env', True)
        )
        
        # Set vfs.repo_path as a alias of vfs.root_path
        self._config_service.set_temporary('vfs.repo_path', self.repo_root_path)
        
        # root_path / '.textcase.yml' 的配置，用于初始化 文档/资源 管理器， 此处不需要
        
        # Create service registry
        self.service_registry = create_service_registry(self._config_service)
        
        # VFS service will be initialized when needed
        self._vfs_endpoint = None
        self._vfs_client = None
        
    def start_services(self) -> None:
        """Start all services."""
        self._vfs_endpoint = self.service_registry.get_service('vfs')
        
    def stop_services(self) -> None:
        """Stop all services."""    
        self.service_registry.stop_service('vfs')
        self._vfs_endpoint = None
        self._vfs_client = None
        
    def get_vfs_endpoint(self) -> str:
        """Get VFS service endpoint.
        
        Returns:
            VFS service endpoint
        """
        if self._vfs_endpoint is None:
            self._vfs_endpoint = self.service_registry.get_service('vfs')
        return self._vfs_endpoint
        
    @property
    def vfs(self) -> VFSClient:
        """Get VFS client for interacting with VFS service.
        
        Returns:
            VFS client instance
        """
        if self._vfs_client is None:
            endpoint = self.get_vfs_endpoint()
            self._vfs_client = VFSClient(endpoint)
        return self._vfs_client
        
    def get_config_value(self, key: str, default: Any = None) -> Any:
        """Get configuration value.
        
        Args:
            key: Configuration key
            default: Default value if key not found
            
        Returns:
            Configuration value
        """
        return self.conf.get(key, default)
        
    def set_config_value(self, key: str, value: Any) -> Any:
        """Set configuration value.
        
        Args:
            key: Configuration key
            value: Value to set
            
        Returns:
            Previous value
        """
        return self.conf.set(key, value)
         
    def __repr__(self):
        return f"TextCase(repo_root_path='{self.repo_root_path}')"