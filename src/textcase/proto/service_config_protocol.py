"""Configuration service protocol definition.

This module defines the protocol interface for configuration services.
"""

from abc import ABC, abstractmethod
from tkinter import NO
from typing import Dict, Any, Optional, Union, List


class ServiceConfigProtocol(ABC):
    """Protocol interface for configuration services.
    
    This protocol defines the interface that all configuration service
    implementations must follow.
    """
    
    @abstractmethod
    def get(self, key: str, default: Optional[Union[str, List[str]]] = None) -> Union[None, str, List[str]]:
        """Get configuration value by key.
        
        Args:
            key: Configuration key (supports dot notation, e.g., 'vfs.root_path')
            default: Default value if key not found
            
        Returns:
            Configuration value
        """
        ...
    
    @abstractmethod
    def set(self, key: str, value: Union[None, str, List[str]]) -> Union[None, str, List[str]]:
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
    def set_temporary(self, key: str, value: Union[str, List[str]], override: bool = False) -> Union[None,str, List[str]]:
        """Set temporary configuration value.
        
        Args:
            key: Configuration key
            value: Value to set
            override: Whether to override existing value (default: False)
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