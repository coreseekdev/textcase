"""Resource Collection Implementation

This module provides concrete implementation of ResourceCollection protocol,
managing items within a single collection directory.
"""

from pathlib import PurePosixPath
from typing import Dict, Generic, Iterator, List, Optional, Set, TypeVar, Union

from ..client.vfs_client import VFSClient, VFSClientException
from ..proto.resource_collection_protocol import ResourceCollection, ResourceItem
from .config import CollectionConfig
from .item import ResourceItemImpl

T = TypeVar('T')


class ResourceCollectionImpl(Generic[T], ResourceCollection[T]):
    """Directory-based implementation of ResourceCollection protocol.
    
    This implementation stores collections as directories with:
    - .textcase.yml for collection metadata
    - Individual files for each item
    - Tag files (*.txt) containing item names for each tag
    """
    
    def __init__(
        self,
        name: str,
        path: Union[PurePosixPath, str],
        vfs: VFSClient,
        parent: Optional['ResourceCollectionImpl[T]'] = None
    ):
        """Initialize a resource collection.
        
        Args:
            name: The unique name of the collection
            path: Path to the collection directory
            vfs: VFS client for file operations
            parent: Optional parent collection
        """
        self._name = name
        self._path = PurePosixPath(path) if isinstance(path, str) else path
        self._vfs = vfs
        self._parent = parent
        self._config: Optional[CollectionConfig] = None
        self._items_cache: Dict[str, ResourceItemImpl[T]] = {}
        
        # Ensure directory exists and load configuration
        self._ensure_directory_exists()
        self._load_config()
    
    @property
    def name(self) -> str:
        """Get the unique name of this collection."""
        return self._name
    
    @property
    def path(self) -> PurePosixPath:
        """Get the filesystem path of this collection."""
        return self._path
    
    @property
    def parent(self) -> Optional['ResourceCollectionImpl[T]']:
        """Get the parent collection, if any."""
        return self._parent
    
    @property
    def config(self) -> CollectionConfig:
        """Get the collection configuration."""
        if self._config is None:
            self._load_config()
        return self._config
    
    def add_item(self, name: str, data: Optional[T] = None) -> ResourceItem[T]:
        """Add a new item to this collection.
        
        Args:
            name: Unique name for the item within this collection
            data: Optional data payload for the item
            
        Returns:
            The created ResourceItem
            
        Raises:
            ValueError: If an item with the same name already exists
        """
        if self.has_item(name):
            raise ValueError(f"Item '{name}' already exists in collection '{self._name}'")
        
        item = ResourceItemImpl[T](name, self._path, self.config, self._vfs, data)
        self._items_cache[name] = item
        
        # Create the item file if it doesn't exist
        if not item.exists():
            item.create()
        
        return item
    
    def get_item(self, name: str) -> Optional[ResourceItem[T]]:
        """Get an item by name.
        
        Args:
            name: The name of the item to retrieve
            
        Returns:
            The ResourceItem if found, None otherwise
        """
        if name in self._items_cache:
            return self._items_cache[name]
        
        # Check if item file exists
        item = ResourceItemImpl[T](name, self._path, self.config, self._vfs)
        if item.exists():
            self._items_cache[name] = item
            return item
        
        return None
    
    def remove_item(self, name: str) -> bool:
        """Remove an item from this collection.
        
        Args:
            name: The name of the item to remove
            
        Returns:
            True if the item was removed, False if it didn't exist
        """
        item = self.get_item(name)
        if item is None:
            return False
        
        # Delete the item
        item.delete()
        
        # Remove from cache
        if name in self._items_cache:
            del self._items_cache[name]
        
        return True
    
    def has_item(self, name: str) -> bool:
        """Check if an item exists in this collection.
        
        Args:
            name: The name of the item to check
            
        Returns:
            True if the item exists, False otherwise
        """
        return self.get_item(name) is not None
    
    def list_items(self) -> List[str]:
        """List all item names in this collection.
        
        Returns:
            A list of item names
        """
        try:
            # List all files in the collection directory
            items = self._vfs.list(self._path)
            item_names = []
            
            for item_info in items:
                # Skip directories and special files
                if item_info.get('type') == 'directory':
                    continue
                
                filename = item_info.get('name', '')
                if filename.startswith('.') or filename.endswith('.txt'):
                    continue  # Skip config files and tag files
                
                # Parse item name from filename
                item_name = self.config.parse_item_name(filename)
                if item_name:
                    item_names.append(item_name)
            
            return sorted(item_names)
            
        except VFSClientException:
            return []
    
    def iter_items(self) -> Iterator[ResourceItem[T]]:
        """Iterate over all items in this collection.
        
        Yields:
            ResourceItem instances for each item in the collection
        """
        for name in self.list_items():
            item = self.get_item(name)
            if item:
                yield item
    
    def add_tag(self, tag: str, description: str = "") -> None:
        """Add a new tag to this collection.
        
        Args:
            tag: The tag name
            description: Optional description for the tag
        """
        # Update config
        config = self.config
        config.tags[tag] = description
        config.save(self._vfs)
        
        # Create empty tag file
        tag_file_path = self._path / f"{tag}.txt"
        try:
            # Only create if it doesn't exist
            info = self._vfs.info(tag_file_path)
            if not info:
                self._vfs.put(tag_file_path, b'', create_if_missing=True)
        except VFSClientException:
            # File doesn't exist, create it
            self._vfs.put(tag_file_path, b'', create_if_missing=True)
    
    def remove_tag(self, tag: str) -> bool:
        """Remove a tag from this collection.
        
        Args:
            tag: The tag name to remove
            
        Returns:
            True if the tag was removed, False if it didn't exist
        """
        config = self.config
        if tag not in config.tags:
            return False
        
        # Remove from all items first
        for item in self.iter_items():
            if item.has_tag(tag):
                item.remove_tag(tag)
        
        # Remove from config
        del config.tags[tag]
        config.save(self._vfs)
        
        # Delete tag file
        tag_file_path = self._path / f"{tag}.txt"
        try:
            # Note: VFS doesn't have delete method in the interface
            # We'll need to handle this when VFS supports file deletion
            pass  # TODO: Implement file deletion when VFS supports it
        except Exception:
            pass
        
        return True
    
    def has_tag(self, tag: str) -> bool:
        """Check if a tag exists in this collection.
        
        Args:
            tag: The tag name to check
            
        Returns:
            True if the tag exists, False otherwise
        """
        return tag in self.config.tags
    
    def list_tags(self) -> List[str]:
        """List all tags in this collection.
        
        Returns:
            A list of tag names
        """
        return list(self.config.tags.keys())
    
    def get_items_by_tag(self, tag: str) -> List[ResourceItem[T]]:
        """Get all items that have a specific tag.
        
        Args:
            tag: The tag to filter by
            
        Returns:
            A list of ResourceItem instances with the specified tag
        """
        if not self.has_tag(tag):
            return []
        
        tag_file_path = self._path / f"{tag}.txt"
        try:
            content = self._vfs.get_text(tag_file_path, encoding='utf-8')
            if not content:
                return []
            
            item_names = [line.strip() for line in content.splitlines() if line.strip()]
            items = []
            
            for name in item_names:
                item = self.get_item(name)
                if item:
                    items.append(item)
            
            return items
            
        except VFSClientException:
            return []
    
    def search_items(self, query: str, tags: Optional[Set[str]] = None) -> List[ResourceItem[T]]:
        """Search for items by name pattern and optional tags.
        
        Args:
            query: Search pattern for item names
            tags: Optional set of tags to filter by
            
        Returns:
            A list of matching ResourceItem instances
        """
        results = []
        
        for item in self.iter_items():
            # Check name pattern
            if query.lower() not in item.name.lower():
                continue
            
            # Check tags if specified
            if tags:
                item_tags = item.tags
                if not tags.issubset(item_tags):
                    continue
            
            results.append(item)
        
        return results
    
    def get_next_item_name(self, prefix: Optional[str] = None) -> str:
        """Generate the next available item name.
        
        Args:
            prefix: Optional prefix override (uses collection prefix if not provided)
            
        Returns:
            The next available item name
        """
        config = self.config
        actual_prefix = prefix or config.prefix
        
        # Find the highest existing number
        max_num = 0
        for name in self.list_items():
            if name.startswith(actual_prefix):
                number_part = name[len(actual_prefix):]
                if number_part.isdigit():
                    max_num = max(max_num, int(number_part))
        
        # Return next number
        next_num = max_num + 1
        return f"{actual_prefix}{next_num}"
    
    def _ensure_directory_exists(self) -> None:
        """Ensure the collection directory exists."""
        try:
            info = self._vfs.info(self._path)
            if not info:
                # Directory doesn't exist, we need to create it
                # Note: VFS interface doesn't show directory creation method
                # We'll assume it's handled by putting a file in the directory
                pass
        except VFSClientException:
            # Directory doesn't exist
            pass
    
    def _load_config(self) -> None:
        """Load collection configuration from .textcase.yml."""
        self._config = CollectionConfig.load(self._path, self._vfs)
        
        # Update name if it differs
        if self._config.name != self._name:
            self._config.name = self._name
            self._config.save(self._vfs)