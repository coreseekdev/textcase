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
"""Module protocol and related types."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, NamedTuple, Optional, Protocol, TypeVar, runtime_checkable
import yaml

from .vfs import VFS

__all__ = [
    'ModuleConfig',
    'ProjectConfig',
    'Module',
    'Project',
    'ModuleOrder',
    'ModuleTags',
]

class ModuleConfig(Protocol):
    """Protocol for module configuration."""
    
    path: Path
    """The filesystem path of the module."""
    
    settings: Dict[str, Any]
    """Module settings as key-value pairs."""
    
    tags: Dict[str, str]
    """Module tags as key-description pairs."""

    @classmethod
    def load(cls, path: Path, vfs: VFS) -> 'ModuleConfig':
        """Load configuration from storage.
        
        Args:
            path: The path to the module directory.
            vfs: The virtual filesystem to use for loading.
            
        Returns:
            A new ModuleConfig instance loaded from storage.
        """
        ...
    
    def save(self, vfs: VFS) -> None:
        """Save configuration to storage.
        
        Args:
            vfs: The virtual filesystem to use for saving.
        """
        ...
        
    def update_settings(self, settings: Dict[str, Any]) -> None:
        """Update module settings.
        
        Args:
            settings: Dictionary of settings to update.
        """
        ...
        
    def update_tags(self, tags: Dict[str, str]) -> None:
        """Update module tags.
        
        Args:
            tags: Dictionary of tags to update.
        """
        ...


class SubmoduleInfo(NamedTuple):
    """Information about a submodule in the project."""
    prefix: str
    """The unique prefix key of the submodule."""
    
    path: Path
    """The filesystem path of the submodule."""
    
    parent_prefix: Optional[str]
    """The prefix key of the parent module, None for root modules."""


class ProjectConfig(ModuleConfig, Protocol):
    """Protocol for project configuration, extending ModuleConfig with submodule management.
    
    This configuration adds support for managing submodules within a project,
    including adding, removing, and querying submodule relationships.
    """
    
    @abstractmethod
    def add_submodule(self, prefix: str, path: Path, parent_prefix: Optional[str] = None) -> None:
        """Add a new submodule to the project configuration.
        
        Args:
            prefix: The unique prefix key for the submodule.
            path: The filesystem path of the submodule.
            parent_prefix: Optional prefix of the parent module. None indicates a root-level module.
            
        Raises:
            ValueError: If the prefix is already in use or is invalid.
        """
        ...
        
    @abstractmethod
    def remove_submodule(self, prefix: str) -> None:
        """Remove a submodule from the project configuration.
        
        Args:
            prefix: The prefix key of the submodule to remove.
            
        Raises:
            KeyError: If no submodule with the given prefix exists.
            ValueError: If the submodule has children and force is False.
        """
        ...
        
    @abstractmethod
    def get_submodule(self, prefix: str) -> Optional[SubmoduleInfo]:
        """Get information about a submodule by its prefix.
        
        Args:
            prefix: The prefix key of the submodule to find.
            
        Returns:
            SubmoduleInfo if found, None otherwise.
        """
        ...
        
    @abstractmethod
    def get_children(self, prefix: Optional[str] = None) -> List[SubmoduleInfo]:
        """Get all direct child submodules of the specified module.
        
        Args:
            prefix: The prefix key of the parent module. If None, returns root-level modules.
            
        Returns:
            A list of SubmoduleInfo objects for direct children.
        """
        ...
        
    @abstractmethod
    def get_parent(self, prefix: str) -> Optional[SubmoduleInfo]:
        """Get the parent module of the specified submodule.
        
        Args:
            prefix: The prefix key of the submodule.
            
        Returns:
            SubmoduleInfo of the parent, or None if this is a root module.
        """
        ...
        
    @abstractmethod
    def get_all_submodules(self) -> Dict[str, SubmoduleInfo]:
        """Get all submodules in the project.
        
        Returns:
            A dictionary mapping prefix keys to SubmoduleInfo objects.
        """
        ...

class ModuleOrder(Protocol):
    """Protocol for module ordering functionality."""
    
    @abstractmethod
    def get_ordered_items(self) -> List[Path]:
        """Get items in their defined order."""
        ...
        
    @abstractmethod
    def add_item(self, item: Path) -> None:
        """Add an item to the ordering."""
        ...
        
    @abstractmethod
    def remove_item(self, item: Path) -> None:
        """Remove an item from the ordering."""
        ...

class ModuleTags(Protocol):
    """Protocol for module tagging functionality."""
    
    @abstractmethod
    def get_tags(self) -> Dict[str, List[Path]]:
        """Get all tags and their associated items."""
        ...
        
    @abstractmethod
    def get_items_with_tag(self, tag: str) -> List[Path]:
        """Get all items with the given tag."""
        ...
        
    @abstractmethod
    def add_tag(self, item: Path, tag: str) -> None:
        """Add a tag to an item."""
        ...
        
    @abstractmethod
    def remove_tag(self, item: Path, tag: str) -> None:
        """Remove a tag from an item."""
        ...

class Module(Protocol):
    """Protocol for a module in the project.
    
    A module represents a self-contained unit of functionality with its own
    configuration, ordering, and tagging. Modules can be organized in a hierarchy,
    but the management of submodules is handled by the Project interface.
    """
    
    @property
    @abstractmethod
    def path(self) -> Path:
        """Get the module's filesystem path."""
        ...
        
    @property
    @abstractmethod
    def config(self) -> ModuleConfig:
        """Get the module's configuration."""
        ...
        
    @property
    @abstractmethod
    def order(self) -> ModuleOrder:
        """Get the module's ordering interface."""
        ...
        
    @property
    @abstractmethod
    def tags(self) -> ModuleTags:
        """Get the module's tagging interface."""
        ...
        
    @abstractmethod
    def save(self) -> None:
        """Save any changes to the module."""
        ...


