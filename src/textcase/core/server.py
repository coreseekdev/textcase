import zerorpc
import logging
import time
from typing import Optional

class TextCaseService:
    def hello(self):
        """Simple hello method for testing the RPC service"""
        return "hello world"

def start_server(endpoint: str = "inproc://textcase"):
    """Start the zerorpc server in the current thread
    
    Args:
        endpoint (str): The endpoint to bind the server to
    """
    service = TextCaseService()
    server = zerorpc.Server(service)
    server.bind(endpoint)
    logging.info(f"Starting TextCase RPC server on {endpoint}")
    
    try:
        # Run the server in the current thread
        server.run()
    except KeyboardInterrupt:
        logging.info("Shutting down RPC server...")
    except Exception as e:
        logging.error(f"RPC server error: {e}")
        raise
    finally:
        server.close()

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    start_server()
