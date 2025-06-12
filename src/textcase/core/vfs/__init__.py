"""VFS (Virtual File System) implementations.

This package provides implementations of the ServiceVFSProtocol interface
for different types of file systems.
"""

from .local_vfs import LocalVFS
from .git_vfs import GitVFS
from .repo_vfs import RepoVFS

__all__ = ['LocalVFS', 'GitVFS', 'RepoVFS']