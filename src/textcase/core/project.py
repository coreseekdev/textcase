"""
Project implementation.

This module provides the implementation of the Project protocol.
"""

from pathlib import Path
from typing import Dict, List, Optional, cast

from ..protocol.module import Module, Project, SubmoduleInfo
from ..protocol.vfs import VFS
from .module import YamlModule
from .project_config import YamlProjectConfig
from .vfs import get_default_vfs

# Private implementation class
class _YamlProject(YamlModule, Project):
    """YAML-based implementation of Project.
    
    This implementation provides project-level functionality including
    submodule management.
    """
    
    def __init__(self, path: Path, vfs: Optional[VFS] = None):
        """Initialize the project.
        
        Args:
            path: The path to the project root directory.
            vfs: Optional virtual filesystem to use.
        """
        self._vfs = vfs or get_default_vfs()
        # Initialize the parent class first
        super().__init__(path, self._vfs)
        # Then set up project-specific attributes
        self._config = YamlProjectConfig.load(path, self._vfs)
        self._submodules: Dict[str, Module] = {}
        self._load_submodules()
    
    @property
    def config(self) -> YamlProjectConfig:
        return cast(YamlProjectConfig, self._config)
    
    def _load_submodules(self) -> None:
        """Load all submodules for this project."""
        for info in self.config.get_all_submodules().values():
            module_path = self.path / info.path
            self._submodules[info.prefix] = YamlModule(module_path, self._vfs)
    
    def get_submodules(self) -> List[Module]:
        return list(self._submodules.values())
    
    def find_submodule(self, path: Path) -> Optional[Module]:
        # Convert to relative path if it's absolute
        try:
            rel_path = str(path.relative_to(self.path) if path.is_absolute() else path)
        except ValueError:
            return None
            
        # Look for exact match first
        for module in self._submodules.values():
            try:
                module_rel_path = str(module.path.relative_to(self.path))
                if module_rel_path == rel_path:
                    return module
            except ValueError:
                continue
                
        # Look for best match (deepest parent)
        best_match = None
        best_depth = -1
        
        for module in self._submodules.values():
            try:
                module_rel_path = str(module.path.relative_to(self.path))
                if rel_path.startswith(module_rel_path):
                    depth = len(module_rel_path.split('/'))
                    if depth > best_depth:
                        best_depth = depth
                        best_match = module
            except ValueError:
                continue
                
        return best_match
    
    def add_module(self, parent_prefix: str, module: Module) -> None:
        """Add an existing module to the project.
        
        Args:
            parent_prefix: The prefix of the parent module.
            module: The module instance to add.
            
        Raises:
            ValueError: If a module with the same prefix already exists.
            ValueError: If the module's path is not within the project directory.
        """
        # Verify the module path is within the project
        try:
            rel_path = module.path.relative_to(self.path)
        except ValueError:
            raise ValueError("Module path must be within the project directory")
            
        # Check if a module with this prefix already exists
        if module.path.name in (m.path.name for m in self._submodules.values()):
            raise ValueError(f"A module with path '{module.path.name}' already exists")
            
        # Add to project config
        self.config.add_submodule(module.path.name, rel_path, parent_prefix)
        self.config.save(self._vfs)
        
        # Add to submodules cache
        self._submodules[module.path.name] = module
    
    def __getitem__(self, name: str) -> Module:
        for prefix, module in self._submodules.items():
            if module.path.name == name:
                return module
        raise KeyError(f"No submodule named '{name}'")
    
    def remove_submodule(self, name: str) -> None:
        # Find the module by name
        module_to_remove = None
        prefix_to_remove = None
        
        for prefix, module in self._submodules.items():
            if module.path.name == name:
                module_to_remove = module
                prefix_to_remove = prefix
                break
                
        if module_to_remove is None:
            raise KeyError(f"No submodule named '{name}'")
            
        # Check for uncommitted changes
        # This is a placeholder - actual implementation would check VCS status
        
        # Remove from config
        self.config.remove_submodule(prefix_to_remove)
        self.config.save(self._vfs)
        
        # Remove from memory
        del self._submodules[prefix_to_remove]
        
        # Remove the directory
        # In a real implementation, you might want to move to trash instead
        # or require a force flag
        try:
            self._vfs.rmtree(module_to_remove.path)
        except Exception as e:
            raise RuntimeError(f"Failed to remove module directory: {e}") from e
