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
"""Document module and item protocols.

This module defines protocols for document resources and collections.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, List, Optional, Protocol, Set, TypeVar, runtime_checkable, Union

from .base import ItemBase, ItemCollection, ModuleBase, ModuleConfigBase
from ..base.vfs import VFS

__all__ = [
    'DocumentTag',
    'DocumentItem',
    'DocumentModuleConfig',
    'DocumentModuleBase',
    'DocumentModule',
    'Project',
    'ProjectConfig',
    'ProjectOutline',
]


class DocumentTag(ItemBase, Protocol):
    """Protocol for document tags."""
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Get the tag name."""
        ...
    
    @property
    @abstractmethod
    def description(self) -> str:
        """Get the tag description."""
        ...


class DocumentItem(ItemBase, Protocol):
    """Protocol for document items."""
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Get the item name (identifier)."""
        ...
    
    @property
    @abstractmethod
    def module(self) -> DocumentModuleBase:
        """Get the module this item belongs to."""
        ...
    
    @abstractmethod
    def make_link(self, target: ItemBase, label: Optional[str] = None, region: Optional[str] = None) -> bool:
        """Create a link from this document to the target.
        
        Args:
            target: The target item to link to
            label: Optional label for the link
            region: Optional region where to create the link (e.g., "frontmatter", "content")
            
        Returns:
            True if the link was successfully created, False otherwise
        """
        ...
    
    @abstractmethod
    def get_links(self) -> Dict[str, List[str]]:
        """Get all links from this document.
        
        Returns:
            A dictionary mapping target keys to lists of labels
        """
        ...


class DocumentModuleConfig(ModuleConfigBase, Protocol):
    """Protocol for document module configuration."""
    
    @property
    @abstractmethod
    def prefix(self) -> str:
        """Get the module prefix."""
        ...
    
    @property
    @abstractmethod
    def path(self) -> Path:
        """Get the module path."""
        ...
    
    @property
    @abstractmethod
    def settings(self) -> Dict[str, Any]:
        """Get module settings."""
        ...
    
    @property
    @abstractmethod
    def tags(self) -> Dict[str, str]:
        """Get module tags."""
        ...
    
    @classmethod
    @abstractmethod
    def load(cls, path: Path, vfs: VFS) -> DocumentModuleConfig:
        """Load configuration from storage.
        
        Args:
            path: The path to the module directory.
            vfs: The virtual filesystem to use for loading.
            
        Returns:
            A new DocumentModuleConfig instance loaded from storage.
        """
        ...
    
    @abstractmethod
    def save(self, vfs: VFS) -> None:
        """Save configuration to storage.
        
        Args:
            vfs: The virtual filesystem to use for saving.
        """
        ...
    
    @abstractmethod
    def update_settings(self, settings: Dict[str, Any]) -> None:
        """Update module settings.
        
        Args:
            settings: Dictionary of settings to update.
        """
        ...
    
    @abstractmethod
    def update_tags(self, tags: Dict[str, str]) -> None:
        """Update module tags.
        
        Args:
            tags: Dictionary of tags to update.
        """
        ...


class DocumentModuleBase(ModuleBase, Protocol):
    """Base protocol for document modules."""
    
    @property
    @abstractmethod
    def path(self) -> Path:
        """Get the module's filesystem path."""
        ...
    
    @property
    @abstractmethod
    def prefix(self) -> str:
        """Get the module's prefix."""
        ...
    
    @property
    @abstractmethod
    def config(self) -> DocumentModuleConfig:
        """Get the module's configuration."""
        ...
    
    @property
    @abstractmethod
    def items(self) -> List[DocumentItem]:
        """Get all document items in the module."""
        ...
    
    @property
    @abstractmethod
    def modules(self) -> List[DocumentModuleBase]:
        """Get all submodules of this module."""
        ...
    
    @property
    @abstractmethod
    def tags(self) -> List[DocumentTag]:
        """Get all tags defined in this module."""
        ...
    
    @abstractmethod
    def next(self) -> str:
        """Get the next available document ID.
        
        Returns:
            The next available document ID that doesn't conflict with existing items.
        """
        ...
    
    @abstractmethod
    def add_tag(self, item: DocumentItem, tag: str) -> None:
        """Add a tag to a document item.
        
        Args:
            item: The document item to tag.
            tag: The tag to add.
            
        Raises:
            ValueError: If the tag is not in the available tags list.
        """
        ...
    
    @abstractmethod
    def remove_tag(self, item: DocumentItem, tag: str) -> None:
        """Remove a tag from a document item.
        
        Args:
            item: The document item to untag.
            tag: The tag to remove.
        """
        ...
    
    @abstractmethod
    def save(self) -> None:
        """Save any changes to the module."""
        ...
    
    @abstractmethod
    def get_document_item(self, id: str) -> DocumentItem:
        """Get a DocumentItem for the given ID using this module's prefix.
        
        Args:
            id: The ID of the document item.
                
        Returns:
            A DocumentItem with the module's prefix and the given ID.
        """
        ...
    
    @abstractmethod
    def new_item(self, default_content: str = '', *, editor_mode: bool = False) -> Optional[DocumentItem]:
        """Create a new document item in this module.
        
        Args:
            default_content: Optional default content for the new document.
            editor_mode: If True, opens an editor for the user to edit the content.
                       If the user exits without saving, returns None.
                       
        Returns:
            The newly created DocumentItem, or None if creation was cancelled.
        """
        ...


