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
from ..proto.resource_collection_protocol import InvalidCollectionError, ConfigLoadError


@dataclass
class CollectionConfig:
    """YAML-based configuration for resource collections.
    
    This implementation stores configuration in a YAML file at `.textcase.yml`
    within the collection directory, following the same pattern as module_config.
    """
    
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
    
    def __init__(self, prefix: str = "", num: int = 3, sep: str = "", suffix: str = "",
                 tags: Dict[str, str] = None, settings: Dict[str, Any] = None):
        """Initialize a collection configuration with specified parameters.
        
        Args:
            prefix: The prefix for items in this collection
            num: Number of digits for item numbering
            sep: Separator between prefix and number
            suffix: Suffix for item files
            tags: Collection tags as key-description pairs
            settings: Additional collection settings
        """ 
        self.prefix = prefix
        self.num = num
        self.sep = sep
        self.suffix = suffix
        self.tags = tags or {}
        self.settings = settings or {}
    
    @classmethod
    def loads(cls, config_file: PurePosixPath, content: str) -> 'CollectionConfig':
        """Load configuration from a YAML file.
        
        Args:
            content: The YAML content to load
            
        Returns:
            A new CollectionConfig instance loaded from storage
            
        Raises:
            InvalidCollectionError: If the collection directory does not contain a valid config file
        """
        if not content:
            raise InvalidCollectionError(f"Collection config file {config_file} is invalid")

        try:            
            data = yaml.safe_load(content) or {}
            return cls(
                prefix=data.get('prefix', ""),
                num=data.get('num', 3),
                sep=data.get('sep', ''),
                suffix=data.get('suffix', '.md'),
                tags=data.get('tags', {}),
                settings=data.get('settings', {})
            )
        except Exception as e:
            raise ConfigLoadError(
                f'Failed to load collection config from {config_path}: {e}'
            )
    
    @classmethod
    def _create_default_config(cls, prefix: str, tags: Dict[str, str] = None) -> 'CollectionConfig':
        """Create a default configuration for a new collection.
        
        Args:
            prefix: The prefix of the collection
            tags: Optional tags for the collection
            
        Returns:
            A new CollectionConfig with default values
        """
        assert prefix, "prefix must be set"

        return cls(
            prefix=prefix,
            num=3,
            sep='',
            suffix='.md',
            tags=tags or {},
            settings={}
        )
    
    def dumps(self) -> str:
        """Save configuration to a YAML file.
        
        Args:
            vfs: The VFS client to use for file operations
            
        Raises:
            VFSClientException: If the configuration file cannot be written
        """
        
        data = {
            'prefix': self.prefix,
            'num': self.num,
            'sep': self.sep,
            'suffix': self.suffix,
        }
        # 有数据才会出现的配置项
        if self.settings:
            data['settings'] = self.settings
        if self.tags:
            data['tags'] = self.tags

        return yaml.dump(data, default_flow_style=False, allow_unicode=True)

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
                
        return 0, None