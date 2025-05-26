"""Module protocol and related types."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Protocol, TypeVar, runtime_checkable
import yaml

from .vfs_protocol import VFS

__all__ = [
    'ModuleConfig',
    'Module',
    'ModuleOrder',
    'ModuleTags',
]

@dataclass
class ModuleConfig:
    """Module configuration."""
    path: Path
    settings: Dict[str, Any] = field(default_factory=dict)
    tags: Dict[str, str] = field(default_factory=dict)
    
    @classmethod
    def load(cls, path: Path, vfs: VFS) -> ModuleConfig:
        """Load configuration from a YAML file."""
        config_path = path / '.textcase' / 'config.yml'
        if not vfs.exists(config_path):
            return cls(path=path)
            
        with vfs.open(config_path, 'r') as f:
            data = yaml.safe_load(f) or {}
            
        return cls(
            path=path,
            settings=data.get('settings', {}),
            tags=data.get('tags', {})
        )
    
    def save(self, vfs: VFS) -> None:
        """Save configuration to a YAML file."""
        config_dir = self.path / '.textcase'
        if not vfs.exists(config_dir):
            vfs.makedirs(config_dir, exist_ok=True)
            
        config_path = config_dir / 'config.yml'
        data = {
            'settings': self.settings,
            'tags': self.tags
        }
        
        with vfs.open(config_path, 'w') as f:
            yaml.safe_dump(data, f, default_flow_style=False)

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