class DocumentModule(DocumentModuleBase, Protocol):
    """Protocol for a document module that is a child of another module."""
    
    @property
    @abstractmethod
    def parent(self) -> DocumentModuleBase:
        """Get the parent module."""
        ...


class ProjectConfig(DocumentModuleConfig, Protocol):
    """Protocol for project configuration."""
    
    @property
    @abstractmethod
    def root_source_module(self) -> Optional[str]:
        """Get the root source module prefix."""
        ...
    
    @property
    @abstractmethod
    def modules(self) -> Dict[str, Dict[str, Any]]:
        """Get all module configurations."""
        ...
    
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
            ValueError: If the submodule has children.
        """
        ...


class ProjectOutline(Protocol):
    """Protocol for project outline management."""
    
    @abstractmethod
    def get_ordered_items(self) -> List[DocumentItem]:
        """Get items in their defined order.
        
        Returns:
            A list of DocumentItem objects in their defined order.
        """
        ...
    
    @abstractmethod
    def add_item(self, item: DocumentItem) -> None:
        """Add an item to the outline.
        
        Args:
            item: The DocumentItem to add to the outline.
        """
        ...
    
    @abstractmethod
    def remove_item(self, item: DocumentItem) -> None:
        """Remove an item from the outline.
        
        Args:
            item: The DocumentItem to remove from the outline.
        """
        ...


class Project(DocumentModuleBase, Protocol):
    """Protocol for a project, which is the root module in the module hierarchy."""
    
    @property
    @abstractmethod
    def config(self) -> ProjectConfig:
        """Get the project's configuration."""
        ...
    
    @property
    @abstractmethod
    def sources(self) -> List[Any]:  # Will be List[SourceModule] once defined
        """Get all root source modules."""
        ...
    
    @property
    @abstractmethod
    def outline(self) -> ProjectOutline:
        """Get the project's outline interface."""
        ...
    
    @abstractmethod
    def get_submodules(self) -> List[DocumentModule]:
        """Get all direct submodules of this project.
        
        Returns:
            A list of DocumentModule objects representing the direct submodules.
        """
        ...
    
    @abstractmethod
    def find_submodule(self, path: Path) -> Optional[DocumentModule]:
        """Find a submodule by its path.
        
        Args:
            path: The path of the submodule to find, relative to the project root.
            
        Returns:
            The found DocumentModule, or None if not found.
        """
        ...
    
    @abstractmethod
    def add_module(self, parent_prefix: str, module: DocumentModule) -> None:
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
    def __getitem__(self, name: str) -> DocumentModule:
        """Get a submodule by name.
        
        Args:
            name: The name of the submodule to get.
            
        Returns:
            The DocumentModule with the given name.
            
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
            RuntimeError: If the submodule cannot be removed due to dependencies.
        """
        ...
