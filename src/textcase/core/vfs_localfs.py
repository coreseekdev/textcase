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
"""Local filesystem implementation of the VFS protocol."""

from __future__ import annotations

import os
import shutil
import tempfile
from pathlib import Path
from typing import Any, Iterator, Optional, Union, Tuple

from ..protocol import FileHandle, FileStat, VFS, TempDir


__all__ = ['get_default_local_vfs', 'LocalTempDir']

_default_local_vfs = None

def get_default_local_vfs() -> VFS:
    """Get the default local filesystem VFS instance.
    
    Returns:
        A shared LocalVFS instance.
    """
    global _default_local_vfs
    if _default_local_vfs is None:
        _default_local_vfs = LocalVFS()
    return _default_local_vfs

class LocalFileHandle(FileHandle):
    """Local filesystem file handle implementation."""
    
    def __init__(self, path: Union[str, Path], mode: str = 'r', **kwargs: Any):
        self._path = Path(path)
        self._mode = mode
        self._file = self._path.open(mode, **kwargs)
        self._closed = False
    
    def read(self, size: int = -1) -> bytes:
        if 'b' in self._mode:
            return self._file.read(size)
        return self._file.read(size).encode('utf-8')
    
    def write(self, data: Union[bytes, str]) -> int:
        if 'b' in self._mode:
            if isinstance(data, str):
                data = data.encode('utf-8')
            return self._file.write(data)
        else:
            if isinstance(data, bytes):
                data = data.decode('utf-8')
            return self._file.write(data)
    
    def seek(self, offset: int, whence: int = 0) -> int:
        return self._file.seek(offset, whence)
    
    def tell(self) -> int:
        return self._file.tell()
    
    def truncate(self, size: Optional[int] = None) -> int:
        return self._file.truncate(size)
    
    def flush(self) -> None:
        self._file.flush()
    
    def close(self) -> None:
        if not self._closed:
            self._file.close()
            self._closed = True
    
    def __enter__(self) -> FileHandle:
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
    
    @property
    def closed(self) -> bool:
        return self._closed
    
    def readable(self) -> bool:
        return self._file.readable()
    
    def writable(self) -> bool:
        return self._file.writable()
    
    def seekable(self) -> bool:
        return self._file.seekable()

class LocalTempDir(TempDir):
    """Local filesystem implementation of TempDir."""
    
    def __init__(self, temp_dir_path: str, overlay_target: Optional[str] = None):
        """Initialize a local temporary directory.
        
        Args:
            temp_dir_path: Path to the temporary directory
            overlay_target: Optional path to the directory this temp dir is overlaying
        """
        self._path = temp_dir_path
        self._overlay_target = overlay_target
        self._closed = False
    
    @property
    def path(self) -> str:
        """Get the path to the temporary directory."""
        return self._path
    
    @property
    def is_overlay(self) -> bool:
        """Return True if this temporary directory is an overlay on an existing directory."""
        return self._overlay_target is not None
    
    @property
    def overlay_target(self) -> Optional[str]:
        """Return the path of the directory this temporary directory is overlaying, if any."""
        return self._overlay_target
    
    def commit(self) -> None:
        """Commit changes to the underlying directory if this is an overlay.
        
        For non-overlay temporary directories, this is a no-op.
        """
        if not self.is_overlay or self._closed:
            return
            
        # Copy all files from temp directory to target directory
        target_path = Path(self._overlay_target)
        temp_path = Path(self._path)
        
        # Ensure target directory exists
        target_path.mkdir(parents=True, exist_ok=True)
        
        # Copy all files from temp directory to target directory
        for item in temp_path.glob('**/*'):
            # Get the relative path from the temp directory
            rel_path = item.relative_to(temp_path)
            target_item = target_path / rel_path
            
            if item.is_dir():
                target_item.mkdir(parents=True, exist_ok=True)
            else:
                # Ensure parent directories exist
                target_item.parent.mkdir(parents=True, exist_ok=True)
                # Copy the file
                shutil.copy2(item, target_item)
    
    def rollback(self) -> None:
        """Discard changes and revert to the original state if this is an overlay.
        
        For non-overlay temporary directories, this is a no-op.
        """
        # For local filesystem, rollback is just not committing changes
        # No additional action needed
        pass
    
    def close(self) -> None:
        """Close the temporary directory and clean up resources.
        
        This will delete the temporary directory if it has not been committed.
        """
        if not self._closed:
            # Remove the temporary directory
            if Path(self._path).exists():
                shutil.rmtree(self._path)
            self._closed = True


