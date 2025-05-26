"""
Virtual File System (VFS) utilities.

This module provides a unified interface for getting the default VFS instance.
"""

__all__ = ['get_default_vfs']

from typing import TYPE_CHECKING

# Import locally to avoid circular imports
if TYPE_CHECKING:
    from ..protocol.vfs import VFS

# Re-export get_default_local_vfs as get_default_vfs
from .vfs_localfs import get_default_local_vfs as get_default_vfs

# For type checking only
if TYPE_CHECKING:
    def get_default_vfs() -> 'VFS': ...  # type: ignore
