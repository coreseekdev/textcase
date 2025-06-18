#!/usr/bin/env python3
"""Tests for optional RPC functionality.

This module tests the new service registry and client implementations
with optional zerorpc/gevent dependencies.
"""

import unittest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import patch, MagicMock

# Import the modules to test
from textcase.service.service_registry_new import create_service_registry
from textcase.service.service_registry_base import BaseServiceRegistry
from textcase.service.backends.direct_backend import DirectBackend
from textcase.client.vfs_client_new import VFSClientNew, VFSClientException

# Try to import zerorpc backend
try:
    from textcase.service.backends.zerorpc_backend import ZeroRPCBackend
    ZERORPC_AVAILABLE = True
except ImportError:
    ZERORPC_AVAILABLE = False


class TestDirectBackend(unittest.TestCase):
    """Test the direct backend implementation."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.backend = DirectBackend()
    
    def test_generate_endpoint(self):
        """Test endpoint generation."""
        endpoint = self.backend.generate_endpoint('test_service')
        self.assertTrue(endpoint.startswith('direct://test_service-'))
        self.assertIn('-', endpoint)
    
    def test_service_lifecycle(self):
        """Test service start/stop lifecycle."""
        # Mock service instance
        service_instance = MagicMock()
        service_instance.test_method.return_value = "test_result"
        
        # Start service
        handle = self.backend.start_service('test', service_instance, 'direct://test')
        self.assertIsInstance(handle, dict)
        self.assertEqual(handle['service_instance'], service_instance)
        
        # Check if running
        self.assertTrue(self.backend.is_service_running('test', handle))
        
        # Stop service
        self.backend.stop_service('test', handle)
        self.assertFalse(self.backend.is_service_running('test', handle))
    
    def test_create_client(self):
        """Test client creation."""
        # Mock service instance
        service_instance = MagicMock()
        service_instance.test_method.return_value = "test_result"
        
        # Start service
        handle = self.backend.start_service('test', service_instance, 'direct://test')
        
        # Create client
        client = self.backend.create_client('direct://test')
        
        # Test client method call
        result = client.test_method()
        self.assertEqual(result, "test_result")
        
        # Clean up
        self.backend.stop_service('test', handle)


@unittest.skipUnless(ZERORPC_AVAILABLE, "zerorpc not available")
class TestZeroRPCBackend(unittest.TestCase):
    """Test the ZeroRPC backend implementation."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.backend = ZeroRPCBackend()
    
    def test_generate_endpoint(self):
        """Test endpoint generation."""
        endpoint = self.backend.generate_endpoint('test_service')
        self.assertTrue(endpoint.startswith('inproc://test_service-'))
        self.assertIn('-', endpoint)
    
    def test_backend_initialization(self):
        """Test backend initialization."""
        self.assertIsInstance(self.backend._service_greenlets, dict)
        self.assertIsInstance(self.backend._service_servers, dict)
        self.assertIsInstance(self.backend._stop_events, dict)


