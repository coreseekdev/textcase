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
from typing import Any, Dict, List, NamedTuple, Optional, Protocol, Set, TypeVar, runtime_checkable
import yaml

from .vfs import VFS

__all__ = [
    'ModuleConfig',
    'ProjectConfig',
    'Module',
    'Project',
    'ModuleOrder',
    'ModuleTagging',
    'CaseItem',
    'DocumentCaseItem',
    'ProjectTags',
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

class CaseItem(Protocol):
    """Protocol for a case item that can be tagged.
    
    A case item represents a document or test case that can be tagged
    for organization and retrieval.
    """
    
    @property
    @abstractmethod
    def prefix(self) -> str:
        """Get the prefix of the case item.
        
        The prefix is used to group related case items together.
        """
        ...
        
    @property
    @abstractmethod
    def id(self) -> str:
        """Get the unique identifier of the case item within its prefix.
        
        The ID must be unique within the same prefix and should be a valid filename.
        """
        ...
        
    @property
    @abstractmethod
    def key(self) -> str:
        """Get the unique key for this case item.
        
        The key is used to uniquely identify the item in the tagging system.
        It should be in the format 'prefix:id'.
        """
        ...


@runtime_checkable
class DocumentCaseItem(CaseItem, Protocol):
    """Protocol for a document case item.
    
    This is a placeholder protocol that extends CaseItem for document-specific
    functionality. Currently, it doesn't add any new methods or properties.
    """
    pass


class ModuleOrder(Protocol):
    """Protocol for module ordering functionality."""
    
    @abstractmethod
    def get_ordered_items(self) -> List[CaseItem]:
        """Get items in their defined order.
        
        Returns:
            A list of CaseItem objects in their defined order.
        """
        ...
    
    @abstractmethod
    def add_item(self, item: CaseItem) -> None:
        """Add an item to the ordering.
        
        Args:
            item: The CaseItem to add to the ordering.
        """
        ...
    
    @abstractmethod
    def remove_item(self, item: CaseItem) -> None:
        """Remove an item from the ordering.
        
        Args:
            item: The CaseItem to remove from the ordering.
        """
        ...
        
    @abstractmethod
    def get_next_item_id(self, prefix: str) -> str:
        """Get the next available item ID for the given prefix.
        
        The ID is a monotonically increasing sequence number based on existing files
        in the directory with the pattern 'prefixNNN.md'. It will find the highest
        existing sequence number and return the next one.
        
        Args:
            prefix: The prefix to use for finding existing files (e.g., 'REQ')
            
        Returns:
            The next available sequence number as a string, formatted according to
            the module's settings (e.g., '001' if digits=3)
        """
        ...
        
class ModuleTagging(Protocol):
    """Protocol for module-level tag management.
    
    This protocol defines the interface for managing tags on case items within a module.
    It provides methods to add, remove, and query tags for case items.
    """
    
    @abstractmethod
    def add_tag(self, item: 'CaseItem', tag: str) -> None:
        """Add a tag to a case item.
        
        Args:
            item: The case item to tag.
            tag: The tag to add.
            
        Raises:
            ValueError: If the tag is not in the available tags list.
        """
        ...
    
    @abstractmethod
    def remove_tag(self, item: 'CaseItem', tag: str) -> None:
        """Remove a tag from a case item.
        
        Args:
            item: The case item to untag.
            tag: The tag to remove.
        """
        ...
    
    @abstractmethod
    def get_item_tags(self, item: 'CaseItem') -> List[str]:
        """Get all tags for a specific case item.
        
        Args:
            item: The case item to get tags for.
            
        Returns:
            A list of tag names associated with the item.
        """
        ...
    
    @abstractmethod
    def get_tags(self) -> List[str]:
        """Get all available tags."""
        ...
        
    @abstractmethod
    def invalidate_cache(self) -> None:
        """Invalidate any cached tag data."""
        ...
    
    @abstractmethod
    def invalidate_cache(self) -> None:
        """Invalidate any cached tag data."""
        ...


class ProjectTags(Protocol):
    """Protocol for project-level tag management.
    
    This protocol defines the interface for managing tags at the project level.
    It provides access to the tag management functionality for the entire project.
    """
    
    @abstractmethod
    def get_tags(self, prefix: str) -> List[str]:
        """Get all available tags for the specified prefix.
        
        Tags from parent modules are included in the result.
        
        Args:
            prefix: The prefix to get tags for.
                   
        Returns:
            A list of tag names that can be used with the specified prefix.
        """
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
    def prefix(self) -> str:
        """Get the module's prefix.
        
        The prefix is used to identify the module within the project hierarchy.
        It should be unique among siblings.
        """
        ...
    
    @property
    @abstractmethod
    def tags(self) -> ModuleTagging:
        """Get the project's global tagging interface.
        
        The tags are managed at the project level and are available to all modules.
        """
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
        
    @abstractmethod
    def save(self) -> None:
        """Save any changes to the module."""
        ...
    
    @abstractmethod
    def get_document_item(self, id: str) -> DocumentCaseItem:
        """Get a DocumentCaseItem for the given ID using this module's prefix.
        
        The returned DocumentCaseItem will use this module's prefix and the provided ID.
        This does not require the item to exist on disk.
        
        Args:
            id: The ID of the document item.
                
        Returns:
            A DocumentCaseItem with the module's prefix and the given ID.
        """
        ...
    
    @abstractmethod
    def new_item(self, default_content: str = '', *, editor_mode: bool = False) -> Optional[DocumentCaseItem]:
        """Create a new document item in this module.
        
        Args:
            default_content: Optional default content for the new document.
            editor_mode: If True, opens an editor for the user to edit the content.
                       If the user exits without saving, returns None.
                       
        Returns:
            The newly created DocumentCaseItem, or None if creation was cancelled.
        """
        ...


class Project(Module, Protocol):
    """Protocol for a project, which is the root module in the module hierarchy.
    
    A Project is a Module with additional capabilities for managing submodules and tags.
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
    def add_module(self, parent_prefix: str, module: Module) -> None:
        """Add an existing module to the project.
        
        Args:
            parent_prefix: The prefix of the parent module. Must not be empty.
            module: The module instance to add. Must have a non-empty prefix.
            
        Raises:
            ValueError: If parent_prefix is empty or module has no prefix.
            ValueError: If a module with the given prefix already exists.
            ValueError: If the module's path is not within the project directory.
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
