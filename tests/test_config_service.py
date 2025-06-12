#!/usr/bin/env python3
"""Unit tests for ConfigService."""

import os
import sys
import unittest
import tempfile
import json
from unittest.mock import patch

# Add the src directory to the path so we can import textcase
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from textcase.core import ConfigService, get_config, set_config


class TestConfigService(unittest.TestCase):
    """Test cases for ConfigService."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Reset global config before each test
        import textcase.core.config_service
        textcase.core.config_service._global_config = None
    
    def test_default_config(self):
        """Test default configuration values."""
        config = ConfigService()
        
        # Test default VFS configuration
        self.assertEqual(config.get('vfs.root_path'), os.getcwd())
        self.assertTrue(config.get('vfs.enable_git_repo'))
        self.assertEqual(config.get('vfs.max_file_size'), 10 * 1024 * 1024)
        self.assertEqual(config.get('vfs.session_timeout'), 3600)
        
        # Test default service configuration
        self.assertEqual(config.get('services.default_port'), 8000)
        self.assertEqual(config.get('services.bind_host'), 'localhost')
        
        # Test default logging configuration
        self.assertEqual(config.get('logging.level'), 'INFO')
    
    def test_get_set_config(self):
        """Test getting and setting configuration values."""
        config = ConfigService()
        
        # Test simple get/set
        config.set('test.value', 'hello')
        self.assertEqual(config.get('test.value'), 'hello')
        
        # Test nested get/set
        config.set('nested.deep.value', 42)
        self.assertEqual(config.get('nested.deep.value'), 42)
        
        # Test default value
        self.assertEqual(config.get('nonexistent.key', 'default'), 'default')
        self.assertIsNone(config.get('nonexistent.key'))
    
    def test_config_file_loading(self):
        """Test loading configuration from file."""
        # Create temporary config file
        config_data = {
            'vfs': {
                'root_path': '/test/path',
                'max_file_size': 5242880
            },
            'custom': {
                'value': 'from_file'
            }
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(config_data, f)
            config_file = f.name
        
        try:
            config = ConfigService(config_file)
            
            # Test loaded values
            self.assertEqual(config.get('vfs.root_path'), '/test/path')
            self.assertEqual(config.get('vfs.max_file_size'), 5242880)
            self.assertEqual(config.get('custom.value'), 'from_file')
            
            # Test that defaults are still present
            self.assertTrue(config.get('vfs.enable_git_repo'))
            
        finally:
            os.unlink(config_file)
    
    def test_environment_variables(self):
        """Test loading configuration from environment variables."""
        env_vars = {
            'TEXTCASE_VFS_ROOT_PATH': '/env/path',
            'TEXTCASE_VFS_MAX_FILE_SIZE': '1048576',
            'TEXTCASE_DEFAULT_PORT': '9000',
            'TEXTCASE_BIND_HOST': '0.0.0.0',
            'TEXTCASE_LOG_LEVEL': 'DEBUG'
        }
        
        with patch.dict(os.environ, env_vars):
            config = ConfigService()
            
            self.assertEqual(config.get('vfs.root_path'), '/env/path')
            self.assertEqual(config.get('vfs.max_file_size'), 1048576)
            self.assertEqual(config.get('services.default_port'), 9000)
            self.assertEqual(config.get('services.bind_host'), '0.0.0.0')
            self.assertEqual(config.get('logging.level'), 'DEBUG')
    
    def test_config_merge(self):
        """Test configuration merging."""
        # Create config with file and env vars
        config_data = {
            'vfs': {
                'root_path': '/file/path',
                'custom_setting': 'from_file'
            },
            'services': {
                'default_port': 7000
            }
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(config_data, f)
            config_file = f.name
        
        env_vars = {
            'TEXTCASE_VFS_ROOT_PATH': '/env/path',  # Should override file
            'TEXTCASE_DEFAULT_PORT': '8080'  # Should override file
        }
        
        try:
            with patch.dict(os.environ, env_vars):
                config = ConfigService(config_file)
                
                # Env vars should override file values
                self.assertEqual(config.get('vfs.root_path'), '/env/path')
                self.assertEqual(config.get('services.default_port'), 8080)
                
                # File values should be preserved if not overridden
                self.assertEqual(config.get('vfs.custom_setting'), 'from_file')
                
                # Default values should still be present
                self.assertTrue(config.get('vfs.enable_git_repo'))
                
        finally:
            os.unlink(config_file)
    
    def test_save_config(self):
        """Test saving configuration to file."""
        config = ConfigService()
        config.set('test.save', 'saved_value')
        config.set('nested.config.value', 123)
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            save_file = f.name
        
        try:
            config.save_config(save_file)
            
            # Load saved config
            with open(save_file, 'r') as f:
                saved_data = json.load(f)
            
            self.assertEqual(saved_data['test']['save'], 'saved_value')
            self.assertEqual(saved_data['nested']['config']['value'], 123)
            
        finally:
            os.unlink(save_file)
    
    def test_vfs_root_path(self):
        """Test VFS root path helper method."""
        config = ConfigService()
        
        # Test default
        self.assertEqual(config.get_vfs_root_path(), os.getcwd())
        
        # Test custom value
        config.set('vfs.root_path', '/custom/path')
        self.assertEqual(config.get_vfs_root_path(), '/custom/path')
    
    def test_service_config(self):
        """Test service-specific configuration."""
        config = ConfigService()
        
        # Set service-specific config
        config.set('services.vfs.timeout', 30)
        config.set('services.vfs.retries', 3)
        config.set('services.test.enabled', True)
        
        # Get service configs
        vfs_config = config.get_service_config('vfs')
        test_config = config.get_service_config('test')
        unknown_config = config.get_service_config('unknown')
        
        self.assertEqual(vfs_config['timeout'], 30)
        self.assertEqual(vfs_config['retries'], 3)
        self.assertEqual(test_config['enabled'], True)
        self.assertEqual(unknown_config, {})
    
    def test_global_config(self):
        """Test global configuration instance."""
        # Get global config
        config1 = get_config()
        config2 = get_config()
        
        # Should be the same instance
        self.assertIs(config1, config2)
        
        # Set custom global config
        custom_config = ConfigService()
        custom_config.set('test.global', 'custom')
        set_config(custom_config)
        
        # Should get the custom config
        config3 = get_config()
        self.assertIs(config3, custom_config)
        self.assertEqual(config3.get('test.global'), 'custom')
    
    def test_service_name(self):
        """Test service name method."""
        config = ConfigService()
        self.assertEqual(config.name(), "ConfigService")
    
    def test_to_dict(self):
        """Test converting config to dictionary."""
        config = ConfigService()
        config.set('test.value', 'hello')
        
        config_dict = config.to_dict()
        
        # Should contain default values
        self.assertIn('vfs', config_dict)
        self.assertIn('services', config_dict)
        self.assertIn('logging', config_dict)
        
        # Should contain custom value
        self.assertEqual(config_dict['test']['value'], 'hello')
        
        # Should be a copy (modifying shouldn't affect original)
        config_dict['test']['value'] = 'modified'
        self.assertEqual(config.get('test.value'), 'hello')
    
    def test_invalid_config_file(self):
        """Test handling of invalid config file."""
        # Test with non-existent file
        config = ConfigService('/nonexistent/file.json')
        # Should still have default values
        self.assertEqual(config.get('vfs.root_path'), os.getcwd())
        
        # Test with invalid JSON
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            f.write('invalid json content')
            invalid_file = f.name
        
        try:
            config = ConfigService(invalid_file)
            # Should still have default values
            self.assertEqual(config.get('vfs.root_path'), os.getcwd())
        finally:
            os.unlink(invalid_file)
    
    def test_invalid_env_vars(self):
        """Test handling of invalid environment variables."""
        env_vars = {
            'TEXTCASE_VFS_MAX_FILE_SIZE': 'not_a_number',
            'TEXTCASE_DEFAULT_PORT': 'not_a_port'
        }
        
        with patch.dict(os.environ, env_vars):
            config = ConfigService()
            
            # Should use default values for invalid env vars
            self.assertEqual(config.get('vfs.max_file_size'), 10 * 1024 * 1024)
            self.assertEqual(config.get('services.default_port'), 8000)


if __name__ == '__main__':
    unittest.main()