"""Configuration service protocol definition.

This module defines the protocol interface for configuration services.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, Union, List


class ServiceConfigProtocol(ABC):
    """Protocol interface for configuration services.
    
    This protocol defines the interface that all configuration service
    implementations must follow.
    """
    
    @abstractmethod
    def get(self, key: str, default: Optional[Union[str, List[str]]] = None) -> Optional[Union[str, List[str]]]:
        """Get configuration value by key.
        
        Args:
            key: Configuration key (supports dot notation, e.g., 'vfs.root_path')
            default: Default value if key not found
            
        Returns:
            Configuration value
        """
        ...
    
    @abstractmethod
    def set(self, key: str, value: Union[str, List[str]], persistent: bool = False) -> Union[str, List[str]]:
        """Set configuration value by key.
        
        Args:
            key: Configuration key (supports dot notation)
            value: Value to set (can be scalar or list)
            persistent: Whether to store in persistent config (default: temporary)
            
        Returns:
            Previous value if any
        """
        ...
    
    @abstractmethod
    def set_persistent(self, key: str, value: Union[Any, List[Any]]) -> None:
        """Set persistent configuration value.
        
        Args:
            key: Configuration key
            value: Value to set
        """
        ...
    
    @abstractmethod
    def set_temporary(self, key: str, value: Union[Any, List[Any]]) -> None:
        """Set temporary configuration value.
        
        Args:
            key: Configuration key
            value: Value to set
        """
        ...
    
    @abstractmethod
    def set_if_not_default(self, key: str, value: Union[str, List[str]], is_default: bool = False, persistent: bool = False) -> bool:
        """Set configuration value only if conditions are met.
        
        Args:
            key: Configuration key (supports dot notation)
            value: Value to set
            is_default: Whether the value being set is a default value
            persistent: Whether to store in persistent config (default: temporary)
            
        Returns:
            True if value was set, False if skipped
        """
        ...
    
    @abstractmethod
    def remove(self, key: str, persistent: bool = False) -> None:
        """Remove configuration value.
        
        Args:
            key: Configuration key
            persistent: Whether to remove from persistent config
        """
        ...
    
    @abstractmethod
    def save_config(self, config_file: Optional[str] = None) -> None:
        """Save persistent configuration to file.
        
        Args:
            config_file: Optional path to save configuration
        """
        ...
    
    @abstractmethod
    def get_persistent_config(self) -> Dict[str, Any]:
        """Get persistent configuration as dictionary.
        
        Returns:
            Persistent configuration dictionary
        """
        ...
    
    @abstractmethod
    def get_temporary_config(self) -> Dict[str, Any]:
        """Get temporary configuration as dictionary.
        
        Returns:
            Temporary configuration dictionary
        """
        ...
    
    @abstractmethod
    def get_merged_config(self) -> Dict[str, Any]:
        """Get merged configuration (persistent + temporary).
        
        Returns:
            Merged configuration dictionary
        """
        ...
    
    @abstractmethod
    def name(self) -> str:
        """Get the name of the configuration service.
        
        Returns:
            Service name
        """
        ...
    
    @abstractmethod
    def to_dict(self) -> Dict[str, Any]:
        """Get all configuration as dictionary.
        
        Returns:
            Complete merged configuration dictionary
        """
        ...