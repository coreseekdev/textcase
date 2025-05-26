"""
Module configuration implementation.

This module provides the YAML-based implementation of the ModuleConfig protocol.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Optional

import yaml

from ..protocol.module import ModuleConfig
from ..protocol.vfs import VFS

__all__ = ['YamlModuleConfig']

@dataclass
class YamlModuleConfig(ModuleConfig):
    """YAML-based implementation of ModuleConfig.
    
    This implementation stores configuration in a YAML file at `.textcase.yml`
    within the module directory.
    """
    path: Path
    """The filesystem path of the module."""
    
    settings: Dict[str, Any] = field(default_factory=dict)
    """Module settings as key-value pairs."""
    
    tags: Dict[str, str] = field(default_factory=dict)
    """Module tags as key-description pairs."""
    
    @classmethod
    def load(cls, path: Path, vfs: VFS) -> 'YamlModuleConfig':
        """Load configuration from a YAML file.
        
        Args:
            path: The path to the module directory.
            vfs: The virtual filesystem to use for loading.
            
        Returns:
            A new YamlModuleConfig instance loaded from storage.
        """
        config_path = path / '.textcase.yml'
        if not vfs.exists(config_path):
            return cls(path=path)
            
        with vfs.open(config_path, 'r') as f:
            data = yaml.safe_load(f) or {}
            
        return cls(
            path=path,
            settings=data.get('settings', {}),
            tags=data.get('tags', {})
        )
    
    def save(self, vfs: VFS) -> None:
        """Save configuration to a YAML file.
        
        Args:
            vfs: The virtual filesystem to use for saving.
            
        Raises:
            OSError: If the configuration file cannot be written.
        """
        config_path = self.path / '.textcase.yml'
        
        # Ensure the parent directory exists
        if not vfs.exists(self.path):
            vfs.makedirs(self.path, exist_ok=True)
            
        data = {
            'settings': self.settings,
            'tags': self.tags
        }
        
        # Use a temporary file for atomic write
        temp_path = config_path.with_suffix('.tmp')
        try:
            with vfs.open(temp_path, 'w') as f:
                yaml.safe_dump(data, f, default_flow_style=False)
            
            # Move temp file to target (atomic on POSIX systems)
            if vfs.exists(config_path):
                vfs.remove(config_path)
            vfs.move(temp_path, config_path)
            
        except Exception as e:
            # Clean up temp file if it exists
            if vfs.exists(temp_path):
                vfs.remove(temp_path)
            raise
    
    def update_settings(self, settings: Dict[str, Any]) -> None:
        """Update module settings.
        
        Args:
            settings: Dictionary of settings to update.
        """
        self.settings.update(settings)
    
    def update_tags(self, tags: Dict[str, str]) -> None:
        """Update module tags.
        
        Args:
            tags: Dictionary of tags to update.
        """
        self.tags.update(tags)
