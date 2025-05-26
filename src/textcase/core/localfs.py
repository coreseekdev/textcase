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
from pathlib import Path
from typing import Any, Iterator, Optional, Union

from ..protocol import FileHandle, FileStat, VFS

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
    
    def __enter__(self) -> LocalFileHandle:
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
        import shutil
        shutil.rmtree(path)
