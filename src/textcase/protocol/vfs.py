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
"""Virtual File System (VFS) protocol definitions.

This module defines the VFS protocol and related types that all VFS implementations
must adhere to.
"""

from __future__ import annotations

from abc import abstractmethod
from enum import Enum
from pathlib import Path
from typing import Any, Iterator, Optional, Protocol, runtime_checkable, TypeVar, Union
from types import TracebackType

__all__ = [
    'FileSeek',
    'FileHandle',
    'VFS',
    'FileStat',
    'TempDir',
]

T = TypeVar('T', bound='FileHandle')
D = TypeVar('D', bound='TempDir')

class FileSeek(Enum):
    """File seek modes."""
    START = 0
    CURRENT = 1
    END = 2

@runtime_checkable
class FileHandle(Protocol):
    """Abstract file handle interface for VFS operations."""
    
    @abstractmethod
    def read(self, size: int = -1) -> bytes:
        """Read up to size bytes from the file."""
        ...
    
    @abstractmethod
    def write(self, data: bytes) -> int:
        """Write data to the file."""
        ...
    
    @abstractmethod
    def seek(self, offset: int, whence: int = 0) -> int:
        """Change the file position."""
        ...
    
    @abstractmethod
    def tell(self) -> int:
        """Return the current file position."""
        ...
    
    @abstractmethod
    def truncate(self, size: Optional[int] = None) -> int:
        """Truncate the file to at most size bytes."""
        ...
    
    @abstractmethod
    def flush(self) -> None:
        """Flush write buffers if applicable."""
        ...
    
    @abstractmethod
    def close(self) -> None:
        """Close the file."""
        ...
    
    def __enter__(self: T) -> T:
        """Context manager entry."""
        ...
    
    def __exit__(
        self,
        exc_type: Optional[type[BaseException]],
        exc_val: Optional[BaseException],
        exc_tb: Optional[TracebackType],
    ) -> Optional[bool]:
        """Context manager exit."""
        ...
    
    @property
    @abstractmethod
    def closed(self) -> bool:
        """Return True if the file is closed."""
        ...
    
    @abstractmethod
    def readable(self) -> bool:
        """Return whether the file was opened for reading."""
        ...
    
    @abstractmethod
    def writable(self) -> bool:
        """Return whether the file was opened for writing."""
        ...
    
    @abstractmethod
    def seekable(self) -> bool:
        """Return whether random access is supported."""
        ...

class FileStat:
    """File/directory metadata."""
    
    def __init__(
        self,
        name: str,
        size: int,
        mtime: float,
        is_dir: bool = False,
        **kwargs: Any
    ) -> None:
        self.name = name
        self.size = size
        self.mtime = mtime
        self.is_dir = is_dir
        self.extra = kwargs
    
    def __repr__(self) -> str:
        return (
            f"<FileStat name={self.name!r} size={self.size} "
            f"mtime={self.mtime} is_dir={self.is_dir}>"
        )

@runtime_checkable
class TempDir(Protocol):
    """Temporary directory protocol.
    
    This protocol defines the interface that all temporary directory implementations must provide.
    A temporary directory can optionally be an overlay on top of an existing directory.
    """
    
    @property
    @abstractmethod
    def path(self) -> str:
        """Get the path to the temporary directory."""
        ...
    
    @property
    @abstractmethod
    def is_overlay(self) -> bool:
        """Return True if this temporary directory is an overlay on an existing directory."""
        ...
    
    @property
    @abstractmethod
    def overlay_target(self) -> Optional[str]:
        """Return the path of the directory this temporary directory is overlaying, if any."""
        ...
    
    @abstractmethod
    def commit(self) -> None:
        """Commit changes to the underlying directory if this is an overlay.
        
        For non-overlay temporary directories, this is a no-op.
        """
        ...
    
    @abstractmethod
    def rollback(self) -> None:
        """Discard changes and revert to the original state if this is an overlay.
        
        For non-overlay temporary directories, this is a no-op.
        """
        ...
    
    @abstractmethod
    def close(self) -> None:
        """Close the temporary directory and clean up resources.
        
        This will delete the temporary directory if it has not been committed.
        """
        ...
    
    def __enter__(self: D) -> D:
        """Context manager entry."""
        return self
    
    def __exit__(
        self,
        exc_type: Optional[type[BaseException]],
        exc_val: Optional[BaseException],
        exc_tb: Optional[TracebackType],
    ) -> Optional[bool]:
        """Context manager exit.
        
        Automatically closes the temporary directory without committing.
        """
        self.close()
        return None


