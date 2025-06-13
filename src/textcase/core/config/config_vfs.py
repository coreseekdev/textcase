#!/usr/bin/env python3
"""
VFS Configuration Module

This module handles VFS-specific configuration loading and management.
"""

import os
from typing import Optional, Dict, Any
from pathlib import Path
from .config_service import ConfigService


class VFSConfig:
    """VFS configuration handler.
    
    This class manages VFS-specific configuration including:
    - Root path detection and validation
    - Environment variable loading
    - Default value management
    """
    
    def __init__(self, config_service: ConfigService):
        """Initialize VFS configuration.
        
        Args:
            config_service: ConfigService instance to use
        """
        self.config = config_service
        self._load_defaults()
    
    @property
    def defaults(self) -> Dict[str, Any]:
        """Get default VFS configuration values.
        
        Returns:
            Default VFS configuration dictionary
        """
        defaults = {
            'vfs.root_path': '.',
            'vfs.enable_git_repo': True,
        }
        
        return defaults

    def _load_defaults(self) -> None:
        """Load default VFS configuration values."""
        for key, value in self.defaults.items():
            self.config.set_temporary(key, value, override=False)
    
    def load_from_env(self, prefix: str = "TCE_VFS_") -> None:
        """Load VFS configuration from environment variables.
        
        Args:
            prefix: Environment variable prefix
        """
        # VFS root path
        root_path = os.environ.get(f'{prefix}ROOT_PATH')
        if root_path:
            self.config.set_temporary('vfs.root_path', root_path)
        
        # Enable git repo
        enable_git = os.environ.get(f'{prefix}ENABLE_GIT_REPO')
        if enable_git:
            self.config.set_temporary('vfs.enable_git_repo', self._parse_bool(enable_git))
    
    def set_root_path(self, root_path: str, is_default: bool = False) -> bool:
        """Set VFS root path.
        
        Args:
            root_path: Path to set as VFS root
            is_default: Whether this is a default value
            
        Returns:
            True if value was set, False if skipped
        """
        # Normalize and validate path
        normalized_path = os.path.abspath(os.path.expanduser(root_path))
        
        return self.config.set_temporary(
            'vfs.root_path', 
            normalized_path, 
            override=not is_default
        )
    
    def get_root_path(self) -> str:
        """Get VFS root path.
        
        Returns:
            VFS root path
        """
        key = 'vfs.root_path'
        return self.config.get(key, self.defaults[key])
    
    def validate_root_path(self) -> bool:
        """Validate VFS root path exists and is accessible.
        
        Returns:
            True if path is valid, False otherwise
        """
        root_path = self.get_root_path()
        try:
            path = Path(root_path)
            return path.exists() and path.is_dir()
        except (OSError, ValueError):
            return False
    
    def get_config_dict(self) -> Dict[str, Any]:
        """Get VFS configuration as dictionary.
        
        Returns:
            VFS configuration dictionary
        """
        return {
            'root_path': self.config.get('vfs.root_path', 
                self.defaults['vfs.root_path']),
            'enable_git_repo': self.config.get('vfs.enable_git_repo', 
                self.defaults['vfs.enable_git_repo']),
        }
    
    def print_summary(self) -> None:
        """Print VFS configuration summary."""
        config = self.get_config_dict()
        print("VFS Configuration:")
        print(f"  Root Path: {config['root_path']}")
        print(f"  Git Repo Support: {config['enable_git_repo']}")
        
        # Validation status
        is_valid = self.validate_root_path()
        print(f"  Path Valid: {is_valid}")
    
    @staticmethod
    def _parse_bool(value: str) -> bool:
        """Parse boolean value from string.
        
        Args:
            value: String value to parse
            
        Returns:
            Boolean value
        """
        return value.lower() in ('true', '1', 'yes', 'on', 'enabled')


def setup_vfs_config(
    config_service: ConfigService,
    root_path: Optional[str] = None,
    load_env: bool = True
) -> VFSConfig:
    """Setup VFS configuration.
    
    Args:
        config_service: ConfigService instance
        root_path: Optional root path to set
        load_env: Whether to load from environment variables
        
    Returns:
        Configured VFSConfig instance
    """
    vfs_config = VFSConfig(config_service)
    
    if load_env:
        vfs_config.load_from_env()
    
    if root_path:
        vfs_config.set_root_path(root_path, is_default=False)
    
    return vfs_config
