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
from .client import VFSClient, VFSClientException
from .collection.collection_manager import ResourceCollectionManagerImpl



class TextCaseFactory:
    """Factory for creating TextCase instances.
    
    This factory uses ConfigService to initialize and configure
    TextCase instances with proper VFS and service registry setup.
    
    The factory maintains a weak reference cache to ensure the same
    repository path returns the same TextCase instance.
    """
    
    _instance_cache = WeakValueDictionary()
    
    def create(self, file_path: Union[str, Path], collection_name: str = "ROOT", force: bool = False) -> 'TextCase':
        """Create a TextCase instance from scratch.
        
        This method:
        1. Determines the Git repository root from the given file_path (if possible)
        2. Initializes a new TextCase instance
        3. Creates a root collection at the specified file_path
        
        Args:
            file_path: Path where the root collection will be created
            collection_name: Name for the root collection (default: "ROOT")
            force: If True, force creation even if collection already exists
            
        Returns:
            Configured TextCase instance with initialized root collection
        """
        # Use current factory instance
        factory = self
        
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
        
        # Create new instance
        instance = TextCase(repo_root_path, factory.config_service)
        
        # Start services to ensure VFS is available
        instance.start_services()
        
        # 将Windows风格路径转换为POSIX风格
        vfs_path = instance.vfs.to_vfs_path(Path(abs_path))

        # Create root collection at the specified path
        instance.resource_manager.create_collection(
            name=collection_name,
            parent=None,
            path=vfs_path,
            force=force
        )
        
        # Cache the instance
        cache_key = (repo_root_path, factory.config_file)
        self.__class__._instance_cache[cache_key] = instance
        
        return instance
    
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
        
        # Resource collection manager will be initialized when vfs is available
        self._resource_manager = None
        
    def start_services(self) -> None:
        """Start all services."""
        self._vfs_endpoint = self.service_registry.get_service('vfs')
        
    def stop_services(self) -> None:
        """Stop all services."""    
        self.service_registry.stop_service('vfs')
        self._vfs_endpoint = None
        self._vfs_client = None
        self._resource_manager = None
        
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
            # Pass service_registry for direct backend support
            self._vfs_client = VFSClient(endpoint, service_registry=self.service_registry)
        return self._vfs_client
    
    @property
    def resource_manager(self) -> ResourceCollectionManagerImpl:
        """Get resource collection manager for managing collections.
        
        Returns:
            ResourceCollectionManagerImpl instance
        """
        if self._resource_manager is None:
            self._resource_manager = ResourceCollectionManagerImpl(self.repo_root_path, self.vfs)
        return self._resource_manager
        
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