@runtime_checkable
class VFS(Protocol):
    """Virtual File System protocol.
    
    This protocol defines the interface that all VFS implementations must provide.
    """
    
    @abstractmethod
    def exists(self, path: Union[str, Path]) -> bool:
        """Check if a path exists."""
        ...
    
    @abstractmethod
    def isfile(self, path: Union[str, Path]) -> bool:
        """Check if path is a file."""
        ...
    
    @abstractmethod
    def isdir(self, path: Union[str, Path]) -> bool:
        """Check if path is a directory."""
        ...
    
    @abstractmethod
    def open(self, path: Union[str, Path], mode: str = 'r', **kwargs: Any) -> FileHandle:
        """Open a file and return a file handle."""
        ...
    
    @abstractmethod
    def stat(self, path: Union[str, Path]) -> FileStat:
        """Get file/directory status."""
        ...
    
    @abstractmethod
    def makedirs(self, path: Union[str, Path], exist_ok: bool = False) -> None:
        """Create a directory and any necessary parent directories."""
        ...
    
    @abstractmethod
    def listdir(
        self,
        path: Union[str, Path],
        pattern: Optional[str] = None,
        recursive: bool = False,
        sort_by: Optional[str] = None,
        reverse: bool = False,
        **kwargs: Any
    ) -> Iterator[FileStat]:
        """List directory contents with optional filtering and sorting."""
        ...
    
    def listdir_names(
        self,
        path: Union[str, Path],
        **kwargs: Any
    ) -> Iterator[str]:
        """List directory contents as names only."""
        for entry in self.listdir(path, **kwargs):
            yield entry.name
    
    @abstractmethod
    def join(self, *paths: Union[str, Path]) -> str:
        """Join path components."""
        ...
    
    @abstractmethod
    def dirname(self, path: Union[str, Path]) -> str:
        """Get the directory name of a path."""
        ...
    
    @abstractmethod
    def basename(self, path: Union[str, Path]) -> str:
        """Get the base name of a path."""
        ...
    
    @abstractmethod
    def relpath(self, path: Union[str, Path], start: Optional[Union[str, Path]] = None) -> str:
        """Get a relative filepath to path from the start directory."""
        ...
    
    @abstractmethod
    def remove(self, path: Union[str, Path]) -> None:
        """Remove a file."""
        ...
    
    @abstractmethod
    def rmdir(self, path: Union[str, Path]) -> None:
        """Remove a directory."""
        ...
    
    @abstractmethod
    def move(self, src: Union[str, Path], dst: Union[str, Path]) -> None:
        """Move a file or directory."""
        ...
    
    @abstractmethod
    def create_temp_file(self, prefix: Optional[str] = None, suffix: Optional[str] = None, dir: Optional[Union[str, Path]] = None) -> tuple[str, FileHandle]:
        """Create a temporary file and return its path and a file handle.
        
        Args:
            prefix: Optional prefix for the temporary file name
            suffix: Optional suffix for the temporary file name (e.g., '.txt')
            dir: Optional directory where the temp file should be created
                 If None, system default temporary directory is used
                 
        Returns:
            A tuple containing the path to the temporary file and an open file handle
        """
        ...
    
    @abstractmethod
    def create_temp_dir(self, prefix: Optional[str] = None, suffix: Optional[str] = None, base_dir: Optional[Union[str, Path]] = None) -> TempDir:
        """Create a temporary directory.
        
        Args:
            prefix: Optional prefix for the temporary directory name
            suffix: Optional suffix for the temporary directory name
            base_dir: Optional parent directory where the temp directory should be created
                     If None, system default temporary directory is used
                     
        Returns:
            A TempDir object representing the temporary directory
        """
        ...
    
    @abstractmethod
    def create_overlay_temp_dir(self, target_dir: Union[str, Path], prefix: Optional[str] = None, suffix: Optional[str] = None, base_dir: Optional[Union[str, Path]] = None) -> TempDir:
        """Create a temporary directory that acts as an overlay on top of an existing directory.
        
        Changes made in the overlay directory can be committed to the target directory
        or discarded using the TempDir interface.
        
        Args:
            target_dir: The directory to overlay
            prefix: Optional prefix for the temporary directory name
            suffix: Optional suffix for the temporary directory name
            base_dir: Optional parent directory where the temp directory should be created
                     If None, system default temporary directory is used
                     
        Returns:
            A TempDir object representing the overlay temporary directory
        """
        ...
