#!/usr/bin/env python3
"""
Test script for TextCaseFactory and VFS functionality.

This script demonstrates:
1. Creating a TextCase instance from TextCaseFactory
2. Starting VFS services
3. Listing root directory using VFS
4. Stopping services
"""

import sys
import os
from pathlib import Path

# Add the src directory to Python path
project_root = Path(__file__).parent.parent
src_path = project_root / 'src'
sys.path.insert(0, str(src_path))

from textcase.textcase import TextCaseFactory

def main():
    print("=== TextCase VFS Test ===")
    
    # Create TextCaseFactory
    factory = TextCaseFactory()
    
    # Get TextCase instance for current project
    textcase = factory.get(project_root)
    print(f"Created TextCase for: {textcase}")
    
    # Start services
    print("Starting VFS services...")
    textcase.start_services()
    
    # Get VFS endpoint
    vfs_endpoint = textcase.get_vfs_endpoint()
    print(f"VFS endpoint: {vfs_endpoint}")
    
    # Get VFS service
    vfs = textcase.vfs
    
    # List root directory
    print("Listing root directory:")
    try:
        entries = vfs.list('/')
        for entry in entries:
            print(f"  - {entry}")
    except Exception as e:
        print(f"Error listing root directory: {e}")
    
    # Stop services
    print("Stopping services...")
    textcase.stop_services()
    print("Services stopped")
    
    print("=== Test completed ===")

if __name__ == '__main__':
    main()