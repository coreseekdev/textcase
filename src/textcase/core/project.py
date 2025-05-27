"""
Project implementation.

This module provides the implementation of the Project protocol.
"""

from pathlib import Path
from typing import Dict, List, Optional, cast

from ..protocol.module import Module, Project, ProjectTags, SubmoduleInfo
from ..protocol.vfs import VFS
from .module import YamlModule
from .project_config import YamlProjectConfig
# from .project_tag import TagManager
from .vfs import get_default_vfs

# Private implementation class
class _YamlProject(YamlModule, Project, ProjectTags):
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
        super().__init__(path, self._vfs, self)
        # Then set up project-specific attributes
        self._config = YamlProjectConfig.load(path, self._vfs)
        self._submodules: Dict[str, Module] = {}
        #self._tag_manager = TagManager(path, self._vfs)
        self._load_submodules()
    
    @property
    def config(self) -> YamlProjectConfig:
        return cast(YamlProjectConfig, self._config)
        
    def get_tags(self, prefix: str) -> List[str]:
        """Get all available tags for the specified prefix.
        
        This collects tags from the module matching the prefix and all its parent modules
        up to the project root, then returns a deduplicated list of all tags.
        
        Args:
            prefix: The prefix to get tags for.
            
        Returns:
            A sorted list of unique tag names that can be used with the specified prefix.
        """
        # Start with tags from the project config
        all_tags = set(self.config.tags.keys())
        
        # If no prefix is provided, return all project-level tags
        if not prefix:
            return sorted(all_tags)
            
        # Find the module info for the given prefix
        module_info = self.config.get_submodule(prefix)
        if module_info is None:
            return sorted(all_tags)
            
        # Start with the current module's tags
        current_prefix = prefix
        while True:
            # Get the module info for current prefix
            current_info = self.config.get_submodule(current_prefix)
            if current_info is None:
                break
                
            # Add tags from current module's config
            module = self._submodules.get(current_prefix)
            if module and hasattr(module, 'config') and hasattr(module.config, 'tags'):
                all_tags.update(module.config.tags.keys())
                
            # Move to parent module
            if not current_info.parent_prefix:
                break
                
            current_prefix = current_info.parent_prefix
                
        return sorted(all_tags)
    
    def _load_submodules(self) -> None:
        """Load all submodules for this project."""
        for info in self.config.get_all_submodules().values():
            self._load_submodule(info)
    
    def _load_submodule(self, info: SubmoduleInfo) -> Module:
        """Load a single submodule.
        
        Args:
            info: The SubmoduleInfo containing the submodule's metadata.
            
        Returns:
            The loaded module instance.
            
        Raises:
            ValueError: If a module with the same prefix already exists.
        """
        module_path = self.path / info.path
        
        # Check if we already have this module loaded
        if info.prefix in self._submodules:
            return self._submodules[info.prefix]
            
        # Create the module with self as the project
        module = YamlModule(self, module_path, self._vfs)
        
        # Add to submodules dictionary with both name and full prefix as keys
        module_name = module_path.name
        if module_name in self._submodules:
            raise ValueError(f"A module named '{module_name}' already exists")
            
        self._submodules[module_name] = module
        self._submodules[info.prefix] = module  # Also index by full prefix
        
        return module
    
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
            parent_prefix: The prefix of the parent module. Must not be empty.
            module: The module instance to add. Must have a non-empty prefix.
            
        Raises:
            ValueError: If parent_prefix is empty or module has no prefix.
            ValueError: If a module with the same prefix already exists.
            ValueError: If the module's path is not within the project directory.
        """
        # Validate parent_prefix is not empty
        if not parent_prefix or not parent_prefix.strip():
            raise ValueError("parent_prefix cannot be empty")
            
        # Validate module has a valid prefix
        if not module.prefix or not module.prefix.strip():
            raise ValueError("Module must have a non-empty prefix")
            
        # Verify the module path is within the project
        try:
            rel_path = module.path.relative_to(self.path)
        except ValueError:
            raise ValueError("Module path must be within the project directory")
            
        # Check if a module with this path already exists
        if module.path.name in (m.path.name for m in self._submodules.values()):
            raise ValueError(f"A module with path '{module.path.name}' already exists")
            
        # Create module directory if it doesn't exist
        if not self._vfs.exists(module.path):
            self._vfs.makedirs(module.path, exist_ok=True)
        
        # Set the module's project
        module._set_project(self)
            
        # Save the module's configuration
        module.save()
        
        # Convert path to use forward slashes for consistency across platforms
        rel_path_str = str(rel_path).replace('\\', '/')
        
        # Add to project config using the module's prefix and parent's actual prefix
        self.config.add_submodule(module.prefix, Path(rel_path_str), parent_prefix)
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
        # TODO: 是否真的需要物理的删除文件？ 已经 remove submodule 后，理论上已经找不到了。
        try:
            self._vfs.rmtree(module_to_remove.path)
        except Exception as e:
            raise RuntimeError(f"Failed to remove module directory: {e}") from e
