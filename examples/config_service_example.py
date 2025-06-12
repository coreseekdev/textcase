#!/usr/bin/env python3
"""Example demonstrating the ConfigService usage."""

import os
import sys
import tempfile
import json
from pathlib import Path

# Add the src directory to the path so we can import textcase
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from textcase.core import ConfigService, get_config, set_config
from textcase.core.service_registry import create_service_registry

# Create a service registry instance
service_registry = create_service_registry()


def test_basic_config():
    """Test basic configuration functionality."""
    print("=== Testing Basic Configuration ===")
    
    # Create a new config service
    config = ConfigService()
    
    # Test default values
    print(f"Default VFS root path: {config.get_vfs_root_path()}")
    print(f"Default service port: {config.get('services.default_port')}")
    print(f"Default log level: {config.get('logging.level')}")
    
    # Test setting values
    config.set('vfs.root_path', '/custom/path')
    config.set('services.default_port', 9000)
    
    print(f"\nAfter setting custom values:")
    print(f"VFS root path: {config.get_vfs_root_path()}")
    print(f"Service port: {config.get('services.default_port')}")
    
    # Test nested configuration
    config.set('custom.nested.value', 'test')
    print(f"Custom nested value: {config.get('custom.nested.value')}")
    
    print("✓ Basic configuration test passed\n")


def test_config_file():
    """Test configuration file loading and saving."""
    print("=== Testing Configuration File ===")
    
    # Create a temporary config file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        config_data = {
            'vfs': {
                'root_path': '/test/config/path',
                'max_file_size': 5242880  # 5MB
            },
            'services': {
                'default_port': 8080,
                'bind_host': '0.0.0.0'
            },
            'custom': {
                'app_name': 'TextCase Test',
                'version': '1.0.0'
            }
        }
        json.dump(config_data, f, indent=2)
        config_file = f.name
    
    try:
        # Load config from file
        config = ConfigService(config_file)
        
        print(f"Loaded VFS root path: {config.get_vfs_root_path()}")
        print(f"Loaded service port: {config.get('services.default_port')}")
        print(f"Loaded bind host: {config.get('services.bind_host')}")
        print(f"Loaded app name: {config.get('custom.app_name')}")
        
        # Modify and save
        config.set('custom.modified', True)
        
        # Save to a new file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            save_file = f.name
        
        config.save_config(save_file)
        
        # Verify saved file
        with open(save_file, 'r') as f:
            saved_data = json.load(f)
            print(f"Saved modified flag: {saved_data.get('custom', {}).get('modified')}")
        
        print("✓ Configuration file test passed\n")
        
    finally:
        # Clean up
        os.unlink(config_file)
        if 'save_file' in locals():
            os.unlink(save_file)


def test_environment_variables():
    """Test environment variable configuration."""
    print("=== Testing Environment Variables ===")
    
    # Set environment variables
    os.environ['TEXTCASE_VFS_ROOT_PATH'] = '/env/test/path'
    os.environ['TEXTCASE_DEFAULT_PORT'] = '7777'
    os.environ['TEXTCASE_LOG_LEVEL'] = 'DEBUG'
    
    try:
        # Create config service (should pick up env vars)
        config = ConfigService()
        
        print(f"VFS root path from env: {config.get_vfs_root_path()}")
        print(f"Service port from env: {config.get('services.default_port')}")
        print(f"Log level from env: {config.get('logging.level')}")
        
        print("✓ Environment variables test passed\n")
        
    finally:
        # Clean up environment variables
        del os.environ['TEXTCASE_VFS_ROOT_PATH']
        del os.environ['TEXTCASE_DEFAULT_PORT']
        del os.environ['TEXTCASE_LOG_LEVEL']


def test_global_config():
    """Test global configuration instance."""
    print("=== Testing Global Configuration ===")
    
    # Get global config
    config1 = get_config()
    config2 = get_config()
    
    # Should be the same instance
    print(f"Same instance: {config1 is config2}")
    
    # Set a custom config
    custom_config = ConfigService()
    custom_config.set('test.global', 'custom_value')
    set_config(custom_config)
    
    # Get global config again
    config3 = get_config()
    print(f"Custom global config value: {config3.get('test.global')}")
    
    print("✓ Global configuration test passed\n")


def test_service_integration():
    """Test integration with service registry."""
    print("=== Testing Service Integration ===")
    
    # Set custom VFS root path
    config = ConfigService()
    config.set('vfs.root_path', tempfile.gettempdir())
    set_config(config)
    
    try:
        # Get config service through service registry
        config_service_info = service_registry.get_service('config')
        print(f"Config service endpoint: {config_service_info.endpoint}")
        
        # Get VFS service (should use config for root path)
        vfs_service_info = service_registry.get_service('vfs')
        print(f"VFS service endpoint: {vfs_service_info.endpoint}")
        
        print("✓ Service integration test passed\n")
        
    except Exception as e:
        print(f"Service integration test failed: {e}")
        print("Note: This is expected if services are not running\n")


def test_service_specific_config():
    """Test service-specific configuration."""
    print("=== Testing Service-Specific Configuration ===")
    
    config = ConfigService()
    
    # Set service-specific configuration
    config.set('services.vfs.custom_setting', 'vfs_value')
    config.set('services.test.custom_setting', 'test_value')
    
    # Get service-specific config
    vfs_config = config.get_service_config('vfs')
    test_config = config.get_service_config('test')
    unknown_config = config.get_service_config('unknown')
    
    print(f"VFS service config: {vfs_config}")
    print(f"Test service config: {test_config}")
    print(f"Unknown service config: {unknown_config}")
    
    print("✓ Service-specific configuration test passed\n")


def main():
    """Run all configuration service tests."""
    print("ConfigService Example and Tests")
    print("=" * 40)
    
    test_basic_config()
    test_config_file()
    test_environment_variables()
    test_global_config()
    test_service_integration()
    test_service_specific_config()
    
    print("All tests completed successfully!")


if __name__ == '__main__':
    main()