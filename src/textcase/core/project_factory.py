"""Project factory module.

This module provides factory functions for creating Project instances.
"""

from pathlib import Path
from typing import Optional

from ..protocol.module import Project
from ..protocol.vfs import VFS
from .project import _YamlProject
from .vfs import get_default_vfs

__all__ = ['create_project']


def create_project(path: Path, vfs: Optional[VFS] = None) -> Project:
    """Create a new project instance.
    
    This is the preferred way to create Project instances.
    
    Args:
        path: The path to the project root directory.
        vfs: Optional virtual filesystem to use. Defaults to the default VFS.
        
    Returns:
        A new Project instance.
    """
    return _YamlProject(path=path, vfs=vfs or get_default_vfs())
