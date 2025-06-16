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
from .collection_tag import CollectionTagManager, TagManager
from .item_name_generator import NumericItemNameGenerator
from ..proto.service_vfs_protocol import EntryType

T = TypeVar('T')


class ResourceCollectionImpl(Generic[T], ResourceCollection[T]):
    """Directory-based implementation of ResourceCollection protocol.
    
    This implementation stores collections as directories with:
    - .textcase.yml for collection metadata
    - Individual files for each item
    - Tag files (*.list) containing item names for each tag
    """
    
    # File extension for tag files - now managed by TagManager
    TAG_FILE_EXTENSION: str = '.list'
    # Name of the configuration file within the collection directory
    CONFIG_FILENAME: str = '.textcase.yml'

    def __init__(
        self,
        name: str,
        path: Union[PurePosixPath, str],
        vfs: VFSClient,
        parent: Optional['ResourceCollectionImpl[T]'] = None
    ):
        """Initialize a resource collection.
        
        Note: This constructor is for internal use. Use class methods:
        - create() for creating new collections
        - from_existing() for loading existing collections
        
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
        self._collections_cache: Dict[str, 'ResourceCollectionImpl[T]'] = {}
        self._tag_manager: Optional[CollectionTagManager] = None
        
        # Initialize item name generator
        self._item_name_generator: Optional[NumericItemNameGenerator] = None
    
    @classmethod
    def create(
        cls,
        name: str,
        path: Union[PurePosixPath, str],
        vfs: VFSClient,
        parent: Optional['ResourceCollectionImpl[T]'] = None,
        config: Optional[CollectionConfig] = None,
        force: bool = False
    ) -> 'ResourceCollectionImpl[T]':
        """Create a new resource collection.
        
        This method will:
        - Check if collection already exists (unless force=True)
        - Use provided config or create default configuration
        - Ensure the directory exists
        - Save the configuration to disk
        
        Args:
            name: The unique name of the collection
            path: Path to the collection directory
            vfs: VFS client for file operations
            parent: Optional parent collection
            config: Optional collection configuration (uses default if None)
            force: If True, force initialization even if .textcase.yml exists
            
        Returns:
            A new ResourceCollectionImpl instance
            
        Raises:
            ValueError: If collection already exists and force=False
        """
        
        _path = PurePosixPath(path) if isinstance(path, str) else path
        config_path = _path.joinpath(cls.CONFIG_FILENAME)
        
        # Check if collection already exists
        if not force:
            try:
                # Try to load existing config to check if collection exists
                content = vfs.get_text(config_path, encoding='utf-8')
                if content.strip():  # Non-empty config file exists
                    existing_config = CollectionConfig.loads(config_path, content)
                    raise ValueError(
                        f"Collection already exists at '{path}' with prefix '{existing_config.prefix}'. "
                        f"Use force=True to reinitialize (warning: previous records may become inaccessible "
                        f"if prefix changes)."
                    )
            except FileNotFoundError:
                # Config file doesn't exist, safe to create
                pass
        
        # 尝试构建 collection
        instance = cls(name, _path, vfs, parent)

        # Ensure directory exists
        instance._ensure_directory_exists()
        
        # Use provided config or create default
        if config is not None:
            instance._config = config
        else:
            instance._config = CollectionConfig._create_default_config(name.upper()[:3])
        
        # Save configuration
        instance._save_config()
        return instance
    
    @classmethod
    def create_new(
        cls,
        name: str,
        path: Union[PurePosixPath, str],
        vfs: VFSClient,
        parent: Optional['ResourceCollectionImpl[T]'] = None
    ) -> 'ResourceCollectionImpl[T]':
        """Create a new resource collection (deprecated).
        
        This method is deprecated. Use create() instead.
        
        Args:
            name: The unique name of the collection
            path: Path to the collection directory
            vfs: VFS client for file operations
            parent: Optional parent collection
            
        Returns:
            A new ResourceCollectionImpl instance
        """
        return cls.create(name, path, vfs, parent)
    
    @classmethod
    def from_existing(
        cls,
        name: str,
        path: Union[PurePosixPath, str],
        vfs: VFSClient,
        parent: Optional['ResourceCollectionImpl[T]'] = None
    ) -> 'ResourceCollectionImpl[T]':
        """Load an existing resource collection.
        
        This method is specifically for loading existing collections and will:
        - Load configuration from disk
        - Validate the collection structure
        
        Args:
            name: The unique name of the collection
            path: Path to the collection directory
            vfs: VFS client for file operations
            parent: Optional parent collection
            
        Returns:
            A ResourceCollectionImpl instance loaded from existing data
            
        Raises:
            FileNotFoundError: If the collection directory or config doesn't exist
            ValueError: If the collection configuration is invalid
        """
        instance = cls(name, path, vfs, parent)
        # For existing collections, load configuration
        instance._load_config()
        return instance
    
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
    
    @property
    def tag_manager(self) -> CollectionTagManager:
        """Get the tag manager for this collection.
        
        The tag manager is loaded on demand and cached for future use.
        """
        if self._tag_manager is None:
            self._tag_manager = CollectionTagManager(self, self._vfs)
        return self._tag_manager
    
    @property
    def item_name_generator(self) -> NumericItemNameGenerator:
        """Get the item name generator for this collection."""
        if self._item_name_generator is None:
            self._item_name_generator = NumericItemNameGenerator(
                self.config.num
            )
        return self._item_name_generator
    
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
        
        item = ResourceItemImpl[T](name, self, data)
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
        # 额外处理 name , 如果 name 是 类似 str(1) 
        if name.isdigit() and self.config.num > 1:
            name = name.zfill(self.config.num)

        if name in self._items_cache:
            return self._items_cache[name]
        
        # Check if item file exists
        item = ResourceItemImpl[T](name, self)
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
    
    def get_item_key(self, name: str) -> str:
        """Get the unique key for an item name.
        """
        return self.config.prefix + self.config.sep + name

    def list_items(self) -> List[str]:
        """List all item names in this collection.
        
        Returns:
            A list of item names
        """
        try:
            # List all files in the collection directory
            items = self._vfs.list(self._path)
            item_names = []
            
            for item_name, item_type in items:
                # Skip directories and special files
                if item_type == EntryType.DIR:
                    continue
                
                filename = str(item_name)
                if filename.startswith('.') or filename.endswith(TagManager.TAG_FILE_EXTENSION):
                    continue  # Skip config files and tag files
                
                # Check file sufix
                if not filename.endswith(self.config.suffix):
                    continue
                
                if self.config.prefix:
                    if not filename.startswith(self.config.prefix+self.config.sep):
                        continue

                _, item_name = self.config.parse_item_name(filename)
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
    
    def get_next_item_name(self, prefix: str = '') -> str:
        """Generate the next available item name with numeric numbering.
        
        This method finds the maximum numeric value among existing items that match
        the given prefix pattern and returns the next sequential number.
        
        Args:
            prefix: Optional prefix to filter items. If empty, considers all numeric items.
                   For example, if collection has [REQ-001.md, REQ-001.2.md] and prefix='001.',
                   the next item would be '001.3'. If prefix='', next item would be '2' or '002'.
        
        Returns:
            The next available item name as a string
            
        Examples:
            - Collection has items: ['001', '002', '005'] -> get_next_item_name() returns '006'
            - Collection has items: ['001.1', '001.2', '002'] -> get_next_item_name('001.') returns '001.3'
            - Empty collection -> get_next_item_name() returns '001'
        """
        
        # Get item names (these are parsed names, not filenames)
        # 如果 prefix 为空，则根据 config 自动计算 prefix
        if not prefix:
            prefix = self.config.prefix + self.config.sep
            
        item_names = self.list_items()
        return self.item_name_generator.get_next_item_name(item_names, prefix)
    
    def add_tag(self, tag: str, description: Optional[str] = None) -> None:
        """Add a tag to this collection.
        
        Args:
            tag: The tag name
            description: Optional description for the tag
        """
        self.tag_manager.add_tag(tag, description)
    
    def remove_tag(self, tag: str) -> bool:
        """Remove a tag from this collection.
        
        Args:
            tag: The tag name to remove
            
        Returns:
            True if the tag was removed, False if it didn't exist
        """
        return self.tag_manager.remove_tag(tag)
    
    def has_tag(self, tag: str) -> bool:
        """Check if a tag exists in this collection.
        
        Args:
            tag: The tag name to check
            
        Returns:
            True if the tag exists, False otherwise
        """
        return self.tag_manager.has_tag(tag)
    
    def list_tags(self) -> List[str]:
        """List all tags in this collection.
        
        Returns:
            A list of tag names
        """
        return self.tag_manager.list_tags()
    
    @property
    def tags(self) -> Dict[str, Set[str]]:
        """Get all tags and their associated item names.
        
        Returns:
            Dictionary mapping tag names to sets of item names
        """
        return self.tag_manager.get_all_tags()
        
    def get_items_by_tag(self, tag: str) -> List[ResourceItem[T]]:
        """Get all items that have a specific tag.
        
        Args:
            tag: The tag to filter by
            
        Returns:
            A list of ResourceItem instances with the specified tag
        """
        if not self.has_tag(tag):
            return []
        
        # Get item names from tag manager
        item_names = self.tag_manager.get_items_by_tag(tag)
        items = []
        
        # Convert item names to ResourceItem instances
        for name in item_names:
            item = self.get_item(name)
            if item:
                items.append(item)
        
        return items
    
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
    
    def get_items_by_tags(self, tags: Set[str], match_all: bool = True) -> List[ResourceItem[T]]:
        """Get items that match tag criteria.
        
        Args:
            tags: Set of tag names to search for
            match_all: If True, items must have all tags; if False, any tag
            
        Returns:
            List of items matching the tag criteria
        """
        if not tags:
            return []
        
        # Get all items with their tags
        all_items = list(self.iter_items())
        results = []
        
        for item in all_items:
            item_tags = item.tags
            if match_all:
                # Item must have all specified tags
                if tags.issubset(item_tags):
                    results.append(item)
            else:
                # Item must have at least one of the specified tags
                if tags.intersection(item_tags):
                    results.append(item)
        
        return results
    
    def get_available_tags(self) -> Set[str]:
        """Get all tags used in this collection.
        
        Returns:
            Set of all tag names used by items in this collection
        """
        return set(self.tag_manager.list_tags())
    
    def clear(self) -> None:
        """Remove all items and sub-collections from this collection."""
        # Remove all items first
        for item_name in self.list_items():
            item = self.get_item(item_name)
            if item:
                item.delete()
        
        # Remove all sub-collections
        for sub_collection in self.iter_collections():
            sub_collection.clear()  # Recursively clear sub-collections
            # Remove the sub-collection directory
            try:
                self._vfs.remove(sub_collection.path, force=True, recursive=True)
            except VFSClientException:
                pass  # Continue even if removal fails
        
        # Clear all tags
        if self._tag_manager is not None:
            self._tag_manager.clear_tags()
        
        # Clear caches
        self._items_cache.clear()
        self._collections_cache.clear()
        self._tag_manager = None  # Reset tag manager
    
    def get_next_item_name(self, prefix: Optional[str] = None) -> str:
        """Generate the next available item name.
        
        Args:
            prefix: Optional prefix override (uses collection prefix if not provided)
            
        Returns:
            The next available item name
        """
        return self.item_name_generator.get_next_item_name(self.list_items(), prefix)
    
    def _ensure_directory_exists(self) -> None:
        """Ensure the collection directory exists."""
        try:
            info = self._vfs.info(self._path)
            if not info:
                # Directory doesn't exist, create it
                self._vfs.mkdir(self._path, parents=True, exist_ok=True)
        except FileNotFoundError:
            # Directory doesn't exist, create it
            try:
                self._vfs.mkdir(self._path, parents=True, exist_ok=True)
            except FileExistsError:
                # 如果文件已经存在，则无需处理任何事
                pass
    
    def _load_config(self) -> None:
        """Load collection configuration from .textcase.yml."""
        config_path = self._path / self.CONFIG_FILENAME
        
        try:
            # Try to load existing config
            content = self._vfs.get_text(config_path, encoding='utf-8')
            if content:
                self._config = CollectionConfig.loads(config_path, content)
            else:
                # Create default config if file is empty
                self._config = CollectionConfig._create_default_config(self._name.upper()[:3])
                self._save_config()
        except FileNotFoundError:
            # Create default config if file doesn't exist
            self._config = CollectionConfig._create_default_config(self._name.upper()[:3])
            self._save_config()
        
        # Update name if it differs
        self._save_config()
    
    def _save_config(self) -> None:
        """Save collection configuration to .textcase.yml."""
        config_path = self._path / self.CONFIG_FILENAME
        content = self._config.dumps()
        
        try:
            self._vfs.put(config_path, content.encode('utf-8'), create_if_missing=True)
        except Exception as e:
            raise VFSClientException(
                'ConfigSaveError',
                f'Failed to save collection config to {config_path}: {e}'
            )
    
    def item_exists(self, name: str) -> bool:
        """Check if an item file exists.
        
        Args:
            name: The name of the item
            
        Returns:
            True if the item file exists, False otherwise
        """
        file_path = self._get_item_file_path(name)
        try:
            info = self._vfs.info(file_path)
            return info is not None
        except VFSClientException:
            return False
    
    def create_item_file(self, name: str, content: str = "") -> None:
        """Create an item file.
        
        Args:
            name: The name of the item
            content: Initial content for the file
            
        Raises:
            VFSClientException: If the file cannot be created
        """
        file_path = self._get_item_file_path(name)
        try:
            self._vfs.put(file_path, content.encode('utf-8'), create_if_missing=True)
        except Exception as e:
            raise VFSClientException(
                'ItemCreateError',
                f'Failed to create item file {file_path}: {e}'
            )
    
    def read_item_file(self, name: str) -> str:
        """Read the content of an item file.
        
        Args:
            name: The name of the item
            
        Returns:
            The file content as string
            
        Raises:
            VFSClientException: If the file cannot be read
        """
        file_path = self._get_item_file_path(name)
        try:
            return self._vfs.get_text(file_path, encoding='utf-8')
        except Exception as e:
            raise VFSClientException(
                'ItemReadError',
                f'Failed to read item file {file_path}: {e}'
            )
    
    def write_item_file(self, name: str, content: str) -> None:
        """Write content to an item file.
        
        Args:
            name: The name of the item
            content: The content to write
            
        Raises:
            VFSClientException: If the file cannot be written
        """
        file_path = self._get_item_file_path(name)
        try:
            self._vfs.put(file_path, content.encode('utf-8'), create_if_missing=True)
        except Exception as e:
            raise VFSClientException(
                'ItemWriteError',
                f'Failed to write item file {file_path}: {e}'
            )
    
    def delete_item_file(self, name: str) -> None:
        """Delete an item file.
        
        Args:
            name: The name of the item
            
        Raises:
            VFSClientException: If the file cannot be deleted
        """
        file_path = self._get_item_file_path(name)
        try:
            # Check if file exists before attempting to delete
            if self.item_exists(name):
                self._vfs.remove(file_path, force=True)
        except VFSClientException as e:
            raise VFSClientException(
                'ItemDeleteError',
                f'Failed to delete item file {file_path}: {e}'
            )
    
    def _get_item_file_path(self, name: str) -> PurePosixPath:
        """Get the file path for an item.
        
        Args:
            name: The name of the item
            
        Returns:
            The full path to the item's file
        """
        filename = self.config.get_item_filename(name)
        # 确保使用PurePosixPath处理路径
        return self._path / filename
    
    def get_item_tags(self, name: str) -> Set[str]:
        """Get all tags for an item.
        
        Args:
            name: The name of the item
            
        Returns:
            A set of tags associated with the item
        """
        return self.tag_manager.get_item_tags(name)
    
    def update_item_tag(self, name: str, tag: str, add: bool) -> None:
        """Update a tag file to add or remove an item.
        
        Args:
            name: The name of the item
            tag: The tag name
            add: True to add the item, False to remove it
        """
        self.tag_manager.update_item_tag(name, tag, add)
    
    def assign_tag(self, item_name: str, tag: str) -> None:
        """Assign a tag to an item.
        
        Args:
            item_name: Name of the item to tag
            tag: Tag name to assign
        """
        self.update_item_tag(item_name, tag, add=True)
    
    def unassign_tag(self, item_name: str, tag: str) -> None:
        """Remove a tag from an item.
        
        Args:
            item_name: Name of the item
            tag: Tag name to remove
        """
        self.update_item_tag(item_name, tag, add=False)
    
    # Sub-collection management methods required by ResourceCollection protocol
    @property
    def item_names(self) -> List[str]:
        """Get all items in this collection.
        
        Returns:
            List of item names
        """
        # Build a dictionary of all items
        return self.list_items()
    
    @property
    def collections(self) -> Dict[str, 'ResourceCollection[T]']:
        """Get all sub-collections of this collection.
        
        Returns:
            Dictionary mapping sub-collection names to collection instances
        """
        # This is a placeholder implementation
        return {}
    
    def add_collection(self, collection: 'ResourceCollection[T]') -> None:
        """Add a sub-collection to this collection.
        
        Args:
            collection: Sub-collection to add
            
        Raises:
            ValueError: If a sub-collection with the same name already exists
        """
        # This is a placeholder implementation
        # In a real implementation, we would create a sub-directory
        # and initialize it as a collection
        pass
    
    def remove_collection(self, name: str) -> Optional['ResourceCollection[T]']:
        """Remove a sub-collection from this collection.
        
        Args:
            name: Name of the sub-collection to remove
            
        Returns:
            The removed sub-collection, or None if not found
        """
        # This is a placeholder implementation
        return None
    
    def get_collection(self, name: str) -> Optional['ResourceCollection[T]']:
        """Get a sub-collection by name.
        
        Args:
            name: Name of the sub-collection to retrieve
            
        Returns:
            The sub-collection if found, None otherwise
        """
        # This is a placeholder implementation
        return None
    
    def has_collection(self, name: str) -> bool:
        """Check if a sub-collection exists.
        
        Args:
            name: Name of the sub-collection to check
            
        Returns:
            True if the sub-collection exists, False otherwise
        """
        # This is a placeholder implementation
        return False
    
    def size(self) -> int:
        """Get the number of items in this collection.
        
        Returns:
            Number of items (not including sub-collections)
        """
        return len(self.list_items())
    
    def is_empty(self) -> bool:
        """Check if this collection is empty (has no items).
        
        Returns:
            True if the collection has no items, False otherwise
        """
        return len(self.list_items()) == 0
    
    def size(self) -> int:
        """Get the number of items in this collection.
        
        Returns:
            The number of items
        """
        return len(self.list_items())