"""
Project configuration implementation.

This module provides the YAML-based implementation of the ProjectConfig protocol.
"""

from pathlib import Path
from typing import Any, Dict, List, Optional, cast

from ..protocol.module import ProjectConfig, SubmoduleInfo
from .module_config import YamlModuleConfig

__all__ = ['YamlProjectConfig']

class YamlProjectConfig(YamlModuleConfig, ProjectConfig):
    """YAML-based implementation of ProjectConfig.
    
    This implementation extends YamlModuleConfig to support submodule management.
    Submodule information is stored in the 'modules' section of .textcase.yml.
    """
    
    def __init__(self, path: Path, settings: Dict[str, Any] = None, tags: Dict[str, str] = None):
        """Initialize the project configuration.
        
        Args:
            path: The path to the project root directory.
            settings: Optional initial settings.
            tags: Optional initial tags.
        """
        super().__init__(path, settings or {}, tags or {})
        self._modules: Dict[str, Dict[str, str]] = {}
        self._load_modules()
    
    def _load_modules(self) -> None:
        """Load module information from the configuration file."""
        if 'modules' in self.settings and isinstance(self.settings['modules'], dict):
            self._modules = cast(Dict[str, Dict[str, str]], self.settings['modules'])
    
    def _save_modules(self) -> None:
        """Save module information to the settings dictionary."""
        if self._modules:
            self.settings['modules'] = self._modules
    
    def add_submodule(self, prefix: str, path: Path, parent_prefix: Optional[str] = None) -> None:
        if not prefix or not prefix.strip():
            raise ValueError("Prefix cannot be empty")
        
        if self.get_submodule(prefix) is not None:
            raise ValueError(f"A submodule with prefix '{prefix}' already exists")
        
        parent_key = parent_prefix if parent_prefix is not None else ''
        
        if parent_key not in self._modules:
            self._modules[parent_key] = {}
            
        self._modules[parent_key][prefix] = str(path)
        self._save_modules()
    
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
                return SubmoduleInfo(
                    prefix=prefix,
                    path=Path(modules[prefix]),
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
