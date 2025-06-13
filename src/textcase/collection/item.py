"""Resource Item Implementation

This module provides concrete implementation of ResourceItem protocol,
following the design patterns from the original module_item.py.
"""

from pathlib import PurePosixPath
from typing import Any, Dict, Generic, Optional, Set, TypeVar, Union

from ..client.vfs_client import VFSClient, VFSClientException
from ..proto.resource_collection_protocol import ResourceItem
from .config import CollectionConfig

T = TypeVar('T')


class ResourceItemImpl(Generic[T], ResourceItem[T]):
    """File-based implementation of ResourceItem protocol.
    
    This implementation stores items as files within a collection directory,
    following the naming conventions defined in the collection configuration.
    """
    
    def __init__(
        self,
        name: str,
        collection_path: Union[PurePosixPath, str],
        config: CollectionConfig,
        vfs: VFSClient,
        data: Optional[T] = None
    ):
        """Initialize a resource item.
        
        Args:
            name: The unique name of the item within the collection
            collection_path: Path to the collection directory
            config: Collection configuration
            vfs: VFS client for file operations
            data: Optional data payload for the item
        """
        self._name = name
        self._collection_path = PurePosixPath(collection_path) if isinstance(collection_path, str) else collection_path
        self._config = config
        self._vfs = vfs
        self._data = data
        self._tags: Set[str] = set()
        self._metadata: Dict[str, Any] = {}
        
        # Load existing tags and metadata if item exists
        self._load_item_info()
    
    @property
    def name(self) -> str:
        """Get the unique name of this item."""
        return self._name
    
    @property
    def data(self) -> Optional[T]:
        """Get the data payload of this item."""
        return self._data
    
    @data.setter
    def data(self, value: Optional[T]) -> None:
        """Set the data payload of this item."""
        self._data = value
    
    @property
    def tags(self) -> Set[str]:
        """Get all tags associated with this item."""
        return self._tags.copy()
    
    def add_tag(self, tag: str) -> None:
        """Add a tag to this item.
        
        Args:
            tag: The tag to add
        """
        if tag not in self._tags:
            self._tags.add(tag)
            self._update_tag_file(tag, add=True)
    
    def remove_tag(self, tag: str) -> None:
        """Remove a tag from this item.
        
        Args:
            tag: The tag to remove
        """
        if tag in self._tags:
            self._tags.remove(tag)
            self._update_tag_file(tag, add=False)
    
    def has_tag(self, tag: str) -> bool:
        """Check if this item has a specific tag.
        
        Args:
            tag: The tag to check
            
        Returns:
            True if the item has the tag, False otherwise
        """
        return tag in self._tags
    
    def get_metadata(self, key: str, default: Any = None) -> Any:
        """Get metadata value by key.
        
        Args:
            key: The metadata key
            default: Default value if key doesn't exist
            
        Returns:
            The metadata value or default
        """
        return self._metadata.get(key, default)
    
    def set_metadata(self, key: str, value: Any) -> None:
        """Set metadata value by key.
        
        Args:
            key: The metadata key
            value: The metadata value
        """
        self._metadata[key] = value
    
    def get_file_path(self) -> PurePosixPath:
        """Get the file path for this item.
        
        Returns:
            The full path to the item's file
        """
        filename = self._config.get_item_filename(self._name)
        return self._collection_path / filename
    
    def exists(self) -> bool:
        """Check if the item file exists.
        
        Returns:
            True if the item file exists, False otherwise
        """
        try:
            info = self._vfs.info(self.get_file_path())
            return info is not None
        except VFSClientException:
            return False
    
    def create(self, content: str = "") -> None:
        """Create the item file.
        
        Args:
            content: Initial content for the file
            
        Raises:
            VFSClientException: If the file cannot be created
        """
        file_path = self.get_file_path()
        try:
            self._vfs.put(file_path, content.encode('utf-8'), create_if_missing=True)
        except Exception as e:
            raise VFSClientException(
                'ItemCreateError',
                f'Failed to create item file {file_path}: {e}'
            )
    
    def read_content(self) -> str:
        """Read the content of the item file.
        
        Returns:
            The file content as string
            
        Raises:
            VFSClientException: If the file cannot be read
        """
        file_path = self.get_file_path()
        try:
            return self._vfs.get_text(file_path, encoding='utf-8')
        except Exception as e:
            raise VFSClientException(
                'ItemReadError',
                f'Failed to read item file {file_path}: {e}'
            )
    
    def write_content(self, content: str) -> None:
        """Write content to the item file.
        
        Args:
            content: The content to write
            
        Raises:
            VFSClientException: If the file cannot be written
        """
        file_path = self.get_file_path()
        try:
            self._vfs.put(file_path, content.encode('utf-8'), create_if_missing=True)
        except Exception as e:
            raise VFSClientException(
                'ItemWriteError',
                f'Failed to write item file {file_path}: {e}'
            )
    
    def delete(self) -> None:
        """Delete the item file and remove from all tag files.
        
        Raises:
            VFSClientException: If the file cannot be deleted
        """
        # Remove from all tag files first
        for tag in self._tags.copy():
            self.remove_tag(tag)
        
        # Delete the item file
        file_path = self.get_file_path()
        try:
            # Check if file exists before attempting to delete
            if self.exists():
                # Note: VFS client doesn't seem to have a delete method in the interface
                # We'll need to handle this through the VFS implementation
                # For now, we'll assume there's a way to delete files
                pass  # TODO: Implement file deletion when VFS supports it
        except Exception as e:
            raise VFSClientException(
                'ItemDeleteError',
                f'Failed to delete item file {file_path}: {e}'
            )
    
    def _load_item_info(self) -> None:
        """Load item tags and metadata from tag files."""
        # Load tags by checking which tag files contain this item
        for tag_name in self._config.tags.keys():
            tag_file_path = self._collection_path / f"{tag_name}.txt"
            try:
                content = self._vfs.get_text(tag_file_path, encoding='utf-8')
                if content:
                    lines = [line.strip() for line in content.splitlines()]
                    if self._name in lines:
                        self._tags.add(tag_name)
            except VFSClientException:
                # Tag file doesn't exist, skip
                continue
    
    def _update_tag_file(self, tag: str, add: bool) -> None:
        """Update a tag file to add or remove this item.
        
        Args:
            tag: The tag name
            add: True to add the item, False to remove it
        """
        tag_file_path = self._collection_path / f"{tag}.txt"
        
        try:
            # Read existing content
            try:
                content = self._vfs.get_text(tag_file_path, encoding='utf-8')
                lines = [line.strip() for line in content.splitlines() if line.strip()]
            except VFSClientException:
                # File doesn't exist
                lines = []
            
            # Update the lines
            if add:
                if self._name not in lines:
                    lines.append(self._name)
                    lines.sort()  # Keep sorted for consistency
            else:
                if self._name in lines:
                    lines.remove(self._name)
            
            # Write back to file
            new_content = '\n'.join(lines) + ('\n' if lines else '')
            self._vfs.put(tag_file_path, new_content.encode('utf-8'), create_if_missing=True)
            
        except Exception as e:
            raise VFSClientException(
                'TagUpdateError',
                f'Failed to update tag file {tag_file_path}: {e}'
            )