"""Core functionality for TextCase."""

from pathlib import Path
from typing import Any, Dict, List, Optional, Type, TypeVar, Union

from ..protocol import (
    VFS,
    FileHandle,
    FileStat,
    Module,
    ModuleConfig,
    ModuleOrder,
    ModuleTags,
)

from .localfs import LocalVFS, LocalFileHandle
from .order import YamlOrder
from .tags import FileBasedTags
from .module import BaseModule, ProjectModule

__all__ = [
    # Core implementations
    'LocalVFS',
    'LocalFileHandle',
    'YamlOrder',
    'FileBasedTags',
    'BaseModule',
    'ProjectModule',
    
    # Re-exported from protocol for convenience
    'VFS',
    'FileHandle',
    'FileStat',
    'Module',
    'ModuleConfig',
    'ModuleOrder',
    'ModuleTags',
]
