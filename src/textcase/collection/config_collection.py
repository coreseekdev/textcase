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
"""Configuration collection implementation."""

import os
import re
from jinja2.runtime import str_join
import yaml
import jinja2
import jinja2.meta
from pathlib import Path, PurePosixPath
from typing import Dict, Any, Optional, List, TypeVar, Generic, Union, Iterator, Set

from ..client import VFSClient, VFSClientException
from ..proto.resource_collection_protocol import ResourceCollection, ResourceItem
from .collection import ResourceCollectionImpl
from ..proto.service_vfs_protocol import EntryType

T = TypeVar('T')


class ConfigItemImpl(Generic[T], ResourceItem[T]):
    """Implementation of a configuration item."""
    
    def __init__(self, name: str, collection: 'ConfigCollectionImpl', vfs: VFSClient):
        """Initialize a configuration item.
        
        Args:
            name: Name of the configuration item
            collection: Parent collection
            vfs: VFS client for file operations
        """
        self._name = name
        self._collection = collection
        self._vfs = vfs
        self._content = None
        self._tags = set()  # Empty tags set - not supported for config items
    
    @property
    def name(self) -> str:
        """Get the name of this item."""
        return self._name
    
    @property
    def content(self) -> Optional[str_join]:
        """Get the configuration content for this item."""
        return self._load_content()

    def as_yaml(self, variables: Optional[Dict[str, Any]] = None, use_env: bool = True) -> Optional[Dict[str, Any]]:
        try:
            render_context = self.render(variables, use_env)
            return yaml.safe_load(render_context)
        except yaml.YAMLError as exc:
            return None

    def _load_content(self) -> None:
        """Load configuration content from file."""
        try:
            file_path = self.get_file_path()
            content = self._vfs.get_text(str(file_path), encoding='utf-8')
        except Exception as e:
            raise VFSClientException(
                'ConfigLoadError',
                f'Failed to load configuration from {file_path}: {e}'
            )
        return content
    
    def get_file_path(self) -> PurePosixPath:
        """Get the file path for this configuration item."""
        extension = self._collection.get_default_extension()
        return self._collection.path / f"{self._name}{extension}"
    
    def _process_env_vars(self, data: Any, path: str = '') -> None:
        """Process environment variable substitutions in configuration data.
        
        Args:
            data: Configuration data to process
            path: Current path in the configuration (for error reporting)
        """
        if isinstance(data, dict):
            for key, value in data.items():
                new_path = f"{path}.{key}" if path else key
                if isinstance(value, (dict, list)):
                    self._process_env_vars(value, new_path)
                elif isinstance(value, str):
                    data[key] = self._replace_env_vars(value, new_path)
        elif isinstance(data, list):
            for i, item in enumerate(data):
                new_path = f"{path}[{i}]"
                if isinstance(item, (dict, list)):
                    self._process_env_vars(item, new_path)
                elif isinstance(item, str):
                    data[i] = self._replace_env_vars(item, new_path)
    
    def _replace_env_vars(self, value: str, path: str) -> str:
        """Replace environment variables in a string.
        
        Args:
            value: String value to process
            path: Path in the configuration (for error reporting)
            
        Returns:
            String with environment variables replaced
        """
        pattern = r'\{\{\s*([^}]+)\s*\}\}'
        matches = re.findall(pattern, value)
        
        result = value
        for match in matches:
            env_var = match.strip()
            env_value = os.environ.get(env_var)
            if env_value is None:
                # Just leave the placeholder if environment variable is not set
                continue
            
            # Replace the placeholder with the environment variable value
            placeholder = f"{{{{{match}}}}}"
            result = result.replace(placeholder, env_value)
        
        return result
    
    def render(self, variables: Optional[Dict[str, Any]] = None, use_env: bool = True) -> Optional[str]:
        """Render the configuration file as a Jinja2 template.
        
        Args:
            variables: Dictionary of variables to substitute in the template.
                      These variables have priority over environment variables.
            use_env: Whether to read variables from environment variables.
                    Defaults to True.
            
        Returns:
            Rendered template content
            
        Raises:
            VFSClientException: If template parsing or rendering fails
        """
        try:
            # Read the template content
            # file_path = self._get_file_path()
            template_content = self.content
            if template_content is None:
                return None
            
            # Create Jinja2 environment
            env = jinja2.Environment(
                 undefined=jinja2.StrictUndefined,
             )
            
            # Parse the template to find all variables
            try:
                ast = env.parse(template_content)
                template_vars = jinja2.meta.find_undeclared_variables(ast)
            except Exception as e:
                raise VFSClientException(
                    'TemplateParseError',
                    f'Error parsing template {file_path}: {e}'
                )
            
            # Create render context
            render_context = {}
            
            # Populate variables from environment variables if use_env is True
            if use_env:
                for var in template_vars:
                    value = None
                    
                    # 首先尝试全大写匹配
                    upper_var = var.upper()
                    if upper_var in os.environ:
                        value = os.environ[upper_var]
                    else:
                        # 不区分大小写匹配
                        for env_key, env_value in os.environ.items():
                            if env_key.upper() == upper_var:
                                value = env_value
                                break
                    
                    if value is not None:
                        render_context[var] = value
            
            # Override with manually provided variables (higher priority)
            if variables:
                render_context.update(variables)
            
            # Render the template
            try:
                template = env.from_string(template_content)
                rendered_content = template.render(**render_context)
                return rendered_content
                
            except jinja2.exceptions.UndefinedError as e:
                raise VFSClientException(
                    'TemplateRenderError',
                    f'Template variable not found: {e}. Available variables: {", ".join(template_vars)}'
                )
            except Exception as e:
                raise VFSClientException(
                    'TemplateRenderError',
                    f'Error rendering template {file_path}: {e}'
                )
                
        except VFSClientException:
            raise
        except Exception as e:
            raise VFSClientException(
                'ConfigRenderError',
                f'Failed to render configuration {file_path}: {e}'
            )
        return None
    
    def check_availability(self, variables: Optional[Dict[str, Any]] = None, use_env: bool = True) -> tuple[bool, float, Optional[str]]:
        """Check if the configuration is available (all required variables are provided).
        
        Args:
            variables: Dictionary of variables to substitute in the template.
                      These variables have priority over environment variables.
            use_env: Whether to read variables from environment variables.
                    Defaults to True.
            
        Returns:
            Tuple of (is_available, availability_score, error_message)
            - is_available: True if all required variables are available
            - availability_score: Float between 0.0 and 1.0 indicating partial availability
            - error_message: Error message if not available, None otherwise
        """
        try:
            # Read the template content
            # file_path = self._get_file_path()
            template_content = self.content
            if template_content is None:
                return False, 0.0, 'Template content is None'
            
            # Create Jinja2 environment
            env = jinja2.Environment(
                 undefined=jinja2.StrictUndefined,
             )
            
            # Parse the template to find all variables
            try:
                ast = env.parse(template_content)
                template_vars = jinja2.meta.find_undeclared_variables(ast)
            except Exception as e:
                return False, 0.0, f'Template parsing error: {e}'
            
            if not template_vars:
                # No template variables, always available
                return True, 1.0, None
            
            # Create render context
            render_context = {}
            available_vars = set()
            
            # Populate variables from environment variables if use_env is True
            if use_env:
                for var in template_vars:
                    value = None
                    
                    # 首先尝试全大写匹配
                    upper_var = var.upper()
                    if upper_var in os.environ:
                        value = os.environ[upper_var]
                    else:
                        # 不区分大小写匹配
                        for env_key, env_value in os.environ.items():
                            if env_key.upper() == upper_var:
                                value = env_value
                                break
                    
                    if value is not None:
                        render_context[var] = value
                        available_vars.add(var)
            
            # Override with manually provided variables (higher priority)
            if variables:
                for var, value in variables.items():
                    if var in template_vars:
                        render_context[var] = value
                        available_vars.add(var)
            
            # Calculate availability score
            total_vars = len(template_vars)
            available_count = len(available_vars)
            availability_score = available_count / total_vars if total_vars > 0 else 1.0
            
            # Check if all variables are available
            missing_vars = template_vars - available_vars
            if missing_vars:
                error_msg = f'Missing required variables: {", ".join(sorted(missing_vars))}'
                return False, availability_score, error_msg
            
            # Try to render to make sure everything works
            try:
                template = env.from_string(template_content)
                template.render(**render_context)
                return True, 1.0, None
            except Exception as e:
                return False, availability_score, f'Rendering error: {e}'
                
        except Exception as e:
            return False, 0.0, f'Configuration check error: {e}'
    
    def save(self, content= "") -> None:
        """Save configuration data to file."""
        if content is None:
            content= ""

        try:
            file_path = self.get_file_path()
            self._vfs.put(str(file_path), content.encode('utf-8'), create_if_missing=True)
        except Exception as e:
            raise VFSClientException(
                'ConfigSaveError',
                f'Failed to save configuration to {file_path}: {e}'
            )

    # Tag operations - not supported for config items
    def assign_tag(self, tag: str) -> None:
        """Config items do not support tags."""
        raise NotImplementedError("Config items do not support tags")
    
    def unassign_tag(self, tag: str) -> None:
        """Config items do not support tags."""
        raise NotImplementedError("Config items do not support tags")
    
    def has_tag(self, tag: str) -> bool:
        """Config items do not support tags."""
        return False
    
    @property
    def tags(self) -> List[str]:
        """Config items do not support tags."""
        return []