class LocalVFS(VFS):
    """Local filesystem implementation of VFS."""
    
    def exists(self, path: Union[str, Path]) -> bool:
        return Path(path).exists()
    
    def isfile(self, path: Union[str, Path]) -> bool:
        return Path(path).is_file()
    
    def isdir(self, path: Union[str, Path]) -> bool:
        return Path(path).is_dir()
    
    def open(self, path: Union[str, Path], mode: str = 'r', **kwargs: Any) -> FileHandle:
        return LocalFileHandle(path, mode, **kwargs)
    
    def stat(self, path: Union[str, Path]) -> FileStat:
        path = Path(path)
        stat = path.stat()
        return FileStat(
            name=path.name,
            size=stat.st_size,
            mtime=stat.st_mtime,
            is_dir=path.is_dir(),
            mode=stat.st_mode,
            ino=stat.st_ino,
            dev=stat.st_dev,
            nlink=stat.st_nlink,
            uid=stat.st_uid,
            gid=stat.st_gid,
        )
    
    def makedirs(self, path: Union[str, Path], exist_ok: bool = False) -> None:
        Path(path).mkdir(parents=True, exist_ok=exist_ok)
    
    def listdir(
        self,
        path: Union[str, Path],
        pattern: Optional[str] = None,
        recursive: bool = False,
        sort_by: Optional[str] = None,
        reverse: bool = False,
        **kwargs: Any
    ) -> Iterator[FileStat]:
        path = Path(path)
        
        if not path.exists():
            raise FileNotFoundError(f"No such directory: {path}")
        if not path.is_dir():
            raise NotADirectoryError(f"Not a directory: {path}")
        
        # Handle glob pattern
        if pattern:
            if recursive:
                paths = path.rglob(pattern)
            else:
                paths = path.glob(pattern)
        else:
            paths = path.iterdir()
        
        # Convert to FileStat objects
        entries = [self.stat(p) for p in paths]
        
        # Sort if requested
        if sort_by:
            if sort_by == 'name':
                entries.sort(key=lambda x: x.name, reverse=reverse)
            elif sort_by == 'size':
                entries.sort(key=lambda x: x.size, reverse=not reverse)
            elif sort_by == 'mtime':
                entries.sort(key=lambda x: x.mtime, reverse=not reverse)
        
        yield from entries
    
    def join(self, *paths: Union[str, Path]) -> str:
        return str(Path(*paths))
    
    def dirname(self, path: Union[str, Path]) -> str:
        return str(Path(path).parent)
    
    def basename(self, path: Union[str, Path]) -> str:
        return str(Path(path).name)
    
    def relpath(self, path: Union[str, Path], start: Optional[Union[str, Path]] = None) -> str:
        if start is None:
            return str(Path(path).resolve())
        return str(Path(path).resolve().relative_to(Path(start).resolve()))
    
    def remove(self, path: Union[str, Path]) -> None:
        Path(path).unlink()
    
    def rmdir(self, path: Union[str, Path]) -> None:
        Path(path).rmdir()
    
    def move(self, src: Union[str, Path], dst: Union[str, Path]) -> None:
        Path(src).replace(dst)
        
    def rmtree(self, path: Union[str, Path]) -> None:
        """Remove a directory tree recursively.
        
        Args:
            path: Path to the directory to remove
            
        Raises:
            OSError: If the directory cannot be removed
        """
        shutil.rmtree(path)
    
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
        # Create a temporary file
        fd, temp_path = tempfile.mkstemp(prefix=prefix, suffix=suffix, dir=dir)
        os.close(fd)  # Close the file descriptor
        
        # Open the file with our FileHandle implementation
        file_handle = self.open(temp_path, mode='w+b')
        
        return temp_path, file_handle
    
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
        # Create a temporary directory
        temp_dir = tempfile.mkdtemp(prefix=prefix, suffix=suffix, dir=base_dir)
        
        # Return a LocalTempDir instance
        return LocalTempDir(temp_dir)
    
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
        # Create a temporary directory
        temp_dir = tempfile.mkdtemp(prefix=prefix, suffix=suffix, dir=base_dir)
        target_dir_str = str(target_dir)
        
        # If target directory exists, optionally copy its contents to the temp dir
        # This is commented out because we're implementing a pure overlay approach
        # where changes are only written back on commit, not a full copy-on-write
        # if Path(target_dir).exists():
        #     shutil.copytree(target_dir, temp_dir, dirs_exist_ok=True)
        
        # Return a LocalTempDir instance with overlay information
        return LocalTempDir(temp_dir, overlay_target=target_dir_str)
