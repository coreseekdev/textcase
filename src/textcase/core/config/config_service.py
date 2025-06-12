"""Configuration service for managing application settings."""

import os
import yaml
import json
from typing import Dict, Any, Optional, Union, List
from pathlib import Path
import copy

from .service_config_protocol import ServiceConfigProtocol


class ConfigService(ServiceConfigProtocol):
    """Configuration service that provides key/value storage interface.
    
    This service only handles application-level configuration storage.
    Configuration loading strategies are handled by separate components.
    """
    
    def __init__(self, config_file: Optional[str] = None):
        """Initialize configuration service.
        
        Args:
            config_file: Optional path to configuration file
        """
        self._persistent_config: Dict[str, Any] = {}
        self._temporary_config: Dict[str, Any] = {}
        self._config_file = config_file or self._get_default_config_file()
        
        # Load persistent configuration from file
        if self._config_file and os.path.exists(self._config_file):
            self._load_config_file()
    
    def _get_default_config_file(self) -> str:
        """Get default configuration file path.
        
        Returns:
            Default config file path
        """
        # Try ~/.textcase.yml first, then ~/.textcase/config.yml
        home_config = os.path.expanduser('~/.textcase.yml')
        if os.path.exists(home_config):
            return home_config
        
        return os.path.expanduser('~/.textcase/config.yml')
    
    def _load_config_file(self) -> None:
        """Load configuration from file."""
        try:
            with open(self._config_file, 'r', encoding='utf-8') as f:
                if self._config_file.endswith('.yml') or self._config_file.endswith('.yaml'):
                    self._persistent_config = yaml.safe_load(f) or {}
                else:
                    self._persistent_config = json.load(f)
        except (FileNotFoundError, yaml.YAMLError, json.JSONDecodeError) as e:
            print(f"Warning: Could not load config file {self._config_file}: {e}")
            self._persistent_config = {}
    
    def get(self, key: str, default: Optional[Union[str, List[str]]] = None) -> Optional[Union[str, List[str]]] :
        """Get configuration value by key.
        
        Temporary config takes precedence over persistent config.
        
        Args:
            key: Configuration key (supports dot notation, e.g., 'vfs.root_path')
            default: Default value if key not found
            
        Returns:
            Configuration value
        """
        # Check temporary config first
        value = self._get_from_dict(self._temporary_config, key)
        if value is not None:
            return value
        
        # Then check persistent config
        value = self._get_from_dict(self._persistent_config, key)
        if value is not None:
            return value
        
        return default
    
    def _get_from_dict(self, config_dict: Dict[str, Union[str, List[str]]], key: str) -> Optional[Union[str, List[str]]]:
        """Get value from configuration dictionary using dot notation.
        
        Args:
            config_dict: Configuration dictionary
            key: Dot-separated key
            
        Returns:
            Value or None if not found
        """
        keys = key.split('.')
        value = config_dict
        
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return None
        
        return value
    
    def set(self, key: str, value: Union[str, List[str]], persistent: bool = False) -> Union[str, List[str]]:
        """Set configuration value by key.
        
        Args:
            key: Configuration key (supports dot notation)
            value: Value to set (can be scalar or list)
            persistent: Whether to store in persistent config (default: temporary)
        """
        target_config = self._persistent_config if persistent else self._temporary_config
        return self._set_in_dict(target_config, key, value)
    
    def _set_in_dict(self, config_dict: Dict[str, Union[str, List[str]]], key: str, value: Union[str, List[str]]) -> Union[str, List[str]]:
        """Set value in configuration dictionary using dot notation.
        
        Args:
            config_dict: Configuration dictionary
            key: Dot-separated key
            value: Value to set
        """
        keys = key.split('.')
        config = config_dict
        
        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]

        orig = config.get(keys[-1], None)
        config[keys[-1]] = value
        return orig
    
    def set_persistent(self, key: str, value: Union[Any, List[Any]]) -> None:
        """Set persistent configuration value.
        
        Args:
            key: Configuration key
            value: Value to set
        """
        self.set(key, value, persistent=True)
    
    def set_temporary(self, key: str, value: Union[Any, List[Any]]) -> None:
        """Set temporary configuration value.
        
        Args:
            key: Configuration key
            value: Value to set
        """
        self.set(key, value, persistent=False)
    
    def set_if_not_default(self, key: str, value: Union[str, List[str]], is_default: bool = False, persistent: bool = False) -> bool:
        """Set configuration value only if conditions are met.
        
        Args:
            key: Configuration key (supports dot notation)
            value: Value to set
            is_default: Whether the value being set is a default value
            persistent: Whether to store in persistent config (default: temporary)
            
        Returns:
            True if value was set, False if skipped
            
        Logic:
        - If is_default=True and key has no value: set the value
        - If is_default=True and key has value: skip (don't set)
        - If is_default=False: always set the value
        """
        current_value = self.get(key)
        
        if is_default:
            # If it's a default value and key already has a value, skip
            if current_value is not None:
                return False
            # If it's a default value and key has no value, set it
            self.set(key, value, persistent=persistent)
            return True
        else:
            # If it's not a default value, always set it
            self.set(key, value, persistent=persistent)
            return True
    
    def remove(self, key: str, persistent: bool = False) -> None:
        """Remove configuration value.
        
        Args:
            key: Configuration key
            persistent: Whether to remove from persistent config
        """
        target_config = self._persistent_config if persistent else self._temporary_config
        self._remove_from_dict(target_config, key)
    
    def _remove_from_dict(self, config_dict: Dict[str, Any], key: str) -> None:
        """Remove value from configuration dictionary.
        
        Args:
            config_dict: Configuration dictionary
            key: Dot-separated key
        """
        keys = key.split('.')
        config = config_dict
        
        for k in keys[:-1]:
            if isinstance(config, dict) and k in config:
                config = config[k]
            else:
                return
        
        if isinstance(config, dict) and keys[-1] in config:
            del config[keys[-1]]
    
    def save_config(self, config_file: Optional[str] = None) -> None:
        """Save persistent configuration to file.
        
        Args:
            config_file: Optional path to save configuration
        """
        file_path = config_file or self._config_file
        if not file_path:
            raise ValueError("No config file specified")
        
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        
        with open(file_path, 'w', encoding='utf-8') as f:
            if file_path.endswith('.yml') or file_path.endswith('.yaml'):
                yaml.dump(self._persistent_config, f, default_flow_style=False, allow_unicode=True)
            else:
                json.dump(self._persistent_config, f, indent=2, ensure_ascii=False)
    
    def get_persistent_config(self) -> Dict[str, Any]:
        """Get persistent configuration as dictionary.
        
        Returns:
            Persistent configuration dictionary
        """
        return copy.deepcopy(self._persistent_config)
    
    def get_temporary_config(self) -> Dict[str, Any]:
        """Get temporary configuration as dictionary.
        
        Returns:
            Temporary configuration dictionary
        """
        return copy.deepcopy(self._temporary_config)
    
    def get_merged_config(self) -> Dict[str, Any]:
        """Get merged configuration (persistent + temporary).
        
        Returns:
            Merged configuration dictionary
        """
        merged = copy.deepcopy(self._persistent_config)
        self._merge_config(merged, self._temporary_config)
        return merged
    
    def _merge_config(self, base: Dict[str, Any], override: Dict[str, Any]) -> None:
        """Recursively merge configuration dictionaries.
        
        Args:
            base: Base configuration dictionary
            override: Override configuration dictionary
        """
        for key, value in override.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                self._merge_config(base[key], value)
            else:
                base[key] = value
    
    def name(self) -> str:
        """Get the name of the configuration service."""
        return "ConfigService"
    
    def to_dict(self) -> Dict[str, Any]:
        """Get all configuration as dictionary.
        
        Returns:
            Complete merged configuration dictionary
        """
        return self.get_merged_config()
