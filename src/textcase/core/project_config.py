"""
Project configuration implementation.

This module provides the YAML-based implementation of the ProjectConfig protocol.
"""

from pathlib import Path
from typing import Any, Dict, List, Optional, cast

import yaml

from ..protocol.module import ProjectConfig, SubmoduleInfo
from ..protocol.vfs import VFS
from .module_config import YamlModuleConfig

__all__ = ['YamlProjectConfig']

class YamlProjectConfig(YamlModuleConfig, ProjectConfig):
    """YAML-based implementation of ProjectConfig.
    
    This implementation extends YamlModuleConfig to support submodule management.
    Submodule information is stored in the 'modules' section of .textcase.yml.
    """
    
    def __init__(self, path: Path, settings: Dict[str, Any] = None, tags: Dict[str, str] = None, modules: Dict[str, Any] = None):
        """Initialize the project configuration.
        
        Args:
            path: The path to the project root directory.
            settings: Optional initial settings.
            tags: Optional initial tags.
            modules: Optional initial modules configuration.
        """
        super().__init__(path, settings or {}, tags or {})
        self._modules: Dict[str, Dict[str, str]] = modules or {}
        
    @classmethod
    def load(cls, path: Path, vfs: VFS) -> 'YamlProjectConfig':
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
            tags=data.get('tags', {}),
            modules=data.get('modules', {})
        )
    
    def save(self, vfs: VFS) -> None:
        """Save configuration to a YAML file."""
        data = {
            'settings': self.settings,
            'tags': self.tags,
            'modules': self._modules
        }
        
        config_path = self.path / '.textcase.yml'
        
        # Ensure parent directory exists
        vfs.makedirs(self.path, exist_ok=True)
        
        # Use a temporary file for atomic write
        temp_path = config_path.with_suffix('.tmp')
        try:
            with vfs.open(temp_path, 'w') as f:
                yaml.safe_dump(data, f, default_flow_style=False)
            
            # Rename temp file to target (atomic on POSIX systems)
            if vfs.exists(config_path):
                vfs.remove(config_path)
            vfs.move(temp_path, config_path)
            
        except Exception as e:
            # Clean up temp file if it exists
            if vfs.exists(temp_path):
                vfs.remove(temp_path)
            raise
    
    def add_submodule(self, prefix: str, path: Path, parent_prefix: Optional[str] = None) -> None:
        if not prefix or not prefix.strip():
            raise ValueError("Prefix cannot be empty")
        
        if self.get_submodule(prefix) is not None:
            raise ValueError(f"A submodule with prefix '{prefix}' already exists")
        
        # Use parent's prefix or empty string for root modules
        parent_key = parent_prefix if parent_prefix is not None and parent_prefix.strip() else ''
        
        # Add to modules dictionary
        if parent_key not in self._modules:
            self._modules[parent_key] = {}
            
        # Store path with forward slashes for consistency
        path_str = str(path).replace('\\', '/')
        self._modules[parent_key][prefix] = path_str
    
    def remove_submodule(self, prefix: str) -> None:
        found = False
        for parent_key, modules in list(self._modules.items()):
            if prefix in modules:
                # Check if this module has children
                children = self.get_children(prefix)
                if children:
                    raise ValueError(f"Cannot remove module '{prefix}': it has child modules")
                
                del self._modules[parent_key][prefix]
                # Remove parent entry if empty
                if not self._modules[parent_key]:
                    del self._modules[parent_key]
                found = True
                break
                
        if not found:
            raise KeyError(f"No submodule with prefix '{prefix}' found")
            
        self._save_modules()
    
    def get_submodule(self, prefix: str) -> Optional[SubmoduleInfo]:
        for parent_key, modules in self._modules.items():
            if prefix in modules:
                # Convert path to Path object, handling forward slashes
                path_str = modules[prefix]
                path = Path(path_str.replace('/', '\\') if '\\' in path_str else path_str)
                return SubmoduleInfo(
                    prefix=prefix,
                    path=path,
                    parent_prefix=parent_key if parent_key else None
                )
        return None
    
    def get_children(self, prefix: Optional[str] = None) -> List[SubmoduleInfo]:
        parent_key = prefix if prefix is not None else ''
        if parent_key not in self._modules:
            return []
            
        return [
            SubmoduleInfo(
                prefix=child_prefix,
                path=Path(path_str),
                parent_prefix=parent_key if parent_key else None
            )
            for child_prefix, path_str in self._modules[parent_key].items()
        ]
    
    def get_parent(self, prefix: str) -> Optional[SubmoduleInfo]:
        submodule = self.get_submodule(prefix)
        if submodule is None or submodule.parent_prefix is None:
            return None
            
        return self.get_submodule(submodule.parent_prefix)
    
    def get_all_submodules(self) -> Dict[str, SubmoduleInfo]:
        result = {}
        for parent_key, modules in self._modules.items():
            for prefix, path_str in modules.items():
                result[prefix] = SubmoduleInfo(
                    prefix=prefix,
                    path=Path(path_str),
                    parent_prefix=parent_key if parent_key else None
                )
        return result
