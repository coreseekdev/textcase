"""Resource Item Implementation

This module provides concrete implementation of ResourceItem protocol,
following the design patterns from the original module_item.py.
"""

from pathlib import PurePosixPath
from typing import Any, Dict, Generic, Optional, Set, TypeVar, Union

from ..client.vfs_client import VFSClient, VFSClientException
from ..proto.resource_collection_protocol import ResourceItem, ResourceCollection
from .config import CollectionConfig
from .collection_tag import TagManager

T = TypeVar('T')


class ResourceItemImpl(Generic[T], ResourceItem[T]):
    """File-based implementation of ResourceItem protocol.
    
    This implementation stores items as files within a collection directory,
    following the naming conventions defined in the collection configuration.
    """
    
    # File extension for tag files
    TAG_FILE_EXTENSION: str = '.list'
    
    def __init__(
        self,
        name: str,
        collection: 'ResourceCollection[T]',
        data: Optional[T] = None,
        vfs: Optional[VFSClient] = None
    ):
        """Initialize a resource item.
        
        Args:
            name: The unique name of the item within the collection
            collection: The parent collection this item belongs to
            data: Optional data payload for the item
            vfs: Optional VFSClient for direct file operations
        """
        self._name = name
        self._collection = collection
        self._data = data
        self._tags: Set[str] = set()
        self._metadata: Dict[str, Any] = {}
        self._vfs = vfs or getattr(collection, '_vfs', None)
        self._collection_path = collection.path
        self._config = collection.config
        
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
    
    def assign_tag(self, tag: str) -> None:
        """Assign a tag to this item.
        
        Args:
            tag: Tag name to assign
        """
        self.add_tag(tag)
    
    def remove_tag(self, tag: str) -> None:
        """Remove a tag from this item.
        
        Args:
            tag: The tag to remove
        """
        if tag in self._tags:
            self._tags.remove(tag)
            self._update_tag_file(tag, add=False)
    
    def unassign_tag(self, tag: str) -> None:
        """Remove a tag from this item.
        
        Args:
            tag: Tag name to remove
        """
        self.remove_tag(tag)
    
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
        # Get the collection path and config from the parent collection
        collection_path = self._collection.path
        config = self._collection.config
        filename = config.get_item_filename(self._name)
        return collection_path / filename
    
    def exists(self) -> bool:
        """Check if the item file exists.
        
        Returns:
            True if the item file exists, False otherwise
        """
        try:
            file_path = self.get_file_path()
            info = self._vfs.info(file_path)
            return info is not None
        except FileNotFoundError:
            return False
    
    def create(self, content: Optional[T] = None) -> None:
        """Create the item file.
        
        Args:
            content: Initial content for the file
            
        Raises:
            VFSClientException: If the file cannot be created
        """
        try:
            file_path = self.get_file_path()
            if content is None:
                content = self.data if self.data is not None else ""
            self._vfs.put(file_path, str(content).encode('utf-8'), create_if_missing=True)
        except (VFSClientException, FileNotFoundError, PermissionError) as e:
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
        try:
            file_path = self.get_file_path()
            return self._vfs.get_text(file_path, encoding='utf-8')
        except VFSClientException as e:
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
        try:
            file_path = self.get_file_path()
            self._vfs.put(file_path, content.encode('utf-8'), create_if_missing=True)
        except VFSClientException as e:
            raise VFSClientException(
                'ItemWriteError',
                f'Failed to write to item file {file_path}: {e}'
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
                self._vfs.remove(file_path, force=True)
        except VFSClientException as e:
            raise VFSClientException(
                'ItemDeleteError',
                f'Failed to delete item file {file_path}: {e}'
            )
    
    def _load_item_info(self) -> None:
        """Load item tags and metadata from tag files."""
        # Load tags by checking which tag files contain this item
        for tag_name in self._config.tags.keys():
            tag_file_path = self._collection_path / f"{tag_name}.{TagManager.TAG_FILE_EXTENSION}"
            try:
                content = self._vfs.get_text(tag_file_path, encoding='utf-8')
                if content:
                    lines = [line.strip() for line in content.splitlines()]
                    if self._name in lines:
                        self._tags.add(tag_name)
            except (VFSClientException, FileNotFoundError, PermissionError):
                # Tag file doesn't exist or can't be read, skip
                continue
    
    def _update_tag_file(self, tag: str, add: bool) -> None:
        """Update a tag file to add or remove this item.
        
        Args:
            tag: The tag name
            add: True to add the item, False to remove it
        """
        # 使用集合配置中定义的标签大小写形式
        if hasattr(self._collection, 'config') and hasattr(self._collection.config, 'tags'):
            for defined_tag in self._collection.config.tags:
                if defined_tag.upper() == tag.upper():
                    tag = defined_tag
                    break
        
        tag_file_path = self._collection_path / f"{tag}.{TagManager.TAG_FILE_EXTENSION}"
        
        try:
            # Read existing content
            try:
                content = self._vfs.get_text(str(tag_file_path), encoding='utf-8')
                lines = [line.strip() for line in content.splitlines() if line.strip()]
            except Exception:
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
            self._vfs.put(str(tag_file_path), new_content.encode('utf-8'), create_if_missing=True)
            
        except Exception as e:
            raise VFSClientException(
                'TagUpdateError',
                f'Failed to update tag file {tag_file_path}: {e}'
            )