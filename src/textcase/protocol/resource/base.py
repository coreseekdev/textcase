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
"""Base resource protocol definitions for TextCase.

This module defines base protocols for resources, including items and modules.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Protocol, Set, TypeVar, runtime_checkable, Union

from ..base.vfs import VFS

__all__ = [
    'ItemBase',
    'ItemCollection',
    'ModuleBase',
    'ModuleConfigBase',
]


class ItemBase(Protocol):
    """Base protocol for all items in the system."""
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Get the name of the item."""
        ...


class ItemCollection(Protocol):
    """Protocol for collections of items."""
    
    @property
    @abstractmethod
    def items(self) -> List[ItemBase]:
        """Get all items in the collection."""
        ...


class ModuleConfigBase(Protocol):
    """Base protocol for module configuration."""
    
    @abstractmethod
    def get(self, key: str, default: Any = None) -> Any:
        """Get a configuration value.
        
        Args:
            key: The configuration key.
            default: Default value to return if key is not found.
            
        Returns:
            The configuration value, or default if not found.
        """
        ...


class ModuleBase(ItemCollection, Protocol):
    """Base protocol for all modules."""
    
    @property
    @abstractmethod
    def config(self) -> ModuleConfigBase:
        """Get the module's configuration."""
        ...
    
    @abstractmethod
    def save(self) -> None:
        """Save any changes to the module."""
        ...
