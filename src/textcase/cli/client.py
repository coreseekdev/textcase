import logging
import threading
import zerorpc
from typing import Optional, Any
from ..core.service_registry import service_registry

class TextCaseClient:
    """Client for TextCase RPC service using ServiceRegistry."""
    
    _instance = None
    _lock = threading.Lock()

    def __new__(cls, endpoint: str = "inproc://textcase"):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(TextCaseClient, cls).__new__(cls)
                cls._instance._connect(endpoint)
            return cls._instance

    def _connect(self, endpoint: str):
        """Connect to the RPC server."""
        # Get or create the service
        self.endpoint = service_registry.get_service(
            "test",
            endpoint=endpoint,
        )
        self.client = zerorpc.Client(connect_to=self.endpoint)
        logging.debug(f"Connected to TextCase RPC service on {self.endpoint}")
    
    def hello(self) -> str:
        """Call the hello method on the RPC service."""
        return self.client.hello()
    
    def name(self) -> str:
        """Call the name method on the RPC service."""
        return self.client.name()

    def __getattr__(self, name):
        """Forward method calls to the RPC client."""
        return getattr(self.client, name)

# For backward compatibility
def get_client(endpoint: str = "inproc://textcase") -> TextCaseClient:
    """Get a TextCase RPC client instance."""
    return TextCaseClient(endpoint)

if __name__ == "__main__":
    # Example usage
    logging.basicConfig(level=logging.INFO)
    client = get_client()
    try:
        result = client.hello()
        print(f"Server response: {result}")
    except Exception as e:
        print(f"Error: {e}")
