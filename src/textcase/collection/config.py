"""Collection Configuration Implementation

This module provides YAML-based configuration management for collections,
similar to the original module_config.py implementation.
"""

from ast import Tuple
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath
from typing import Any, Dict, Optional, Union, Tuple

import yaml

from ..client.vfs_client import VFSClient, VFSClientException
from ..proto.resource_collection_protocol import InvalidCollectionError


@dataclass
class CollectionConfig:
    """YAML-based configuration for resource collections.
    
    This implementation stores configuration in a YAML file at `.textcase.yml`
    within the collection directory, following the same pattern as module_config.
    """

    path: Union[Path, PurePosixPath]
    """The filesystem path of the collection."""
    
    CONFIG_FILENAME: str = '.textcase.yml'
    """The name of the configuration file within the collection directory."""
    
    name: str = ""
    """The name of the collection."""
    
    prefix: str = ""
    """The prefix for items in this collection (e.g., 'REQ', 'TST')."""
    
    num: int = 3
    """Number of digits for item numbering."""
    
    sep: str = ""
    """Separator between prefix and number."""
    
    suffix: str = ""
    """Suffix for item files."""
    
    tags: Dict[str, str] = field(default_factory=dict)
    """Collection tags as key-description pairs."""
    
    settings: Dict[str, Any] = field(default_factory=dict)
    """Additional collection settings."""
    
    def __init__(self, path: Union[Path, PurePosixPath], name: str = "", 
                 prefix: str = "", num: int = 3, sep: str = "", suffix: str = "",
                 tags: Dict[str, str] = None, settings: Dict[str, Any] = None):
        """Initialize a collection configuration with specified parameters.
        
        Args:
            path: The filesystem path of the collection
            name: The name of the collection (defaults to directory name if empty)
            prefix: The prefix for items in this collection
            num: Number of digits for item numbering
            sep: Separator between prefix and number
            suffix: Suffix for item files
            tags: Collection tags as key-description pairs
            settings: Additional collection settings
        """
        self.path = path
        self.name = name if name else (path.name if path else "")
        self.prefix = prefix if prefix else (self.name.upper()[:3] if self.name else "")
        self.num = num
        self.sep = sep
        self.suffix = suffix
        self.tags = tags or {}
        self.settings = settings or {}
    
    @classmethod
    def load(cls, path: Union[Path, PurePosixPath], vfs: VFSClient) -> 'CollectionConfig':
        """Load configuration from a YAML file.
        
        Args:
            path: The path to the collection directory
            vfs: The VFS client to use for file operations
            
        Returns:
            A new CollectionConfig instance loaded from storage
            
        Raises:
            InvalidCollectionError: If the collection directory does not contain a valid config file
        """
        # Convert to PurePosixPath for VFS operations
        if isinstance(path, Path):
            path = PurePosixPath(path.as_posix())
        
        CONFIG_FILENAME = cls.CONFIG_FILENAME
        config_path = path / CONFIG_FILENAME
        
        # Check if config file exists
        try:
            info = vfs.info(config_path)
            if not info:  # File doesn't exist
                raise InvalidCollectionError(f"Collection at '{path}' is invalid: Missing {CONFIG_FILENAME} file")
        except VFSClientException:
            raise InvalidCollectionError(f"Collection at '{path}' is invalid: Cannot access {CONFIG_FILENAME} file")
            
        try:
            content = vfs.get_text(config_path, encoding='utf-8')
            if not content:
                raise InvalidCollectionError(f"Collection at '{path}' is invalid: Empty {CONFIG_FILENAME} file")
                
            data = yaml.safe_load(content) or {}
            
            return cls(
                path=path,
                name=data.get('name', path.name),
                prefix=data.get('prefix', path.name.upper()[:3]),
                num=data.get('num', 3),
                sep=data.get('sep', ''),
                suffix=data.get('suffix', '.md'),
                tags=data.get('tags', {}),
                settings=data.get('settings', {})
            )
            
        except InvalidCollectionError:
            raise
        except Exception as e:
            raise VFSClientException(
                'ConfigLoadError',
                f'Failed to load collection config from {config_path}: {e}'
            )
    
    @classmethod
    def _create_default_config(cls, path: Union[Path, PurePosixPath]) -> 'CollectionConfig':
        """Create a default configuration for a new collection.
        
        Args:
            path: The path to the collection directory
            
        Returns:
            A new CollectionConfig with default values
        """
        if isinstance(path, Path):
            path = PurePosixPath(path.as_posix())
            
        return cls(
            path=path,
            name=path.name,
            prefix=path.name.upper()[:3],
            num=3,
            sep='',
            suffix='.md',
            tags={},
            settings={}
        )
    
    def save(self, vfs: VFSClient) -> None:
        """Save configuration to a YAML file.
        
        Args:
            vfs: The VFS client to use for file operations
            
        Raises:
            VFSClientException: If the configuration file cannot be written
        """
        config_path = self.path / CONFIG_FILENAME
        
        data = {
            'name': self.name,
            'prefix': self.prefix,
            'num': self.num,
            'sep': self.sep,
            'suffix': self.suffix,
            'tags': self.tags,
            'settings': self.settings
        }
        
        try:
            content = yaml.dump(data, default_flow_style=False, allow_unicode=True)
            vfs.put(config_path, content.encode('utf-8'), create_if_missing=True)
        except Exception as e:
            raise VFSClientException(
                'ConfigSaveError',
                f'Failed to save collection config to {config_path}: {e}'
            )
    
    def get_item_filename(self, item_name: str) -> str:
        """Generate filename for an item based on collection configuration.
        
        Args:
            item_name: The name of the item
            
        Returns:
            The formatted filename for the item
        """
        # 兼容，可以直接传入 item_name ，也可以传入 带 prefix 的 item 
        if self.prefix and item_name.startswith(self.prefix):
            # Extract the number part
            name_part = item_name[len(self.prefix):]
            if self.sep and name_part.startswith(self.sep):
                name_part = name_part[len(self.sep):]
        else:
            name_part = item_name
        if name_part.isdigit():
            number = int(name_part)
            formatted_number = f"{number:0{self.num}d}"
            return f"{self.prefix}{self.sep}{formatted_number}{self.suffix}"
        else:
            return f"{self.prefix}{self.sep}{name_part}{self.suffix}"

    def parse_item_name(self, filename: str) -> Optional[Tuple[int,str]]:
        """Parse item name from filename.
        
        Args:
            filename: The filename to parse
            
        Returns:
            The item name if parsing succeeds, None otherwise
        """
        # Remove suffix if present
        if self.suffix and filename.endswith(self.suffix):
            base_name = filename[:-len(self.suffix)]
        else:
            base_name = filename
            
        # Check if it starts with prefix
        if self.prefix and base_name.startswith(self.prefix):
            # Extract the number part
            number_part = base_name[len(self.prefix):]
            if self.sep and number_part.startswith(self.sep):
                number_part = number_part[len(self.sep):]
                
            if number_part.isdigit():
                return int(number_part), number_part
            else:
                return 0, number_part       # 隐含的，number 不能是 0
                
        return None