class ConfigTemplateItemImpl(Generic[T], ResourceItem[T]):
    """Implementation of a configuration template item."""
    
    def __init__(self, name: str, collection: ResourceCollection[T], vfs: VFSClient = None):
        """Initialize a configuration template item.
        
        Args:
            name: Name of the item
            collection: Collection this item belongs to
            vfs: VFS client for file operations
        """
        self._name = name
        self._collection = collection
        self._vfs = vfs
    
    @property
    def name(self) -> str:
        """Get the name of this item."""
        return self._name
    
    @property
    def collection(self) -> ResourceCollection[T]:
        """Get the collection this item belongs to."""
        return self._collection
    
    @property
    def template_file(self) -> Optional[str]:
        """Find the template file for this item.
        
        Returns:
            Path to the template file or None if not found
        """
        # 不能使用 with suffix ，改为操作字符串
        return self._collection.path / f"{self._name}.tmpl"
    
    def read_content(self) -> str:
        """Read the content of this template item.
        
        Returns:
            Content of the template item
        """
        # 查找并读取模板文件
        file_path = self.template_file
        if not file_path:
            raise ValueError(f"Template file for '{self._name}' not found")
        
        try:
            content = self._vfs.get(file_path)
            if isinstance(content, bytes):
                content = content.decode('utf-8')
            return content
        except Exception as e:
            raise ValueError(f"Failed to read template content: {e}")
    
    def write_content(self, content: str) -> None:
        """Write content to this template item.
        
        Args:
            content: Content to write
        """
        # Template items are read-only, so this method is not implemented
        raise NotImplementedError("Template items are read-only")
    
    @property
    def tags(self) -> Set[str]:
        """Get the tags assigned to this item.
        
        Template items don't support tags.
        
        Returns:
            Empty set as template items don't have tags
        """
        return set()
    
    def assign_tag(self, tag: str) -> None:
        """Assign a tag to this item.
        
        Template items don't support tags.
        
        Args:
            tag: Tag name to assign
        """
        raise NotImplementedError("Template items don't support tags")
    
    def unassign_tag(self, tag: str) -> None:
        """Remove a tag from this item.
        
        Template items don't support tags.
        
        Args:
            tag: Tag name to remove
        """
        raise NotImplementedError("Template items don't support tags")
    
    def has_tag(self, tag: str) -> bool:
        """Check if this item has a specific tag.

        Template items don't support tags.

        Args:
            tag: Tag name to check
            
        Returns:
            False as template items don't have tags
        """
        return False
    
    def render(self, variables: Dict[str, str] = None) -> str:
        """Render the template with the given variables.
        
        Args:
            variables: Dictionary of variables to substitute in the template
            
        Returns:
            Rendered template content
        """
        content = self.read_content()
        
        if variables:
            # Simple variable substitution using string replacement
            # Variables are expected to be in the format {{variable_name}}
            for key, value in variables.items():
                placeholder = f"{{{{{key}}}}}"
                content = content.replace(placeholder, value)
        
        return content
    
    def get_extension(self) -> str:
        """Get the extension of this item.
        
        Returns:
            Extension of the item (without the .tmpl suffix)
        """
        file_path = self.template_file
        if not file_path:
            return ""
        
        # 从文件名中提取扩展名（不包括 .tmpl）
        filename = os.path.basename(file_path)
        parts = filename.split('.')
        if len(parts) > 2:  # 至少有 name.ext.tmpl
            return '.'.join(parts[1:-1])  # 返回中间的扩展名部分
        return ""


