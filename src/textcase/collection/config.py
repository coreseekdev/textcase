"""Collection Configuration Implementation

This module provides YAML-based configuration management for collections,
similar to the original module_config.py implementation.
"""

from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath
from typing import Any, Dict, Optional, Union

import yaml

from ..client.vfs_client import VFSClient, VFSClientException


@dataclass
class CollectionConfig:
    """YAML-based configuration for resource collections.
    
    This implementation stores configuration in a YAML file at `.textcase.yml`
    within the collection directory, following the same pattern as module_config.
    """
    
    path: Union[Path, PurePosixPath]
    """The filesystem path of the collection."""
    
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
    
    @classmethod
    def load(cls, path: Union[Path, PurePosixPath], vfs: VFSClient) -> 'CollectionConfig':
        """Load configuration from a YAML file.
        
        Args:
            path: The path to the collection directory
            vfs: The VFS client to use for file operations
            
        Returns:
            A new CollectionConfig instance loaded from storage
        """
        # Convert to PurePosixPath for VFS operations
        if isinstance(path, Path):
            path = PurePosixPath(path.as_posix())
            
        config_path = path / '.textcase.yml'
        
        # Check if config file exists
        try:
            info = vfs.info(config_path)
            if not info:  # File doesn't exist
                return cls._create_default_config(path)
        except VFSClientException:
            return cls._create_default_config(path)
            
        try:
            content = vfs.get_text(config_path, encoding='utf-8')
            if not content:
                return cls._create_default_config(path)
                
            data = yaml.safe_load(content) or {}
            
            return cls(
                path=path,
                name=data.get('name', path.name),
                prefix=data.get('prefix', path.name.upper()[:3]),
                num=data.get('num', 3),
                sep=data.get('sep', ''),
                suffix=data.get('suffix', ''),
                tags=data.get('tags', {}),
                settings=data.get('settings', {})
            )
            
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
            suffix='',
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
        config_path = self.path / '.textcase.yml'
        
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
        # Extract number from item name if it follows the pattern
        if item_name.startswith(self.prefix):
            number_part = item_name[len(self.prefix):]
            if number_part.isdigit():
                number = int(number_part)
                formatted_number = f"{number:0{self.num}d}"
                return f"{self.prefix}{self.sep}{formatted_number}{self.suffix}"
        
        # Fallback to simple formatting
        return f"{item_name}{self.suffix}"
    
    def parse_item_name(self, filename: str) -> Optional[str]:
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
                return f"{self.prefix}{number_part}"
                
        return None