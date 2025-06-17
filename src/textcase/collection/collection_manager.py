"""Resource Collection Manager Implementation

This module provides the main manager for resource collections,
storing hierarchy information in git_repo_root_path/.textcase.yml.
"""

import os
import re
from pathlib import Path, PurePosixPath
from typing import Dict, Generic, Iterator, List, Optional, Tuple, Set, TypeVar, Union

import yaml

from ..client.vfs_client import VFSClient, VFSClientException
from ..proto.resource_collection_protocol import ResourceCollection, ResourceCollectionManager, ResourceItem
from .collection import ResourceCollectionImpl
from .config_collection_manager import ConfigCollectionManagerImpl

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
        
        # 管理配置的文件的集合
        self._config_collection_manager: Optional[ConfigCollectionManagerImpl[T]] = None

        # 缓存集合前缀映射关系
        self._prefix_to_collection: Dict[str, Dict] = {}
        self._prefix_list: List[str] = []
        
        # Load existing configuration
        self._load_config()
    
    @property
    def root_collection(self) -> Optional[ResourceCollection[T]]:
        """Get the root collection."""
        if self._root_collection_name:
            return self.get_collection(self._root_collection_name)
        return None
    
    @property
    def config_collection_manager(self) -> Optional[ConfigCollectionManagerImpl[T]]:
        """Get the configuration collection manager."""
                # 检查是否有根模块配置
        if not self._root_collection_name:
            raise ValueError("Root module not configured. Cannot access config collections.")
            
        # 初始化配置集合管理器（如果尚未初始化）
        if not self._config_collection_manager:
            root_collection = self.get_collection(self._root_collection_name)
            if not root_collection:
                raise ValueError(f"Root collection '{self._root_collection_name}' not found")
                
            # 使用根模块路径的 .config 作为配置根目录, 注意 config 是按需加载的，因此不一定存在
            repo_root = root_collection.path.joinpath(".config")
            
            # 初始化配置集合管理器
            self._config_collection_manager = ConfigCollectionManagerImpl[T](repo_root, self._vfs)
            
        return self._config_collection_manager

    # 处理与 config collection 有关的代码
    def _get_config_collection(self, name: str) -> Optional[ResourceCollection[T]]:
        """Get or create a configuration collection.
        
        Args:
            name: Collection name (must start with "config.")
            
        Returns:
            Configuration collection or None if not a valid config collection name
            
        Raises:
            ValueError: If root module is not configured
        """
        # 使用管理器获取配置集合
        return self.config_collection_manager.get_collection(name)

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
        # 对于配置集合需要特别处理，其特点为 config.xxxx 作为 name
        if name.startswith(ConfigCollectionManagerImpl.CONFIG_PREFIX):
            # 注意: config.xxx 仅能通过 get_collection 获取，不能添加，也无法删除（一旦创建过) 
            # 注意: config.xxx 也不会出现再 list_collections 中 
            return self._get_config_collection(name)

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
            # 如果没有指定父集合，则添加为根集合
            if self._root_collection_name:
                # 如果已经有根集合，则添加为根集合的子集合
                parent = self._root_collection_name
            else:
                # 如果没有根集合，则设置为根集合
                self._root_collection_name = name
        
        # Add to hierarchy
        if name not in self._hierarchy:
            self._hierarchy[name] = {'children': [], 'path': str(collection.path)}
        
        # Add to parent's children list if specified
        if parent:
            if parent not in self._hierarchy:
                self._hierarchy[parent] = {'children': [], 'path': ''}
            if name not in self._hierarchy[parent]['children']:
                self._hierarchy[parent]['children'].append(name)
            self._parent_map[name] = parent
        
        # Add to cache
        self._collections_cache[name] = collection
        
        # 更新前缀映射缓存
        self._update_prefix_cache()
        
        # Save configuration
        self._save_config()
    
    def remove_collection(self, name: str) -> Optional[ResourceCollection[T]]:
        """Remove a collection from the manager.
        
        Args:
            name: The name of the collection to remove
            
        Returns:
            The removed collection if found, None otherwise
        """
        if name not in self._hierarchy:
            return None
            
        # Get the collection before removing
        collection = self.get_collection(name)
        
        # Remove from parent's children list
        parent = self._parent_map.get(name)
        if parent and parent in self._hierarchy:
            if name in self._hierarchy[parent]['children']:
                self._hierarchy[parent]['children'].remove(name)
        
        # Remove from hierarchy
        del self._hierarchy[name]
        
        # Remove from parent map
        if name in self._parent_map:
            del self._parent_map[name]
        
        # Remove from cache
        if name in self._collections_cache:
            del self._collections_cache[name]
        
        # Update root collection if needed
        if self._root_collection_name == name:
            # Find a new root collection (one without parent)
            new_root = None
            for coll_name in self._hierarchy.keys():
                if self._parent_map.get(coll_name) is None:
                    new_root = coll_name
                    break
            self._root_collection_name = new_root
        
        # 更新前缀映射缓存
        self._update_prefix_cache()
        
        # Save configuration
        self._save_config()
        
        return collection
    
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
        
    def parse_resource_reference(self, reference: str, partial: bool = False) -> Tuple[Optional[ResourceCollection[T]], Optional[ResourceItem[T]]]:
        """Parse a string reference to locate a collection and/or item.
        
        Args:
            reference: The string reference to parse (e.g., "REQ1", "REQ")
            partial: Whether to allow partial matches (e.g. 'REQ01' for 'REQ011')
            
        Returns:
            A tuple of (collection, item) where either may be None if not found
            Examples:
                'REQ1' -> (REQ_collection, REQ001_item)  # Collection with name/prefix 'REQ' and item '001'
                'REQ' -> (REQ_collection, None)          # Just the collection
                'NONEEXIST' -> (None, None)              # Nothing found
        """
        if not reference:
            return None, None
            
        # 首先尝试完全匹配集合名称
        if reference in self._hierarchy:
            return self.get_collection(reference), None

        # 为配置类的 collection 开后门
        if reference.startswith(ConfigCollectionManagerImpl.CONFIG_PREFIX):
            """
            可能的配置表达： 
            - config.agent                  collection , none
            - config.agent.template         collection , none
            - conifg.agent.agent_name       collection , item | none
            # 目前仅支持作为集合的情况
            """
            return self.get_collection(reference), None

        # 使用缓存的前缀映射关系
        # 如果缓存为空，先更新缓存
        if not self._prefix_to_collection:
            self._update_prefix_cache()
            
        # 查找最长匹配的前缀
        best_match = None
        remaining = ''
        
        # 对引用字符串进行大写处理，便于匹配
        reference_upper = reference.upper()
        
        # 遍历缓存的前缀列表，查找匹配
        for prefix in self._prefix_list:
            if reference_upper.startswith(prefix):
                best_match = self._prefix_to_collection[prefix]
                remaining = reference[len(prefix):]
                break
        
        # 如果没有找到匹配的集合前缀
        if not best_match:
            return None, None
            
        collection = best_match['collection']
        sep = best_match['sep']
        
        # 如果没有剩余部分，则只返回集合
        if not remaining:
            return collection, None
            
        # 处理分隔符
        if sep:
            # 如果剩余部分以分隔符开头，去掉分隔符
            if remaining.startswith(sep):
                item_name = remaining[len(sep):]
            else:
                # 如果引用中省略了分隔符，直接使用剩余部分作为项目名
                item_name = remaining
        else:
            item_name = remaining
            
        # 尝试获取项目
        if item_name:
            # 直接尝试获取项目, 不需要额外处理， item_name 会自动填充 0
            item = collection.get_item(item_name)
            if item:
                return collection, item
                            
            # 仅在 partial 模式下才尝试查找以此名称开头的项目
            if partial:
                # 获取所有项目名称并排序，确保结果一致
                item_names = sorted(collection.list_items())
                for existing_item_name in item_names:
                    if existing_item_name.startswith(item_name):
                        item = collection.get_item(existing_item_name)
                        if item:
                            return collection, item
        
        # 返回找到的集合，但没有找到项目
        return collection, None
    
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
        """Load configuration from disk."""
        try:
            content = self._vfs.get_text(self._config_path, encoding='utf-8')
            data = yaml.safe_load(content) or {}
            
            # Load hierarchy
            self._hierarchy = data.get('collections', {})
            
            # Build parent map
            self._parent_map = {}
            for name, info in self._hierarchy.items():
                for child in info.get('children', []):
                    self._parent_map[child] = name
            
            # Set root collection
            self._root_collection_name = data.get('root_collection')
            
            # 更新前缀映射缓存
            self._update_prefix_cache()
        except FileNotFoundError:
            # No config file exists yet
            self._hierarchy = {}
            self._parent_map = {}
            self._root_collection_name = None
            self._prefix_to_collection = {}
            self._prefix_list = []
            
    def _update_prefix_cache(self) -> None:
        """更新前缀到集合的映射缓存。
        
        当添加或删除集合时，应该调用此方法以更新缓存。
        """
        self._prefix_to_collection = {}
        self._prefix_list = []
        
        for coll_name in self._hierarchy.keys():
            collection = self.get_collection(coll_name)
            if collection:
                config = collection.config
                if config and config.prefix:
                    prefix = config.prefix.upper()  # 统一使用大写进行匹配
                    self._prefix_to_collection[prefix] = {
                        'collection': collection,
                        'sep': config.sep
                    }
                    self._prefix_list.append(prefix)
        
        # 按前缀长度降序排序，确保优先匹配最长前缀
        self._prefix_list.sort(key=len, reverse=True)
    
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