class AbstractConfigCollection(Generic[T], ResourceCollection[T]):
    """Abstract base class for configuration collections."""
    
    def __init__(self, name: str, path: PurePosixPath, vfs: VFSClient):
        """Initialize a configuration collection.
        
        Args:
            name: Name of the collection
            path: Path to the collection directory
            vfs: VFS client for file operations
        """
        self._name = name
        self._path = path
        self._vfs = vfs
        self._items = {}  # Cache of items
        self._tags = set()  # 集合不支持标签，但需要实现接口
    
    @property
    def name(self) -> str:
        """Get the name of this collection."""
        return self._name
    
    @property
    def path(self) -> PurePosixPath:
        """Get the path to this collection."""
        return self._path
    
    def get_item_key(self, item_id: str) -> str:
        """Get the key for an item.
        
        Args:
            item_id: Item ID
            
        Returns:
            Item key
        """
        return item_id
    
    @property
    def item_names(self) -> List[str]:
        """Get all item names.
        
        Returns:
            List of item names
        """
        return self.list_items()
    
    def iter_items(self) -> Iterator[ResourceItem[T]]:
        """Iterate over all items.
        
        Returns:
            Iterator of items
        """
        for name in self.list_items():
            item = self.get_item(name)
            if item:
                yield item
    
    def size(self) -> int:
        """Get the number of items in this collection.
        
        Returns:
            Number of items
        """
        return len(self.list_items())
    
    def is_empty(self) -> bool:
        """Check if this collection is empty.
        
        Returns:
            True if empty, False otherwise
        """
        return self.size() == 0
    
    def clear(self) -> None:
        """Clear this collection."""
        # 删除所有项目
        for name in self.list_items():
            self.remove_item(name)
        
        # 清空缓存
        self._items = {}
    
    # 以下方法与标签相关，配置集合不支持标签，但需要实现接口
    
    def add_tag(self, tag: str) -> None:
        """Add a tag to this collection.
        
        Args:
            tag: Tag to add
        """
        raise NotImplementedError("Configuration collections do not support tags")
    
    def remove_tag(self, tag: str) -> None:
        """Remove a tag from this collection.
        
        Args:
            tag: Tag to remove
        """
        raise NotImplementedError("Configuration collections do not support tags")
    
    def has_tag(self, tag: str) -> bool:
        """Check if this collection has a tag.
        
        Args:
            tag: Tag to check
            
        Returns:
            True if the collection has the tag, False otherwise
        """
        return False
    
    def tags(self) -> List[str]:
        """Get all tags for this collection.
        
        Returns:
            List of tags
        """
        return []
    
    def get_items_by_tag(self, tag: str) -> List[ResourceItem[T]]:
        """Get all items with a specific tag.
        
        Args:
            tag: Tag to filter by
            
        Returns:
            List of items with the tag
        """
        return []
    
    def get_items_by_tags(self, tags: List[str], match_all: bool = False) -> List[ResourceItem[T]]:
        """Get all items with specific tags.
        
        Args:
            tags: Tags to filter by
            match_all: If True, items must have all tags; if False, items must have any tag
            
        Returns:
            List of items with the tags
        """
        return []
    
    def get_available_tags(self) -> List[str]:
        """Get all available tags in this collection.
        
        Returns:
            List of tags
        """
        return []
    
    # 以下方法与子集合相关，配置集合不支持子集合，但需要实现接口
    
    def add_collection(self, name: str, path: Optional[PurePosixPath] = None) -> ResourceCollection[T]:
        """Add a child collection.
        
        Args:
            name: Name of the collection
            path: Path to the collection directory
            
        Returns:
            The created collection
        """
        raise NotImplementedError("Configuration collections do not support child collections")
    
    def get_collection(self, name: str) -> Optional[ResourceCollection[T]]:
        """Get a child collection by name.
        
        Args:
            name: Name of the collection
            
        Returns:
            The collection if found, None otherwise
        """
        return None
    
    def has_collection(self, name: str) -> bool:
        """Check if a child collection exists.
        
        Args:
            name: Name of the collection
            
        Returns:
            True if the collection exists, False otherwise
        """
        return False
    
    def remove_collection(self, name: str) -> bool:
        """Remove a child collection.
        
        Args:
            name: Name of the collection
            
        Returns:
            True if the collection was removed, False otherwise
        """
        return False
    
    def collections(self) -> List[ResourceCollection[T]]:
        """Get all child collections.
        
        Returns:
            List of child collections
        """
        return []
    
    def get_child_collection(self, name: str) -> Optional[ResourceCollection[T]]:
        """Configuration collections do not support child collections."""
        return None
    
    def list_child_collections(self) -> List[str]:
        """Configuration collections do not support child collections."""
        return []
    
    # Tag operations - not supported for configuration collections
    def assign_tag(self, item_name: str, tag: str) -> None:
        """Configuration collections do not support tags."""
        raise NotImplementedError("Configuration collections do not support tags")
    
    def unassign_tag(self, item_name: str, tag: str) -> None:
        """Configuration collections do not support tags."""
        raise NotImplementedError("Configuration collections do not support tags")
    

    
    # 抽象方法，需要子类实现
    def get_next_item_name(self) -> str:
        """Get the next available item name.
        
        Returns:
            Next available item name
        """
        raise NotImplementedError("Subclasses must implement get_next_item_name")
    
    def add_item(self, name: str, content: str = "") -> ResourceItem[T]:
        """Add a new item.
        
        Args:
            name: Name of the item
            content: Initial content for the item
            
        Returns:
            The created item
        """
        raise NotImplementedError("Subclasses must implement add_item")
    
    def get_item(self, name: str) -> Optional[ResourceItem[T]]:
        """Get an item by name.
        
        Args:
            name: Name of the item
            
        Returns:
            The item if found, None otherwise
        """
        raise NotImplementedError("Subclasses must implement get_item")
    
    def has_item(self, name: str) -> bool:
        """Check if an item exists.
        
        Args:
            name: Name of the item
            
        Returns:
            True if the item exists, False otherwise
        """
        raise NotImplementedError("Subclasses must implement has_item")
    
    def remove_item(self, name: str) -> bool:
        """Remove an item.
        
        Args:
            name: Name of the item
            
        Returns:
            True if the item was removed, False otherwise
        """
        raise NotImplementedError("Subclasses must implement remove_item")
    
    def list_items(self) -> List[str]:
        """List all items.
        
        Returns:
            List of item names
        """
        raise NotImplementedError("Subclasses must implement list_items")


