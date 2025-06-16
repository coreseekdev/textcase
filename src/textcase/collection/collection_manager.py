"""Resource Collection Manager Implementation

This module provides the main manager for resource collections,
storing hierarchy information in git_repo_root_path/.textcase.yml.
"""

from pathlib import Path, PurePosixPath
from typing import Dict, Generic, Iterator, List, Optional, Set, TypeVar, Union

import yaml

from ..client.vfs_client import VFSClient, VFSClientException
from ..proto.resource_collection_protocol import ResourceCollection, ResourceCollectionManager, ResourceItem
from .collection import ResourceCollectionImpl

T = TypeVar('T')


class ResourceCollectionManagerImpl(Generic[T], ResourceCollectionManager[T]):
    """File-based implementation of ResourceCollectionManager protocol.
    
    This implementation stores the collection hierarchy and metadata in
    a .textcase.yml file at the git repository root, and manages individual
    collections as subdirectories.
    """
    
    # Configuration file name constant
    CONFIG_FILENAME = '.textcase.yml'
    
    def __init__(self, git_repo_root: Union[Path, PurePosixPath, str], vfs: VFSClient):
        """Initialize the collection manager.
        
        Args:
            git_repo_root: Path to the git repository root
            vfs: VFS client for file operations
        """
        if isinstance(git_repo_root, str):
            self._git_repo_root = PurePosixPath(git_repo_root)
        elif isinstance(git_repo_root, Path):
            self._git_repo_root = PurePosixPath(git_repo_root.as_posix())
        else:
            self._git_repo_root = git_repo_root
            
        self._vfs = vfs
        self._config_path = self._vfs.to_vfs_path(self._git_repo_root.joinpath(self.CONFIG_FILENAME))
        self._collections_cache: Dict[str, ResourceCollectionImpl[T]] = {}
        self._hierarchy: Dict[str, Dict] = {}  # collection_name -> {children, path}
        self._parent_map: Dict[str, Optional[str]] = {}  # collection_name -> parent_name
        self._root_collection_name: Optional[str] = None
        
        # Load existing configuration
        self._load_config()
    
    @property
    def root_collection(self) -> Optional[ResourceCollection[T]]:
        """Get the root collection."""
        if self._root_collection_name:
            return self.get_collection(self._root_collection_name)
        return None
    
    def create_collection(
        self,
        name: str,
        parent: Optional[str] = None,
        path: Optional[Union[PurePosixPath, str]] = None,
        force: bool = False
    ) -> ResourceCollection[T]:
        """Create a new collection.
        
        Args:
            name: Unique name for the collection
            parent: Optional parent collection name
            path: Optional custom path (relative to git repo root)
            tags: Optional tags for the collection
            force: If True, force creation even if collection already exists
            
        Returns:
            The created ResourceCollection
            
        Raises:
            ValueError: If a collection with the same name already exists
        """
        if name in self._hierarchy and not force:
            raise ValueError(f"Collection '{name}' already exists")
        
        # Validate parent exists if specified
        if parent and parent not in self._hierarchy:
            raise ValueError(f"Parent collection '{parent}' does not exist")
        
        if not parent:
            # 仅 root collection 可以没有 parent
            if self._root_collection_name and not force:
                raise ValueError(f"Root collection '{self._root_collection_name}' already exists")

        # Determine collection path
        if path is None:
            if parent:
                parent_path = PurePosixPath(self._hierarchy[parent]['path'])
                collection_path = parent_path / name
            else:
                # CASE stands for Computer-aid Software Engineering
                collection_path = self._git_repo_root / 'case' / name
        else:
            # 确保路径是PurePosixPath类型
            if isinstance(path, str):
                # 将Windows风格路径转换为POSIX风格
                path = Path(path).absolute()
            
            # collection_path 应该是 vfs 的 path
            if path.is_absolute():
                # TODO: 需要验证绝对路径创建 collection 的情况
                collection_path = self._vfs.to_vfs_path(path)
            else:
                collection_path = self._vfs.mount_point().joinpath(path)
        
        # Create collection instance
        parent_collection = self.get_collection(parent) if parent else None
        collection = ResourceCollectionImpl.create(name, collection_path, self._vfs, parent_collection, force=force)

        if collection.name in self._hierarchy and force:
            # 已存在，直接返回
            return collection

        self.add_collection(collection, parent)
        return collection
    
    def get_collection(self, name: str) -> Optional[ResourceCollection[T]]:
        """Get a collection by name.
        
        Args:
            name: The name of the collection to retrieve
            
        Returns:
            The ResourceCollection if found, None otherwise
        """
        if not name or name not in self._hierarchy:
            return None
            
        # Return from cache if available
        if name in self._collections_cache:
            return self._collections_cache[name]
            
        # Create and cache collection instance
        # 配置中的路径为 相对于 vfs root 的相对路径
        collection_path = PurePosixPath('/').joinpath(self._hierarchy[name]['path'])
        parent_name = self._parent_map.get(name)
        parent_collection = self.get_collection(parent_name) if parent_name else None
        
        collection = ResourceCollectionImpl.from_existing(name, collection_path, self._vfs, parent_collection)
        self._collections_cache[name] = collection
        
        return collection
        
    def get_parent_collection_name(self, name: str) -> Optional[str]:
        """Get the parent collection name for a collection.
        
        Args:
            name: The name of the collection to get the parent for
            
        Returns:
            The parent collection name if it has one, None otherwise
        """
        if name not in self._hierarchy:
            return None
            
        return self._parent_map.get(name)
        
    def get_parent_collection(self, name: str) -> Optional[ResourceCollection[T]]:
        """Get the parent collection for a collection.
        
        Args:
            name: The name of the collection to get the parent for
            
        Returns:
            The parent collection if it has one, None otherwise
        """
        parent_name = self.get_parent_collection_name(name)
        if not parent_name:
            return None
        
        return self.get_collection(parent_name)
    
    def add_collection(self, collection: ResourceCollection[T], parent: Optional[str] = None) -> None:
        """Add an existing collection to the manager.
        
        Args:
            collection: The collection to add
            parent: Optional parent collection name
            
        Raises:
            ValueError: If a collection with the same name already exists
        """
        name = collection.name
        if name in self._hierarchy:
            raise ValueError(f"Collection '{name}' already exists")
        
        # Validate parent exists if specified
        if parent and parent not in self._hierarchy:
            raise ValueError(f"Parent collection '{parent}' does not exist")
        if not parent:
            # 仅 root collection 可以没有 parent
            if self._root_collection_name:
                raise ValueError(f"Root collection '{self._root_collection_name}' already exists")
        
        # Add to hierarchy
        if isinstance(collection, ResourceCollectionImpl):
            # 由于理论上，所有的第三方 repo 都需要挂接在 root vfs 中，因此 记录的是 vfs path
            relative_path = collection.path.relative_to(self._vfs.mount_point())
        else:
            raise NotImplemented
            # For external collections, we need to determine the path
            # relative_path = PurePosixPath('collections') / name
        
        self._hierarchy[name] = {
            'children': [],
            'path': str(relative_path)
        }
        
        # Update parent relationship in memory
        self._parent_map[name] = parent
        
        # Update parent's children list
        if parent:
            if name not in self._hierarchy[parent]['children']:
                self._hierarchy[parent]['children'].append(name)
        else:
            self._root_collection_name = name

        # Cache the collection
        if isinstance(collection, ResourceCollectionImpl):
            self._collections_cache[name] = collection
        
        # Save configuration
        self._save_config()
    
    def remove_collection(self, name: str) -> bool:
        """Remove a collection and all its sub-collections.
        
        Args:
            name: The name of the collection to remove
            
        Returns:
            True if the collection was removed, False if it didn't exist
        """
        if name not in self._hierarchy:
            return False
        
        # Recursively remove all children first
        children = self._hierarchy[name]['children'].copy()
        for child_name in children:
            self.remove_collection(child_name)
        
        # Remove from parent's children list
        parent_name = self._parent_map.get(name)
        if parent_name and parent_name in self._hierarchy:
            self._hierarchy[parent_name]['children'].remove(name)
            
        # Remove from parent map
        if name in self._parent_map:
            del self._parent_map[name]
        
        # Remove from hierarchy
        del self._hierarchy[name]
        
        # Remove from cache
        if name in self._collections_cache:
            del self._collections_cache[name]
        
        # Remove the actual collection directory and files
        collection_path = PurePosixPath(self._hierarchy[name]['path'])
        try:
            self._vfs.remove(collection_path, force=True, recursive=True)
        except VFSClientException:
            # Continue even if physical removal fails
            pass
        
        # Update root/default collection if necessary
        if self._root_collection_name == name:
            # Find a new root collection (one without parent)
            new_root = None
            for coll_name in self._hierarchy.keys():
                if self._parent_map.get(coll_name) is None:
                    new_root = coll_name
                    break
            self._root_collection_name = new_root
        
        if self._default_collection_name == name:
            self._default_collection_name = self._root_collection_name
        
        # Save configuration
        self._save_config()
        
        return True
    
    def move_collection(self, name: str, new_parent: Optional[str]) -> bool:
        """Move a collection to a new parent.
        
        Args:
            name: The name of the collection to move
            new_parent: The new parent collection name (None for root level)
            
        Returns:
            True if the collection was moved, False if it didn't exist
        """
        if name not in self._hierarchy:
            return False
        
        # Validate new parent exists if specified
        if new_parent and new_parent not in self._hierarchy:
            raise ValueError(f"New parent collection '{new_parent}' does not exist")
        
        # Prevent circular references
        if new_parent and self._is_ancestor(name, new_parent):
            raise ValueError(f"Cannot move collection '{name}' to '{new_parent}': would create circular reference")
        
        # Remove from old parent's children list
        old_parent = self._parent_map.get(name)
        if old_parent and old_parent in self._hierarchy:
            self._hierarchy[old_parent]['children'].remove(name)
        
        # Update collection's parent in memory
        self._parent_map[name] = new_parent
        
        # Add to new parent's children list
        if new_parent:
            self._hierarchy[new_parent]['children'].append(name)
        
        # Save configuration
        self._save_config()
        
        return True
    
    def list_collections(self, parent: Optional[str] = None) -> List[str]:
        """List collection names, optionally filtered by parent.
        
        Args:
            parent: Optional parent collection name to filter by
            
        Returns:
            A list of collection names
        """
        if parent is None:
            return list(self._hierarchy.keys())
        
        if parent not in self._hierarchy:
            return []
        
        return self._hierarchy[parent]['children'].copy()
    
    def iter_all_collections(self) -> Iterator[ResourceCollection[T]]:
        """Iterate over all collections in the manager.
        
        Yields:
            ResourceCollection instances for each collection
        """
        for name in self._hierarchy.keys():
            collection = self.get_collection(name)
            if collection:
                yield collection
    
    def find_collection_path(self, name: str) -> Optional[List[str]]:
        """Find the path from root to a specific collection.
        
        Args:
            name: The name of the collection to find
            
        Returns:
            A list of collection names from root to the target, or None if not found
        """
        if name not in self._hierarchy:
            return None
        
        path = []
        current = name
        
        while current:
            path.insert(0, current)
            current = self._parent_map.get(current)
        
        return path
    
    def search_items_across_collections(
        self,
        query: str,
        tags: Optional[Set[str]] = None,
        collections: Optional[List[str]] = None
    ) -> Dict[str, List[ResourceItem[T]]]:
        """Search for items across multiple collections.
        
        Args:
            query: Search pattern for item names
            tags: Optional set of tags to filter by
            collections: Optional list of collection names to search in
            
        Returns:
            A dictionary mapping collection names to lists of matching items
        """
        results = {}
        
        # Determine which collections to search
        if collections is None:
            search_collections = list(self._hierarchy.keys())
        else:
            search_collections = [name for name in collections if name in self._hierarchy]
        
        # Search each collection
        for collection_name in search_collections:
            collection = self.get_collection(collection_name)
            if collection:
                items = collection.search_items(query, tags)
                if items:
                    results[collection_name] = items
        
        return results
    
    def set_root_collection(self, name: str) -> bool:
        """Set the root collection.
        
        Args:
            name: The name of the collection to set as root
            
        Returns:
            True if successful, False if collection doesn't exist
        """
        if name not in self._hierarchy:
            return False
        
        self._root_collection_name = name
        self._save_config()
        return True
    
    def set_default_collection(self, name: str) -> bool:
        """Set the default collection.
        
        Args:
            name: The name of the collection to set as default
            
        Returns:
            True if successful, False if collection doesn't exist
        """
        if name not in self._hierarchy:
            return False
        
        self._default_collection_name = name
        self._save_config()
        return True
    
    def _is_ancestor(self, ancestor: str, descendant: str) -> bool:
        """Check if one collection is an ancestor of another.
        
        Args:
            ancestor: The potential ancestor collection name
            descendant: The potential descendant collection name
            
        Returns:
            True if ancestor is an ancestor of descendant
        """
        current = descendant
        while current:
            parent = self._parent_map.get(current)
            if parent == ancestor:
                return True
            current = parent
        return False
    
    def _load_config(self) -> None:
        """Load configuration from .textcase.yml."""
        try:
            content = self._vfs.get_text(self._config_path, encoding='utf-8')
            if content:
                data = yaml.safe_load(content) or {}
                
                self._hierarchy = data.get('collections', {})
                self._root_collection_name = data.get('root_collection')
                
                # Rebuild parent relationships from children lists
                self._rebuild_parent_map()
            else:
                self._hierarchy = {}
                self._parent_map = {}
                self._root_collection_name = None
                self._default_collection_name = None

        except FileNotFoundError:
            # Config file doesn't exist, start with empty state
            self._hierarchy = {}
            self._parent_map = {}
            self._root_collection_name = None
            self._default_collection_name = None
            
    def _rebuild_parent_map(self) -> None:
        """Rebuild the parent map from the hierarchy's children lists."""
        # Clear existing parent map
        self._parent_map = {}
        
        # Set all collections to have no parent initially
        for name in self._hierarchy.keys():
            self._parent_map[name] = None
        
        # Update parent relationships based on children lists
        for parent_name, info in self._hierarchy.items():
            for child_name in info.get('children', []):
                self._parent_map[child_name] = parent_name
    
    def _save_config(self) -> None:
        """Save configuration to .textcase.yml."""
        data = {
            'collections': self._hierarchy,
            'root_collection': self._root_collection_name,
        }
        
        try:
            content = yaml.dump(data, default_flow_style=False, allow_unicode=True)
            self._vfs.put(self._config_path, content.encode('utf-8'), create_if_missing=True)
        except Exception as e:
            raise VFSClientException(
                'ConfigSaveError',
                f'Failed to save collection manager config to {self._config_path}: {e}'
            )