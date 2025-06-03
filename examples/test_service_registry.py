# examples/test_service_registry.py
import time
import logging
import sys
import threading
import zerorpc
from textcase.core import service_registry, ServiceRegistry

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stdout
)

def test_service_registry():
    # Get the service registry (singleton)
    registry = ServiceRegistry()
    
    print("\n--- Test 1: Get or create a service ---")
    endpoint1 = registry.get_service("test_service_1")
    print(f"✓ Created service 'test_service_1' at {endpoint1}")
    
    print("\n--- Test 2: Get the same service again ---")
    endpoint1_again = registry.get_service("test_service_1")
    print(f"✓ Retrieved service 'test_service_1' at {endpoint1_again}")
    assert endpoint1 == endpoint1_again, "Should return the same endpoint for the same service"
    
    print("\n--- Test 3: Create a second service with custom endpoint ---")
    custom_endpoint = "inproc://custom_service"
    endpoint2 = registry.get_service("test_service_2", custom_endpoint)
    print(f"✓ Created service 'test_service_2' at {endpoint2}")
    assert endpoint2 == custom_endpoint, "Should use custom endpoint when provided"
    
    print("\n--- Test 4: Verify services are running ---")
    assert registry.is_service_running("test_service_1"), "test_service_1 should be running"
    assert registry.is_service_running("test_service_2"), "test_service_2 should be running"
    print("✓ Both services are running")
    
    print("\n--- Test 5: Stop a specific service ---")
    registry.stop_service("test_service_1")
    assert not registry.is_service_running("test_service_1"), "test_service_1 should be stopped"
    print("✓ Successfully stopped test_service_1")
    
    print("\n--- Test 6: Stop all services ---")
    registry.stop_all_services()
    assert not registry.is_service_running("test_service_2"), "All services should be stopped"
    print("✓ Successfully stopped all services")
    
    print("\n--- Test 7: Test with actual RPC call ---")
    # Create a simple RPC service
    class TestService:
        def hello(self, name):
            return f"Hello, {name}!"
    
    # Create a service with our custom handler
    endpoint = registry.get_service(
        "rpc_test",
        service_factory=lambda name: TestService()
    )
    
    try:
        # Create a client and test the RPC call
        client = zerorpc.Client()
        client.connect(endpoint)
        
        result = client.hello("World")
        print(f"✓ RPC call successful. Result: {result}")
        assert result == "Hello, World!", "Unexpected RPC result"
        
    except Exception as e:
        print(f"✗ RPC call failed: {e}")
        raise
    finally:
        # Clean up
        registry.stop_all_services()

def test_service_registry_singleton():
    """Test that ServiceRegistry is a singleton"""
    registry1 = ServiceRegistry()
    registry2 = ServiceRegistry()
    assert registry1 is registry2, "ServiceRegistry should be a singleton"
    
    # Also test the module-level instance
    assert registry1 is service_registry, "Module-level instance should be the same"

if __name__ == "__main__":
    print("Starting ServiceRegistry tests...")
    try:
        print("\n=== Testing ServiceRegistry singleton ===")
        test_service_registry_singleton()
        print("✓ Singleton test passed")
        
        print("\n=== Testing ServiceRegistry functionality ===")
        test_service_registry()
        print("✓ Functionality tests passed")
        
        print("\n✅ All tests passed!")
    except Exception as e:
        print(f"\n❌ Test failed: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)