class ConfigTemplateCollectionImpl(AbstractConfigCollection[T]):
    """Implementation of a configuration template collection."""
    
    def get_next_item_name(self) -> str:
        """Get the next available item name.
        
        Returns:
            Next available item name
        """
        raise ValueError("Config template collections do not support get next item name")
    
    def add_item(self, name: str, content: str = "") -> ResourceItem[T]:
        """Add a new template item.
        
        Args:
            name: Name of the item
            content: Initial content for the item
            
        Returns:
            The created item
        """
        raise ValueError("Config template collections do not support add item")
    
    def get_item(self, name: str) -> Optional[ResourceItem[T]]:
        """Get a template item by name.
        
        Args:
            name: Name of the item
            
        Returns:
            The item if found, None otherwise
        """
        # 使用 list_items 检查模板是否存在
        if name in self.list_items():
            return ConfigTemplateItemImpl[T](name, self, self._vfs)
        return None
    
    def has_item(self, name: str) -> bool:
        """Check if a template item exists.
        
        Args:
            name: Name of the item
            
        Returns:
            True if the item exists, False otherwise
        """
        # 直接使用 list_items 检查模板是否存在
        return name in self.list_items()
    
    def remove_item(self, name: str) -> bool:
        """Remove a template item.
        
        Args:
            name: Name of the item
            
        Returns:
            True if the item was removed, False otherwise
        """
        raise ValueError("Config template collections do not support remove item")
    
    def list_items(self) -> List[str]:
        """List all template items.
        
        Returns:
            List of item names
        """
        # 列出目录中的所有 .tmpl 文件
        try:
            files = self._vfs.list(str(self._path))
            items = []
            for file, entry_type in files:
                if entry_type == EntryType.DIR:
                    continue
                file_path = PurePosixPath(file)
                if file_path.suffix.lower() == ".tmpl":
                    # 去掉扩展名，这样返回的名称可用直接定位到具体文件
                    template_name = file_path.stem
                    items.append(template_name)
            return items
        except Exception:
            return []
    
