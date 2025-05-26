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
from typing import Dict, List, Optional, Protocol, TypeVar, runtime_checkable
import yaml

from .vfs import VFS

__all__ = [
    'ModuleConfig',
    'Module',
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
    """Protocol for a module in the project."""
    
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
    def get_submodules(self) -> List[Module]:
        """Get all direct submodules of this module."""
        ...
        
    @abstractmethod
    def find_submodule(self, path: Path) -> Optional[Module]:
        """Find a submodule by its path."""
        ...
        
    @abstractmethod
    def create_submodule(self, name: str) -> Module:
        """Create a new submodule."""
        ...
        
    @abstractmethod
    def save(self) -> None:
        """Save any changes to the module."""
        ...
