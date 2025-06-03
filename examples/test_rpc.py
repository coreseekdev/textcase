import time
import logging
import threading
import sys

# Configure logging to show debug messages
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stdout
)

logger = logging.getLogger('test_rpc')

from textcase.cli import TextCaseClient

def test_rpc():
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    try:
        # First client will start the inproc server
        client1 = TextCaseClient()
        result1 = client1.hello()
        print(f"First RPC call result: {result1}")
        
        # Second client will reuse the same connection
        client2 = TextCaseClient()
        result2 = client2.hello()
        print(f"Second RPC call result: {result2}")
        
        assert result1 == "hello world", f"Expected 'hello world', got '{result1}'"
        assert result2 == "hello world", f"Expected 'hello world', got '{result2}'"
        
        print("✅ RPC test passed!")
        
    except Exception as e:
        print(f"❌ RPC test failed: {e}")
        raise

if __name__ == "__main__":
    test_rpc()
