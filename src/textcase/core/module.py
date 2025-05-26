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

import os
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Type, TypeVar, cast

from ..protocol.module import Module, ModuleConfig, ModuleOrder, ModuleTags
from ..protocol.vfs_protocol import VFS
from .order import YamlOrder
from .tags import FileBasedTags

T = TypeVar('T', bound='BaseModule')

class BaseModule(Module):
    """Base implementation of the Module protocol."""
    
    def __init__(self, path: Path, vfs: VFS, parent: Optional['BaseModule'] = None):
        """Initialize the module."""
        self._path = path
        self._vfs = vfs
        self._parent = parent
        self._config: Optional[ModuleConfig] = None
        self._order: Optional[ModuleOrder] = None
        self._tags: Optional[ModuleTags] = None
        self._submodules: Dict[str, 'BaseModule'] = {}
        self._initialized = False
    
    @property
    def path(self) -> Path:
        """Get the module's filesystem path."""
        return self._path
    
    @property
    def config(self) -> ModuleConfig:
        """Get the module's configuration."""
        if self._config is None:
            self._config = ModuleConfig.load(self._path, self._vfs)
        return self._config
    
    @property
    def order(self) -> ModuleOrder:
        """Get the module's ordering interface."""
        if self._order is None:
            self._order = YamlOrder(self._path, self._vfs)
        return self._order
    
    @property
    def tags(self) -> ModuleTags:
        """Get the module's tagging interface."""
        if self._tags is None:
            self._tags = FileBasedTags(self._path, self._vfs)
        return self._tags
    
    def _ensure_initialized(self) -> None:
        """Ensure the module is initialized."""
        if self._initialized:
            return
            
        # Load submodules
        if self._vfs.isdir(self._path):
            for entry in self._vfs.listdir(self._path):
                # Get the full path of the entry
                entry_path = self._path / entry.name
                if self._vfs.isdir(entry_path):
                    module = self._create_submodule(entry.name, entry_path)
                    self._submodules[entry.name] = module
        
        self._initialized = True
    
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

class ProjectModule(BaseModule):
    """Root module representing a project."""
    
    @classmethod
    def create(
        cls: Type[T],
        path: Path,
        vfs: VFS,
        settings: Optional[Dict[str, Any]] = None,
        tags: Optional[Dict[str, str]] = None
    ) -> 'ProjectModule':
        """Create a new project."""
        # Create the project directory if it doesn't exist
        if not vfs.exists(path):
            vfs.makedirs(path, exist_ok=True)
        
        project = cls(path, vfs)
        
        # Initialize default settings
        if settings:
            project.config.settings.update(settings)
        
        # Initialize default tags
        if tags:
            project.config.tags.update(tags)
        
        # Save the initial configuration
        project.save()
        
        return project
    
    @classmethod
    def load(cls: Type[T], path: Path, vfs: VFS) -> 'ProjectModule':
        """Load an existing project."""
        if not vfs.exists(path):
            raise FileNotFoundError(f"Project directory not found: {path}")
            
        return cls(path, vfs)
