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
"""Configuration collection manager implementation."""

from pathlib import Path, PurePosixPath
from typing import Generic, TypeVar, Optional, Tuple, Dict, List, Union, Iterator
import yaml
import shutil
import os

from ..client.vfs_client import VFSClient, VFSClientException
from ..proto.resource_collection_protocol import ResourceCollection, ResourceItem, ResourceCollectionManager
from .config_collection import ConfigCollectionImpl, ConfigTemplateCollectionImpl

T = TypeVar('T')


class ConfigCollectionManagerImpl(Generic[T], ResourceCollectionManager[T]):
    """Manager for configuration collections."""
    
    # 配置集合将基于数据目录动态判断，不再使用预定义列表

    # 配置集合前缀
    CONFIG_PREFIX = "config."

    # 模板集合的名称后缀
    TEMPLATE_COLLECTION_POSTFIX = ".template"
    
    def __init__(self, repo_root: Union[Path, PurePosixPath, str], vfs: VFSClient):
        """
        Args:
            repo_root: Path to the repository root
            vfs: VFS client for file operations
        """
        # 默认为 repo_root 路径下的 .config 子目录
        
        if isinstance(repo_root, str):
            self._repo_root = PurePosixPath(repo_root)
        elif isinstance(repo_root, Path):
            self._repo_root = PurePosixPath(repo_root.as_posix())
        else:
            self._repo_root = repo_root
        
        self._vfs = vfs
        # self._config_root = self._repo_root / ".config"
        self._config_collections: Dict[str, ConfigCollectionImpl[T]] = {}
        self._template_collections: Dict[str, ConfigTemplateCollectionImpl[T]] = {}
        self._prefix_to_collection = {}
        self._prefix_list = []
    
    def _get_config_source_dir(self, collection_name: str) -> Optional[Path]:
        """Get the source directory for configuration files.
        
        Args:
            collection_name: Name of the collection (e.g., 'config.agent')
            
        Returns:
            Path to the source directory or None if not found
        """
        # Extract the config type from collection name
        # e.g., 'config.agent' -> 'agent'
        parts = collection_name.split('.', 1)
        if len(parts) != 2:
            return None
        
        config_type = parts[1]
        if config_type.endswith(self.TEMPLATE_COLLECTION_POSTFIX):
            config_type = config_type[:-1*len(self.TEMPLATE_COLLECTION_POSTFIX)]

        # Get the package directory (similar to get_template_source_dir)
        current_file = Path(__file__)
        package_dir = current_file.parent.parent.parent
        
        # Config files are stored in src/data/config/{config_type}
        config_source_dir = package_dir / "data" / "config" / config_type
        
        if config_source_dir.exists() and config_source_dir.is_dir():
            return config_source_dir
        
        return None
    
    def _copy_config_files_to_vfs(self, collection_name: str, target_path: PurePosixPath) -> bool:
        """Copy configuration files from source to VFS.
        
        Args:
            collection_name: Name of the collection
            target_path: Target path in VFS
            
        Returns:
            True if successful, False otherwise
        """
        source_dir = self._get_config_source_dir(collection_name)
        if not source_dir:
            return False
        
        try:
            # Copy all files from source directory to VFS
            copied = 0
            for source_file in source_dir.iterdir():
                if source_file.is_file():
                    target_file_path = target_path / source_file.name
                    
                    # Check if file already exists in VFS
                    if not self._vfs.info(str(target_file_path)):
                        # Read source file content
                        with open(source_file, 'rb') as f:
                            content = f.read()
                        
                        # Write to VFS
                        self._vfs.put(str(target_file_path), content, create_if_missing=True)
                        copied += 1
            
            return copied > 0
        except Exception:
            return False
    
    def get_collection(self, name: str) -> Optional[ResourceCollection[T]]:
        """
        Args:
            name: Collection name
            
        Returns:
            Collection or None if not found
        """
        # 检查是否是配置集合
        if name.startswith("config."):
            return self._get_config_collection(name)
        
        # 否则返回 None，因为这个管理器只处理配置集合
        return None
    
    def parse_resource_reference(self, reference: str, partial: bool = False) -> Tuple[Optional[ResourceCollection[T]], Optional[ResourceItem[T]]]:
        """Parse a reference to a resource item.
        
        Args:
            reference: Reference string
            partial: Whether to allow partial matching of item names
            
        Returns:
            Tuple of (collection, item) or (collection, None) if only collection found
            or (None, None) if reference is invalid
        """
        # 只处理 config.* 命名空间的引用
        if not reference or not reference.startswith("config."):
            return None, None
        
        return self.parse_config_reference(reference, partial)
    
    def _get_config_collection(self, name: str) -> Optional[ConfigCollectionImpl[T]]:
        """Get or create a configuration collection.
        
        Args:
            name: Collection name (must start with "config.")
            
        Returns:
            Configuration collection or None if not a valid config collection name
        """
        # 处理 .template 后缀
        collection_name = name if not name.endswith(self.TEMPLATE_COLLECTION_POSTFIX) else name[:-1*len(self.TEMPLATE_COLLECTION_POSTFIX)]

        if collection_name in self._config_collections:
            return self._config_collections[collection_name]
        
        # 根据数据文件判断是否是有效的配置集合
        source_dir = self._get_config_source_dir(name)
        if not source_dir:      # 配置项目没有预制模板，不认为是有效的
            return None

        # 映射到 .config 目录
        # 例如 config.agent -> .config/agent
        parts = collection_name.split(".", 1)
        if len(parts) != 2:
            return None
        
        config_path = self._repo_root / parts[1]
        
        # 确保目录存在
        try:
            if not self._vfs.info(config_path):     # 如果不存在或其他错误（gitfs) , info 返回 None
                self._vfs.mkdir(config_path, parents=True)
                # 复制默认配置文件到新创建的目录, 使用 collection_name 也可也
                self._copy_config_files_to_vfs(name, config_path)
        except Exception as e:
            # 如果创建目录失败，仍然返回集合对象，但操作可能会失败
            raise ValueError(f"Failed to create config collection directory: {config_path}")
        
        # 创建集合
        collection = ConfigCollectionImpl[T](collection_name, config_path, self._vfs)
        self._config_collections[collection_name] = collection
        if collection_name == name:
            return collection
        else:
            return collection.template_collection
    
    def _is_valid_config_collection(self, name: str) -> bool:
        """Check if a name is a valid configuration collection name.
        
        Args:
            name: Collection name to check
            
        Returns:
            True if the name is valid, False otherwise
        """
        if not name.startswith("config."):
            return False
        
        parts = name.split(".")
        if len(parts) != 2:
            return False
        
        # 检查目录是否存在
        config_path = self._config_root / parts[1]
        try:
            info = self._vfs.info(str(config_path))
            return info is not None
        except Exception:
            return False
    
    def parse_config_reference(self, reference: str, partial: bool = False) -> Tuple[Optional[ConfigCollectionImpl[T]], Optional[ResourceItem[T]]]:
        """Parse a reference to a configuration item.
        
        Args:
            reference: Reference string (e.g., "config.provider.openai")
            partial: Whether to allow partial matching of item names
            
        Returns:
            Tuple of (collection, item) or (collection, None) if only collection found
            or (None, None) if reference is invalid
        """
        if not reference or not reference.startswith("config."):
            return None, None
        
        parts = reference.split(".")
        if len(parts) < 2:
            return None, None
        
        # 处理 config.collection.item 格式
        if len(parts) >= 3:
            collection_name = f"{parts[0]}.{parts[1]}"
            item_name = parts[2]
            
            collection = self._get_config_collection(collection_name)
            if not collection:
                return None, None
            
            if partial:
                # 支持部分匹配
                item_names = sorted(collection.list_items())
                for existing_item_name in item_names:
                    if existing_item_name.startswith(item_name):
                        item = collection.get_item(existing_item_name)
                        if item:
                            return collection, item
            else:
                # 精确匹配
                item = collection.get_item(item_name)
                return collection, item
        
        # 处理 config.collection 格式
        collection_name = reference
        collection = self._get_config_collection(collection_name)
        return collection, None
    
    @property
    def root_collection(self) -> ResourceCollection[T]:
        """Get the default collection for operations.
        
        Returns:
            The default collection instance
        """
        # 配置集合没有真正的根集合，返回一个预定义的配置集合
        return self._get_config_collection("config.agent")
    
    def create_collection(self, name: str, parent: Optional[ResourceCollection[T]] = None) -> ResourceCollection[T]:
        raise ValueError("Config collections do not support create collection")
    
    def remove_collection(self, name: str, parent: Optional[ResourceCollection[T]] = None) -> Optional[ResourceCollection[T]]:
        """Remove a collection.
        
        Args:
            name: Name of the collection to remove
            parent: Optional parent collection. If None, removes from root level
            
        Returns:
            The removed collection, or None if not found
        """
        raise ValueError("Config collections do not support remove collection")
    
    def add_collection(self, collection: ResourceCollection[T], parent: Optional[ResourceCollection[T]] = None) -> None:
        """Add an existing collection to a parent.
        
        Args:
            collection: Collection to add
            parent: Optional parent collection. If None, adds to root level
            
        Raises:
            ValueError: If a collection with the same name already exists in the parent
        """
        raise ValueError("Config collections do not support add collection")
    
    def move_collection(self, name: str, 
                       from_parent: Optional[ResourceCollection[T]] = None,
                       to_parent: Optional[ResourceCollection[T]] = None) -> bool:
        """Move a collection from one parent to another.
        
        Args:
            name: Name of the collection to move
            from_parent: Source parent collection. If None, moves from root
            to_parent: Target parent collection. If None, moves to root
            
        Returns:
            True if the collection was moved successfully, False otherwise
        """
        # 配置集合不支持父集合，所以不支持移动
        return False
    
    def list_collections(self, parent: Optional[ResourceCollection[T]] = None) -> List[str]:
        """List collection names under a parent.
        
        Args:
            parent: Optional parent collection. If None, lists root-level collections
            
        Returns:
            List of collection names
        """
        if parent is not None:
            return []  # 配置集合不支持父集合
        
        return self.list_config_collections()
    
    def iter_all_collections(self, include_root: bool = True) -> Iterator[ResourceCollection[T]]:
        """Iterate over all collections in the hierarchy.
        
        Args:
            include_root: Whether to include the root collection in iteration
            
        Returns:
            Iterator over all collections in the hierarchy
        """
        for name in self.list_config_collections():
            collection = self._get_config_collection(name)
            if collection:
                yield collection
    
    def find_collection_path(self, collection: ResourceCollection[T]) -> List[str]:
        """Find the path from root to a specific collection.
        
        Args:
            collection: Collection to find path for
            
        Returns:
            List of collection names representing the path from root
        """
        # 配置集合没有层次结构，所以路径就是集合名称本身
        if collection.name.startswith("config."):
            return [collection.name]
        return []
    
    def list_config_collections(self) -> List[str]:
        """List all available configuration collections.
        
        Returns:
            List of configuration collection names
        """
        result = []
        
        # 基于数据目录动态发现配置集合
        try:
            # 获取数据目录路径
            current_file = Path(__file__)
            package_dir = current_file.parent.parent.parent
            data_config_dir = package_dir / "data" / "config"
            
            if data_config_dir.exists() and data_config_dir.is_dir():
                # 遍历数据目录下的子目录
                for item in data_config_dir.iterdir():
                    if item.is_dir():
                        config_name = f"config.{item.name}"
                        result.append(config_name)
        except Exception:
            pass
        
        # 添加动态发现的集合（从repo_root）
        try:
            info = self._vfs.info(str(self._repo_root))
            if info is not None:
                dirs = self._vfs.list_dirs(str(self._repo_root))
                for dir_name in dirs:
                    config_name = f"config.{dir_name}"
                    if config_name not in result:
                        result.append(config_name)
        except Exception:
            pass
        
        return sorted(result)
    
    def list_available_templates(self, collection_name: str) -> Dict[str, str]:
        """List available templates for a configuration collection.
        
        Args:
            collection_name: Configuration collection name
            
        Returns:
            Dictionary mapping template names to template descriptions
        """
        result = {}
        
        collection = self._get_config_collection(collection_name)
        if not collection:
            return result
        
        template_collection = collection.template_collection
        template_names = template_collection.list_items()
        
        for template_name in template_names:
            template_item = template_collection.get_item(template_name)
            if template_item:
                # 尝试从模板内容中提取描述
                try:
                    content = template_item.content
                    yaml_data = yaml.safe_load(content)
                    description = yaml_data.get('description', 'No description')
                except Exception:
                    description = 'No description'
                
                result[template_name] = description
        
        return result