class ConfigCollectionImpl(AbstractConfigCollection[T]):
    """Implementation of a configuration collection."""
    
    def __init__(self, name: str, path: PurePosixPath, vfs: VFSClient):
        """Initialize a configuration collection.
        
        Args:
            name: Name of the collection
            path: Path to the collection directory
            vfs: VFS client for file operations
        """
        super().__init__(name, path, vfs)
        self._template_collection = None  # Lazy initialized
        self._config = None  # Collection configuration
        self._default_template_name = None  # Lazy initialized
        self._default_extension = None  # Lazy initialized
        
    def get_next_item_name(self) -> str:
        """Get the next available item name.
        
        Returns:
            Next available item name
        """
        # 配置项使用 default 作为默认名称
        if not self.has_item("default"):
            return "default"
        
        # 如果 default 已存在，使用数字后缀
        i = 1
        while self.has_item(f"config_{i}"):
            i += 1
        return f"config_{i}"
    
    def add_item(self, name: str, content: str = "") -> ResourceItem[T]:
        """Add a new configuration item.
        
        Args:
            name: Name of the item
            content: Initial content for the item
            
        Returns:
            The created item
        """
        if self.has_item(name):
            raise ValueError(f"Item '{name}' already exists")
        
        # 创建配置项
        item = ConfigItemImpl[T](name, self, self._vfs)
        self._items[name] = item
        
        # 如果提供了内容，立即写入
        if content:
            extension = self.get_default_extension()
            file_path = self._path / f"{name}{extension}"
            self._vfs.put(str(file_path), content.encode('utf-8'), create_if_missing=True)
        
        return item
    
    def get_item(self, name: str) -> Optional[ResourceItem[T]]:
        """Get a configuration item by name.
        
        Args:
            name: Name of the item
            
        Returns:
            The item if found, None otherwise
        """
        # 如果已缓存，直接返回
        if name in self._items:
            return self._items[name]
        
        # 检查文件是否存在
        extension = self.get_default_extension()
        file_path = self._path / f"{name}{extension}"
        info = self._vfs.info(str(file_path))
        if info is None:
            return None
        
        # 创建配置项
        item = ConfigItemImpl[T](name, self, self._vfs)
        self._items[name] = item
        return item
    
    def has_item(self, name: str) -> bool:
        """Check if a configuration item exists.
        
        Args:
            name: Name of the item
            
        Returns:
            True if the item exists, False otherwise
        """
        if name in self._items:
            return True
        
        # 检查文件是否存在
        extension = self.get_default_extension()
        file_path = self._path / f"{name}{extension}"
        info = self._vfs.info(str(file_path))
        return info is not None
    
    def remove_item(self, name: str) -> bool:
        """Remove a configuration item.
        
        Args:
            name: Name of the item
            
        Returns:
            True if the item was removed, False otherwise
        """
        # 如果已缓存，移除缓存
        if name in self._items:
            del self._items[name]
        
        # 删除文件
        extension = self.get_default_extension()
        file_path = self._path / f"{name}{extension}"
        info = self._vfs.info(str(file_path))
        if info is not None:
            self._vfs.remove(str(file_path))
            return True
        
        return False
    
    def list_items(self) -> List[str]:
        """List all configuration items.
        
        Returns:
            List of item names
        """
        # 列出目录中的所有配置文件
        try:
            extension = self.get_default_extension()
            files = self._vfs.list(str(self._path))
            items = []
            extension = self.get_default_extension()
            for file, entry_type in files:
                if entry_type == EntryType.DIR:
                    continue

                if file.suffix == extension:
                    items.append(file.stem)  # 移除扩展名后缀
            return items
        except Exception as e:
            return []
    
    @property
    def config(self) -> Optional[Dict[str, Any]]:
        """Get the collection configuration."""
        return self._config
    
    @property
    def template_collection(self) -> ConfigTemplateCollectionImpl[T]:
        """Get the template collection for this config collection."""
        if self._template_collection is None:
            template_path = self._path  # template 的数据路径与当前集合的相同
            self._template_collection = ConfigTemplateCollectionImpl(
                f"{self._name}.template", 
                template_path, 
                self._vfs
            )
        return self._template_collection
    
    def get_default_template_name(self) -> Optional[str]:
        """Get the default template name for this collection.
        
        Returns:
            Default template name if found, None otherwise
        """
        if self._default_template_name is None:
            # 查找默认模板，优先级：default > 第一个可用模板
            template_names = self.template_collection.list_items()
            if not template_names:
                self._default_template_name = None
                raise ValueError("No template found in collection")
            for name in template_names:
                if name.startswith("default"):
                    # 不应该是 default. 因为有可能没有扩展名
                    self._default_template_name = name
                    break
            if self._default_template_name is None:
                # 使用第一个可用模板作为默认模板
                self._default_template_name = template_names[0]
        return self._default_template_name
    
    def get_default_extension(self) -> str:
        """Get the default file extension for items in this collection.
        
        Returns:
            Default file extension (e.g., '.yml', '.md')
        """
        default_template_name = self.get_default_template_name()
        default_extension = '.'.join(PurePosixPath(default_template_name).suffixes)
        return default_extension
    
    def create_from_template(self, item_name: str, template_name: str, variables: Dict[str, str] = None) -> ResourceItem[T]:
        """Create a new configuration item from a template.
        
        Args:
            item_name: Name of the new configuration item
            template_name: Name of the template to use
            variables: Dictionary of variables to substitute in the template (unused, kept for compatibility)
            
        Returns:
            Configuration item (existing or newly created)
            
        Raises:
            VFSClientException: If the template does not exist
        """
        # Check if the item already exists
        existing_item = self.get_item(item_name)
        if existing_item:
            return existing_item
        
        # Get the template
        template_item = self.template_collection.get_item(template_name)
        if not template_item:
            raise VFSClientException(
                'ConfigCreateError',
                f'Template {template_name} does not exist'
            )
        
        # Copy template content directly without variable substitution
        content = template_item.read_content()
        
        # Use add_item to create the new item with proper extension handling
        return self.add_item(item_name, content)
