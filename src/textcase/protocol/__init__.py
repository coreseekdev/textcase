"""Protocol definitions for TextCase."""

from pathlib import Path
from typing import Any, Dict, List, Optional, Type, TypeVar, Union

# VFS protocol
from .vfs_protocol import VFS, FileHandle, FileStat, FileSeek

# Module protocol
from .module import (
    Module,
    ModuleConfig,
    ModuleOrder,
    ModuleTags,
)

# For backward compatibility
from .vfs_protocol import VFS as VFSProtocol

__all__ = [
    # VFS related
    'VFS',
    'VFSProtocol',
    'FileHandle',
    'FileStat',
    'FileSeek',
    
    # Module related
    'Module',
    'ModuleConfig',
    'ModuleOrder',
    'ModuleTags',
]
