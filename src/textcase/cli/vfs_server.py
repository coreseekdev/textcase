#!/usr/bin/env python3
"""VFS Server CLI tool."""

import argparse
import sys
import os
import signal
import time
from pathlib import Path

from textcase.core.service_registry import create_service_registry
from textcase.core.services import default_service_factory
from textcase.core.config import ConfigService, setup_vfs_config


# Global service registry for signal handler
_global_service_registry = None

def signal_handler(signum, frame):
    """Handle shutdown signals."""
    print("\nShutting down VFS server...")
    if _global_service_registry:
        _global_service_registry.stop_all_services()
    sys.exit(0)


def start_vfs_server(root_path: str, port: int = 8000, service_name: str = "vfs"):
    """Start VFS server.
    
    Args:
        root_path: Root path for the VFS
        port: Port to bind the service (for TCP)
        service_name: Name of the service to start
    """
    # Create service registry instance
    global _global_service_registry
    service_registry = create_service_registry()
    _global_service_registry = service_registry
    
    # Validate root path
    if not os.path.exists(root_path):
        print(f"Error: Root path does not exist: {root_path}")
        return 1
    
    root_path = os.path.abspath(root_path)
    print(f"Starting VFS server with root: {root_path}")
    
    # Set up signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        # Update the VFS service factory to use the specified root path
        from textcase.core.services import _service_factories
        from textcase.core.vfs_service import VFSService
        
        def create_custom_vfs_service(service_name: str) -> VFSService:
            return VFSService(root_path)
        
        # Override the factory
        _service_factories[service_name] = create_custom_vfs_service
        
        # Start the service
        if port:
            # Use TCP endpoint
            endpoint = f"tcp://0.0.0.0:{port}"
            service_endpoint = service_registry.get_service(service_name, endpoint)
        else:
            # Use default inproc endpoint
            service_endpoint = service_registry.get_service(service_name)
        
        print(f"VFS service '{service_name}' started at: {service_endpoint}")
        print(f"Root path: {root_path}")
        
        if port:
            print(f"\nVFS server is running on port {port}")
            print("You can connect using:")
            print(f"  zerorpc tcp://localhost:{port} <method> [args...]")
            print("\nAvailable methods:")
            print("  name() - Get service name")
            print("  mounts() - List mount points")
            print("  list(path) - List directory contents")
            print("  info(path) - Get path information")
            print("  get_text(path) - Get file content as text")
            print("  put(path, content, 'text') - Write file content")
            print("\nExample:")
            print(f"  zerorpc tcp://localhost:{port} list '/'")
        
        print("\nPress Ctrl+C to stop the server")
        
        # Keep the server running
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            pass
        
    except Exception as e:
        print(f"Error starting VFS server: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    finally:
        print("\nStopping VFS server...")
        service_registry.stop_all_services()
    
    return 0


def create_argument_parser() -> argparse.ArgumentParser:
    """Create command line argument parser.
    
    Returns:
        Configured argument parser
    """
    parser = argparse.ArgumentParser(
        description='TextCase VFS Server - Virtual File System service',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  vfs_server.py /path/to/project
  vfs_server.py /path/to/git/repo --service git-repo --port 8001
  vfs_server.py . --service localfs --port 9000
  vfs_server.py --config /path/to/config.yml

Service types:
  vfs       - Auto-detect VFS type (default)
  localfs   - Local file system VFS
  git-repo  - Git repository VFS
        """
    )
    
    parser.add_argument(
        'root_path',
        nargs='?',
        help='Root path for VFS operations (default: current directory)'
    )
    
    parser.add_argument(
        '--port', '-p',
        type=int,
        help='Port to bind the service (default: from config or 8000)'
    )
    
    parser.add_argument(
        '--service', '-s',
        choices=['vfs', 'localfs', 'git-repo'],
        help='Service type (default: from config or vfs)'
    )
    
    parser.add_argument(
        '--host',
        help='Host to bind the service (default: from config or localhost)'
    )
    
    parser.add_argument(
        '--log-level',
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
        help='Logging level'
    )
    
    parser.add_argument(
        '--config', '-c',
        help='Configuration file path'
    )
    
    return parser


def main():
    """Main entry point for VFS server."""
    # Parse command line arguments
    parser = create_argument_parser()
    args = parser.parse_args()
    
    # Create service registry instance
    global _global_service_registry
    service_registry = create_service_registry(args.config if hasattr(args, 'config') else None)
    _global_service_registry = service_registry
    
    # Get configuration service from service registry
    config_service = service_registry.config_service
    
    # Setup VFS configuration with environment variables
    vfs_config = setup_vfs_config(
        config_service=config_service,
        root_path=None,  # Don't set root_path here, will set manually below
        load_env=True
    )
    
    # Manually set root_path from command line arguments
    if args.root_path:
        vfs_config.set_root_path(args.root_path, is_default=False)
    
    # Write other command line arguments to configuration
    if args.port:
        config_service.set_temporary('services.default_port', args.port)
    if args.service:
        config_service.set_temporary('services.type', args.service)
    if args.host:
        config_service.set_temporary('services.bind_host', args.host)
    if hasattr(args, 'log_level') and args.log_level:
        config_service.set_temporary('logging.level', args.log_level)
    
    # Get final configuration values
    root_path = vfs_config.get_root_path()
    port = config_service.get('services.default_port', 8000)
    service_type = config_service.get('services.type', 'vfs')
    
    # Validate root path
    if not vfs_config.validate_root_path():
        print(f"Error: Root path does not exist or is not accessible: {root_path}")
        return 1
    
    # Print configuration summary
    vfs_config.print_summary()
    
    return start_vfs_server(root_path, port, service_type)


if __name__ == "__main__":
    sys.exit(main())