class Project(Module, Protocol):
    """Protocol for a project, which is the root module in the module hierarchy.
    
    A Project is a Module with additional capabilities for managing submodules.
    It inherits all methods from Module and adds project-specific methods.
    """
    
    @property
    @abstractmethod
    def config(self) -> ProjectConfig:
        """Get the project's configuration."""
        ...
    
    @abstractmethod
    def get_submodules(self) -> List[Module]:
        """Get all direct submodules of this project.
        
        Returns:
            A list of Module objects representing the direct submodules.
        """
        ...
        
    @abstractmethod
    def find_submodule(self, path: Path) -> Optional[Module]:
        """Find a submodule by its path.
        
        Args:
            path: The path of the submodule to find, relative to the project root.
            
        Returns:
            The found Module, or None if not found.
        """
        ...
        
    @abstractmethod
    def create_submodule(self, name: str) -> Module:
        """Create a new submodule in the project.
        
        Args:
            name: The name for the new submodule.
            
        Returns:
            The newly created Module.
            
        Raises:
            ValueError: If a submodule with the given name already exists.
        """
        ...
        
    @abstractmethod
    def __getitem__(self, name: str) -> Module:
        """Get a submodule by name.
        
        This provides dictionary-like access to submodules.
        
        Args:
            name: The name of the submodule to get.
            
        Returns:
            The Module with the given name.
            
        Raises:
            KeyError: If no submodule with the given name exists.
        """
        ...
        
    @abstractmethod
    def remove_submodule(self, name: str) -> None:
        """Remove a submodule from the project.
        
        Args:
            name: The name of the submodule to remove.
            
        Raises:
            KeyError: If no submodule with the given name exists.
            RuntimeError: If the submodule cannot be removed due to dependencies or other constraints.
        """
        ...

# 类型检查帮助器，用于表示一个对象同时满足 Module 和 Project 协议
ProjectType = TypeVar('ProjectType', bound=Module)
