#!/usr/bin/env python3
"""Example demonstrating optional RPC usage.

This example shows how to use the new service registry and VFS client
with optional zerorpc/gevent dependencies.
"""

import sys
import os
import logging
from pathlib import Path

# Add src to path for development
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from textcase.service.service_registry_new import create_service_registry
from textcase.client.vfs_client_new import VFSClientNew

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def check_backend_availability():
    """Check which backends are available."""
    backends = []
    
    # Check ZeroRPC backend
    try:
        from textcase.service.backends.zerorpc_backend import ZeroRPCBackend
        backends.append('zerorpc')
        logger.info("✅ ZeroRPC backend available")
    except ImportError as e:
        logger.info(f"❌ ZeroRPC backend not available: {e}")
    
    # Direct backend is always available
    backends.append('direct')
    logger.info("✅ Direct backend available")
    
    return backends


def test_service_registry():
    """Test the service registry with automatic backend selection."""
    logger.info("\n=== Testing Service Registry ===")
    
    # Create service registry (auto-selects backend)
    registry = create_service_registry()
    logger.info(f"Created registry with backend: {registry.backend_type}")
    
    # Test config service (always available)
    config_service = registry.get_service('config')
    logger.info(f"Config service: {type(config_service).__name__}")
    
    # Configure VFS root path
    repo_path = Path.cwd()
    config_service.set("vfs.root_path", str(repo_path))
    logger.info(f"Set VFS root path to: {repo_path}")
    
    # Test VFS service
    try:
        # Start VFS service
        vfs_endpoint = registry.get_service('vfs')
        if vfs_endpoint:
            logger.info(f"VFS service started on: {vfs_endpoint}")
            
            # Test if service is running
            is_running = registry.is_service_running('vfs')
            logger.info(f"VFS service running: {is_running}")
            
            return registry, vfs_endpoint
        else:
            logger.error("Failed to start VFS service")
            return None, None
            
    except Exception as e:
        logger.error(f"Error starting VFS service: {e}")
        return None, None


def test_vfs_client(registry, endpoint):
    """Test the VFS client with the given endpoint."""
    logger.info("\n=== Testing VFS Client ===")
    
    try:
        # Create VFS client
        client = VFSClientNew(endpoint, service_registry=registry)
        logger.info(f"Created VFS client with backend: {client.backend_type}")
        
        # Test basic operations
        logger.info(f"VFS name: {client.name}")
        logger.info(f"VFS readonly: {client.readonly}")
        logger.info(f"VFS mount point: {client.mount_point}")
        
        # List root directory
        entries = client.list('/')
        logger.info(f"Root directory has {len(entries)} entries")
        
        # Show first few entries
        for i, entry in enumerate(entries[:5]):
            entry_type = "📁" if entry.get('type') == 'directory' else "📄"
            logger.info(f"  {entry_type} {entry.get('name', 'unknown')}")
        
        if len(entries) > 5:
            logger.info(f"  ... and {len(entries) - 5} more entries")
        
        # Test file operations if README exists
        readme_files = ['README.md', 'README.txt', 'README']
        for readme in readme_files:
            if client.exists(f'/{readme}'):
                logger.info(f"\nReading {readme}:")
                try:
                    content = client.get_text(f'/{readme}')
                    # Show first few lines
                    lines = content.split('\n')[:3]
                    for line in lines:
                        logger.info(f"  {line}")
                    if len(content.split('\n')) > 3:
                        logger.info("  ...")
                except Exception as e:
                    logger.error(f"Error reading {readme}: {e}")
                break
        
        return True
        
    except Exception as e:
        logger.error(f"Error testing VFS client: {e}")
        return False


def test_backend_specific():
    """Test specific backend implementations."""
    logger.info("\n=== Testing Specific Backends ===")
    
    # Test direct backend
    try:
        from textcase.service.backends.direct_backend import DirectBackend
        from textcase.service.service_registry_base import BaseServiceRegistry
        
        logger.info("Testing direct backend...")
        direct_backend = DirectBackend()
        direct_registry = BaseServiceRegistry(backend=direct_backend)
        
        # Start a service
        config_service = direct_registry.get_service('config')
        logger.info(f"Direct backend config service: {type(config_service).__name__}")
        
    except Exception as e:
        logger.error(f"Error testing direct backend: {e}")
    
    # Test ZeroRPC backend if available
    try:
        from textcase.service.backends.zerorpc_backend import ZeroRPCBackend
        from textcase.service.service_registry_base import BaseServiceRegistry
        
        logger.info("Testing ZeroRPC backend...")
        zerorpc_backend = ZeroRPCBackend()
        zerorpc_registry = BaseServiceRegistry(backend=zerorpc_backend)
        
        # Start a service
        config_service = zerorpc_registry.get_service('config')
        logger.info(f"ZeroRPC backend config service: {type(config_service).__name__}")
        
        # Clean up
        zerorpc_registry.stop_all_services()
        
    except ImportError:
        logger.info("ZeroRPC backend not available (dependencies not installed)")
    except Exception as e:
        logger.error(f"Error testing ZeroRPC backend: {e}")


def main():
    """Main example function."""
    logger.info("Optional RPC Example")
    logger.info("====================")
    
    # Check available backends
    available_backends = check_backend_availability()
    logger.info(f"Available backends: {', '.join(available_backends)}")
    
    # Test service registry
    registry, endpoint = test_service_registry()
    
    if registry and endpoint:
        # Test VFS client
        success = test_vfs_client(registry, endpoint)
        
        if success:
            logger.info("\n✅ All tests passed!")
        else:
            logger.error("\n❌ Some tests failed")
        
        # Clean up
        try:
            registry.stop_all_services()
            logger.info("Services stopped")
        except Exception as e:
            logger.error(f"Error stopping services: {e}")
    else:
        logger.error("\n❌ Failed to start services")
    
    # Test backend-specific functionality
    test_backend_specific()
    
    logger.info("\nExample completed")


if __name__ == '__main__':
    main()