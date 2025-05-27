#
# Copyright 2025 coreseek.com
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
"""Default implementation of the Module protocol."""

from pathlib import Path
from typing import Dict, List, Optional, TypeVar

from ..protocol.module import Module, ModuleOrder, Project, ModuleTagging
from ..protocol.vfs import VFS
from .module_config import YamlModuleConfig
from .order import YamlOrder
from .module_tag import FileBasedModuleTags

#if TYPE_CHECKING:
#    from .project import _YamlProject # Avoid circular imports

T = TypeVar('T', bound='BaseModule')

class BaseModule(Module):
    """Base implementation of the Module protocol."""
    
    def __init__(self, path: Path, vfs: VFS, project: Optional['Project'] = None):
        """Initialize the module.
        
        Args:
            project: The project this module belongs to. Can be set later using _set_project().
            path: The filesystem path of the module.
            vfs: The virtual filesystem to use for file operations.
            
        Note:
            The project parameter is optional and can be set later using _set_project().
        """
        self._project = project
        self._path = path
        self._vfs = vfs
        self._config: Optional[YamlModuleConfig] = None
        self._order: Optional[ModuleOrder] = None
        self._tagging: Optional[ModuleTagging] = None
        self._submodules: Dict[str, 'BaseModule'] = {}
        self._initialized = False
    
    def _set_project(self, project: 'Project') -> None:
        """Set the project for this module.
        
        Args:
            project: The project this module belongs to.
            
        Raises:
            ValueError: If project is None or already set to a different project.
        """
        if project is None:
            raise ValueError("Project cannot be None")
        if self._project is not None and self._project is not project:
            raise ValueError("Project is already set to a different instance")
        self._project = project
    
    @property
    def path(self) -> Path:
        """Get the module's filesystem path."""
        return self._path
        
    @property
    def prefix(self) -> Optional[str]:
        """Get the module's prefix from config.
        
        Returns:
            The prefix string if configured, None otherwise.
        """
        if self.config and 'prefix' in self.config.settings:
            return self.config.settings['prefix']
        return None
    
    @property
    def tags(self) -> ModuleTagging:
        """Get the project's global tagging interface.
        
        The tags are managed at the project level and are available to all modules.
        
        Returns:
            The module's tagging interface.
            
        Raises:
            RuntimeError: If the module is not associated with a project.
        """
        if self._project is None:
            raise RuntimeError("Cannot access tags: module is not associated with a project")
            
        if self._tagging is None:
            self._tagging = FileBasedModuleTags(self._project, self._path, self._vfs)
        return self._tagging

    @property
    def config(self) -> YamlModuleConfig:
        """Get the module's configuration."""
        if self._config is None:
            self._config = YamlModuleConfig.load(self._path, self._vfs)
        return self._config
    
    @property
    def order(self) -> ModuleOrder:
        """Get the module's ordering interface."""
        if self._order is None:
            self._order = YamlOrder(self._path, self._vfs)
            # Set the prefix from config if available
            if hasattr(self._order, 'set_prefix') and hasattr(self, 'config'):
                prefix = self.config.settings.get('prefix', '')
                if prefix is not None:
                    self._order.set_prefix(prefix)
        return self._order
    
    def _ensure_initialized(self) -> None:
        """Ensure the module is initialized."""
        if self._initialized:
            return
            
        try:
            # Load configuration
            self._config = YamlModuleConfig.load(self._path, self._vfs)
            
            # Initialize order
            self._order = YamlOrder(self._path, self._vfs)
            
            # Set the prefix from config if available
            if hasattr(self._order, 'set_prefix') and hasattr(self, 'config'):
                prefix = self.config.settings.get('prefix', '')
                if prefix is not None:
                    self._order.set_prefix(prefix)
  
            # Load submodules
            self._load_submodules()
            
            self._initialized = True
        except Exception as e:
            raise RuntimeError(f"Failed to initialize module at {self._path}: {e}") from e
    
    def _load_submodules(self) -> None:
        """Load submodules."""
        if self._vfs.isdir(self._path):
            for entry in self._vfs.listdir(self._path):
                # Get the full path of the entry
                entry_path = self._path / entry.name
                if self._vfs.isdir(entry_path):
                    module = self._create_submodule(entry.name, entry_path)
                    self._submodules[entry.name] = module
    
    def _create_submodule(self, name: str, path: Optional[Path] = None) -> 'BaseModule':
        """Create a new submodule instance."""
        module_path = path or (self._path / name)
        return self.__class__(module_path, self._vfs, self)
    
    def get_submodules(self) -> List[Module]:
        """Get all direct submodules of this module."""
        self._ensure_initialized()
        return list(self._submodules.values())
    
    def find_submodule(self, path: Path) -> Optional[Module]:
        """Find a submodule by its path."""
        try:
            rel_path = path.relative_to(self._path)
        except ValueError:
            return None
            
        parts = list(rel_path.parts)
        if not parts:
            return self
            
        self._ensure_initialized()
        
        current = self._submodules.get(parts[0])
        if current is None:
            return None
            
        if len(parts) == 1:
            return current
            
        return current.find_submodule(path)
    
    def create_submodule(self, name: str) -> Module:
        """Create a new submodule."""
        if not name or any(c in name for c in '/\\'):
            raise ValueError(f"Invalid module name: {name}")
            
        self._ensure_initialized()
        
        if name in self._submodules:
            raise ValueError(f"Module already exists: {name}")
        
        module_path = self._path / name
        self._vfs.makedirs(module_path, exist_ok=True)
        
        module = self._create_submodule(name, module_path)
        self._submodules[name] = module
        
        return module
    
    def save(self) -> None:
        """Save any changes to the module."""
        if self._config is not None:
            self._config.save(self._vfs)
        
        # Save all submodules
        for module in self._submodules.values():
            module.save()
            
    def get_document_item(self, id: str) -> 'DocumentItem':
        """Get a DocumentCaseItem for the given ID using this module's prefix and settings.
        
        The returned DocumentItem will use this module's prefix, settings and the provided ID.
        This does not require the item to exist on disk.
        
        Args:
            id: The ID of the document item.
                
        Returns:
            A DocumentItem with the module's prefix, settings and the given ID.
            
        Raises:
            ValueError: If the module doesn't have a prefix set or ID is invalid.
        """
        if not id:
            raise ValueError("Document ID cannot be empty")
            
        prefix = self.prefix
        if not prefix:
            raise ValueError("Cannot create document item: module has no prefix")
            
        # Get relevant settings from config
        settings = {}
        if self._config and hasattr(self._config, 'settings'):
            # Create a copy of the settings to avoid modifying the original
            settings = dict(self._config.settings)
            # Ensure we have default values
            settings.setdefault('sep', '-')
            # Always use the module's prefix, not the one from settings
            settings['prefix'] = prefix
            
        from .document_item import DocumentItem
        return DocumentItem(id=id, prefix=prefix, settings=settings)

class YamlModule(BaseModule):
    pass  # 作为别名
