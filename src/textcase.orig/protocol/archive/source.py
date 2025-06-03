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
"""Source code module and item protocols.

This module is deprecated and will be removed in a future version.
Please use textcase.protocol.resource.file_item instead.
"""

from __future__ import annotations

# Re-export from new location
from .resource.file_item import (
    FileItem,
    FileModule,
    SourceCodeItem,
    SourceModule
)

__all__ = [
    'FileItem',
    'FileModule',
    'SourceCodeItem',
    'SourceModule',
]


class FileItem(ItemBase, Protocol):
    """Protocol for file items.
    
    Represents a complex text container like PDF, Word, or non-project Markdown.
    """
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Get the name of the file item."""
        ...
    
    @property
    @abstractmethod
    def path(self) -> Path:
        """Get the path to the file."""
        ...
    
    @property
    @abstractmethod
    def content_type(self) -> str:
        """Get the content type of the file."""
        ...
    
    @abstractmethod
    def read(self) -> bytes:
        """Read the file content as bytes.
        
        Returns:
            The file content as bytes.
        """
        ...
    
    @abstractmethod
    def write(self, content: bytes) -> None:
        """Write content to the file.
        
        Args:
            content: The content to write as bytes.
        """
        ...


class FileModule(ModuleBase, Protocol):
    """Protocol for file modules.
    
    Represents a directory for storing common document files.
    """
    
    @property
    @abstractmethod
    def path(self) -> Path:
        """Get the module's filesystem path."""
        ...
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Get the module's name."""
        ...
    
    @property
    @abstractmethod
    def config(self) -> ModuleConfigBase:
        """Get the module's configuration."""
        ...
    
    @property
    @abstractmethod
    def items(self) -> List[FileItem]:
        """Get all file items in the module."""
        ...
    
    @abstractmethod
    def save(self) -> None:
        """Save any changes to the module."""
        ...
    
    @abstractmethod
    def get_file_item(self, path: Union[str, Path]) -> Optional[FileItem]:
        """Get a file item by its path.
        
        Args:
            path: The path to the file, relative to the module root.
            
        Returns:
            The FileItem if found, None otherwise.
        """
        ...
    
    @abstractmethod
    def add_file(self, path: Union[str, Path], content: Optional[bytes] = None) -> FileItem:
        """Add a new file to the module.
        
        Args:
            path: The path to the file, relative to the module root.
            content: Optional initial content for the file.
            
        Returns:
            The newly created FileItem.
            
        Raises:
            FileExistsError: If the file already exists.
        """
        ...
    
    @abstractmethod
    def remove_file(self, path: Union[str, Path]) -> bool:
        """Remove a file from the module.
        
        Args:
            path: The path to the file, relative to the module root.
            
        Returns:
            True if the file was removed, False if it didn't exist.
        """
        ...


class SourceCodeItem(FileItem, Protocol):
    """Protocol for source code items.
    
    Represents a source code file.
    """
    
    @property
    @abstractmethod
    def language(self) -> str:
        """Get the programming language of the source code."""
        ...
    
    @abstractmethod
    def get_element(self, element_path: str) -> Optional[Dict[str, Any]]:
        """Get a program element (function, class, etc.) by its path.
        
        Args:
            element_path: The path to the element within the file.
            
        Returns:
            Information about the element if found, None otherwise.
        """
        ...
    
    @abstractmethod
    def get_line_range(self, start: int, end: Optional[int] = None) -> str:
        """Get a range of lines from the source code.
        
        Args:
            start: The starting line number (0-indexed).
            end: The ending line number (inclusive). If None, only the start line is returned.
            
        Returns:
            The requested lines as a string.
            
        Raises:
            IndexError: If the line range is out of bounds.
        """
        ...


class SourceModule(FileModule, Protocol):
    """Protocol for source code modules.
    
    Represents a directory for storing project-related source code.
    """
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Get the name of the source module."""
        ...
    
    @property
    @abstractmethod
    def path(self) -> Path:
        """Get the path to the source module."""
        ...
    
    @property
    @abstractmethod
    def parent(self) -> Optional[ModuleBase]:
        """Get the parent module, if any."""
        ...
    
    @property
    @abstractmethod
    def items(self) -> List[SourceCodeItem]:
        """Get all source code items in the module."""
        ...
    
    @abstractmethod
    def get_source_item(self, path: Union[str, Path]) -> Optional[SourceCodeItem]:
        """Get a source code item by its path.
        
        Args:
            path: The path to the source file, relative to the module root.
            
        Returns:
            The SourceCodeItem if found, None otherwise.
        """
        ...
    
    @abstractmethod
    def find_by_element(self, element_path: str) -> Optional[SourceCodeItem]:
        """Find a source code item by a program element path.
        
        Args:
            element_path: The path to the program element.
            
        Returns:
            The SourceCodeItem containing the element if found, None otherwise.
        """
        ...