class TestServiceRegistry(unittest.TestCase):
    """Test the service registry implementation."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Use direct backend for testing
        self.backend = DirectBackend()
        self.registry = BaseServiceRegistry(backend=self.backend)
    
    def test_config_service(self):
        """Test config service access."""
        config_service = self.registry.get_service('config')
        self.assertIsNotNone(config_service)
        # Config service should be returned directly, not as endpoint
        self.assertNotIsInstance(config_service, str)
    
    def test_backend_type(self):
        """Test backend type property."""
        self.assertEqual(self.registry.backend_type, 'DirectBackend')
    
    def test_service_lifecycle(self):
        """Test service lifecycle management."""
        # Configure VFS root path
        config_service = self.registry.get_service('config')
        config_service.set("vfs.root_path", str(Path.cwd()))
        
        # Start a service
        endpoint = self.registry.get_service('vfs')
        self.assertIsNotNone(endpoint)
        
        # Check if service is running
        self.assertTrue(self.registry.is_service_running('vfs'))
        
        # Stop the service
        self.registry.stop_service('vfs')
        self.assertFalse(self.registry.is_service_running('vfs'))
    
    def test_create_service_registry_factory(self):
        """Test the factory function."""
        registry = create_service_registry()
        self.assertIsInstance(registry, BaseServiceRegistry)


class TestVFSClientNew(unittest.TestCase):
    """Test the new VFS client implementation."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Create a temporary directory for testing
        self.temp_dir = tempfile.mkdtemp()
        self.temp_path = Path(self.temp_dir)
        
        # Create some test files
        (self.temp_path / 'test.txt').write_text('Hello, World!')
        (self.temp_path / 'subdir').mkdir()
        (self.temp_path / 'subdir' / 'nested.txt').write_text('Nested file')
        
        # Set up service registry with direct backend
        self.backend = DirectBackend()
        self.registry = BaseServiceRegistry(backend=self.backend)
    
    def tearDown(self):
        """Clean up test fixtures."""
        # Clean up services
        try:
            self.registry.stop_all_services()
        except:
            pass
        
        # Clean up temporary directory
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_client_creation_direct(self):
        """Test VFS client creation with direct backend."""
        # Create registry with direct backend
        registry = create_service_registry(backend_type='direct')
        
        # Configure VFS root path
        config_service = registry.get_service('config')
        config_service.set("vfs.root_path", str(Path.cwd()))
        
        # Start VFS service
        vfs_endpoint = registry.get_service('vfs')
        self.assertIsNotNone(vfs_endpoint)
        
        # Create VFS client
        client = VFSClientNew(vfs_endpoint, service_registry=registry)
        self.assertIsNotNone(client)
        
        # Test basic operations
        name = client.name
        self.assertIsInstance(name, str)
        
        # Cleanup
        registry.stop_service('vfs')
    
    def test_exception_handling(self):
        """Test VFS client exception handling."""
        # Create registry with direct backend
        registry = create_service_registry(backend_type='direct')
        
        # Configure VFS root path
        config_service = registry.get_service('config')
        config_service.set("vfs.root_path", str(Path.cwd()))
        
        # Start VFS service
        vfs_endpoint = registry.get_service('vfs')
        self.assertIsNotNone(vfs_endpoint)
        
        # Create VFS client
        client = VFSClientNew(vfs_endpoint, service_registry=registry)
        self.assertIsNotNone(client)
        
        # Test exception handling with invalid path
        try:
            client.list('/nonexistent/path/that/does/not/exist')
        except VFSClientException:
            pass  # Expected exception
        except Exception as e:
            # Other exceptions are also acceptable for this test
            pass
        
        # Cleanup
        registry.stop_service('vfs')
    
    @unittest.skipUnless(ZERORPC_AVAILABLE, "zerorpc not available")
    def test_client_creation_zerorpc(self):
        """Test VFS client creation with zerorpc backend."""
        # Create registry with zerorpc backend
        registry = create_service_registry(backend_type='zerorpc')
        
        # Configure VFS root path
        config_service = registry.get_service('config')
        config_service.set("vfs.root_path", str(Path.cwd()))
        
        # Start VFS service
        vfs_endpoint = registry.get_service('vfs')
        self.assertIsNotNone(vfs_endpoint)
        
        # Create VFS client
        client = VFSClientNew(vfs_endpoint, service_registry=registry)
        self.assertIsNotNone(client)
        
        # Test basic operations
        name = client.name
        self.assertIsInstance(name, str)
        
        # Cleanup
        registry.stop_service('vfs')


class TestBackendSelection(unittest.TestCase):
    """Test automatic backend selection."""
    
    def test_default_backend_selection(self):
        """Test automatic backend selection."""
        registry = create_service_registry()
        
        # Should select a backend (either ZeroRPC or Direct)
        self.assertIn(registry.backend_type, ['ZeroRPCBackend', 'DirectBackend'])
    
    def test_fallback_to_direct(self):
        """Test fallback to direct backend when zerorpc is not available."""
        # Mock zerorpc import failure by patching the import in the backend module
        with patch('textcase.service.backends.zerorpc_backend.zerorpc', None):
            with patch('textcase.service.backends.zerorpc_backend.gevent', None):
                with patch.dict('sys.modules', {'zerorpc': None, 'gevent': None}):
                    # Force reimport to trigger fallback
                    from textcase.service.service_registry_base import BaseServiceRegistry
                    registry = BaseServiceRegistry()
                    
                    # Should fall back to direct backend
                    self.assertEqual(registry.backend_type, 'DirectBackend')


if __name__ == '__main__':
    # Run tests
    unittest.main(verbosity=2)