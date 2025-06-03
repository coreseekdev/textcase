"""Base protocol package.

This package contains base protocol interfaces for VFS and other core functionality.
"""

from __future__ import annotations

# Import all protocols from submodules
from .vfs import (
    VFS,
    FileHandle,
    FileStat,
    FileSeek,
    TempDir
)

# Re-export all symbols
__all__ = [
    'VFS',
    'FileHandle',
    'FileStat',
    'FileSeek',
    'TempDir'
]
