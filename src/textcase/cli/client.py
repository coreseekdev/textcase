import zerorpc
import logging
import threading
from typing import Any, Optional, Callable
from textcase.core import start_server

class TextCaseClient:
    _instance = None
    _server_thread = None
    _server_running = False
    _clients_count = 0
    _lock = threading.Lock()

    def __new__(cls, endpoint: str = "inproc://textcase"):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(TextCaseClient, cls).__new__(cls)
                cls._instance.endpoint = endpoint
                cls._instance.client = None
                cls._instance._start_server()
                cls._instance._connect()
            cls._clients_count += 1
            return cls._instance

    def __init__(self, endpoint: str = "inproc://textcase"):
        # Initialization is handled in __new__
        pass
    
    def _start_server(self):
        """Start the inproc server in a separate thread"""
        if not self._server_running:
            self._server_thread = threading.Thread(
                target=start_server,
                args=(self.endpoint,),
                daemon=True
            )
            self._server_thread.start()
            self._server_running = True
            logging.debug(f"Started inproc TextCase RPC server on {self.endpoint}")
    
    def _connect(self):
        """Establish connection to the RPC server"""
        try:
            self.client = zerorpc.Client(heartbeat=None, timeout=10)
            self.client.connect(self.endpoint)
            logging.debug(f"Connected to TextCase RPC server at {self.endpoint}")
        except Exception as e:
            logging.error(f"Failed to connect to RPC server: {e}")
            self._server_running = False
            if self._server_thread:
                self._server_thread.join(timeout=1)
            raise
    
    def hello(self) -> str:
        """Call the hello RPC method
        
        Returns:
            str: The response from the server
        """
        try:
            return self.client.hello()
        except Exception as e:
            logging.error(f"RPC call failed: {e}")
            raise

def create_client(endpoint: str = "inproc://textcase") -> TextCaseClient:
    """Create a new TextCase RPC client
    
    Args:
        endpoint (str): The zerorpc server endpoint to connect to
        
    Returns:
        TextCaseClient: An instance of the RPC client
    """
    return TextCaseClient(endpoint=endpoint)

if __name__ == "__main__":
    # Example usage
    logging.basicConfig(level=logging.INFO)
    client = create_client()
    try:
        result = client.hello()
        print(f"Server response: {result}")
    except Exception as e:
        print(f"Error: {e}")
