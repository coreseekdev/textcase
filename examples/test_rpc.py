# examples/test_rpc.py
import sys
import logging
from textcase.cli.client import TextCaseClient

def test_textcase_rpc():
    """Test the TextCase RPC client."""
    print("Starting TextCase RPC test...")
    
    # Create client 1
    client1 = TextCaseClient()
    print("Client 1 created")
    
    try:
        # Test RPC call
        result = client1.hello()
        print(f"RPC call result: {result}")
        assert result == "hello world", f"Unexpected result: {result}"
        
        # Create client 2 (should reuse the same connection)
        client2 = TextCaseClient()
        print("Client 2 created")
        
        # Test RPC call on client 2
        result = client2.hello()
        print(f"Client 2 RPC call result: {result}")
        
        print("✓ All tests passed!")
        return True
    except Exception as e:
        print(f"❌ Test failed: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return False
    finally:
        # Clean up
        del client1
        if 'client2' in locals():
            del client2

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    test_textcase_rpc()