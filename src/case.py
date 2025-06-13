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
    
    # Test get README.md
    print("\nTesting get README.md:")
    try:
        readme_content = vfs.get('/README.md')
        if isinstance(readme_content, bytes):
            # Handle bytes content
            readme_text = readme_content.decode('utf-8')
            print(f"README.md content (first 200 chars): {readme_text[:200]}...")
        else:
            # Handle string content
            print(f"README.md content (first 200 chars): {readme_content[:200]}...")
    except Exception as e:
        print(f"Error getting README.md: {e}")
    
    # Test put TEST.md
    print("\nTesting put TEST.md:")
    try:
        test_content = "# Test File\n\nThis is a test file created by case.py script.\n\n- Item 1\n- Item 2\n- Item 3\n"
        
        # Try to put as string first (VFS expects bytes, so this should fail)
        try:
            vfs.put('/TEST.md', test_content, True)  # create_if_missing=True
            print("Successfully put TEST.md as string")
        except Exception as string_error:
            print(f"Failed to put as string: {string_error}")
            
            # Try to put as bytes with create_if_missing=True
            try:
                test_content_bytes = test_content.encode('utf-8')
                result = vfs.put('/TEST.md', test_content_bytes, True)  # create_if_missing=True
                print(f"Successfully put TEST.md as bytes, result: {result}")
            except Exception as bytes_error:
                print(f"Failed to put as bytes: {bytes_error}")
                raise
        
        # Verify the file was created
        print("Verifying TEST.md was created:")
        entries_after = vfs.list('/')
        print(f"Entries after put: {entries_after[:5]}...")  # Show first 5 entries for debugging
        
        # Check for TEST.md in different ways
        test_found_exact = any('TEST.md' in str(entry) for entry in entries_after)
        test_found_path = any('/TEST.md' in str(entry) for entry in entries_after)
        print(f"TEST.md found (exact): {test_found_exact}")
        print(f"TEST.md found (with path): {test_found_path}")
        
        # Try to read back the content directly
        print("Attempting to read back TEST.md:")
        try:
            read_back = vfs.get('/TEST.md')
            if isinstance(read_back, bytes):
                read_back_text = read_back.decode('utf-8')
                print(f"Successfully read back TEST.md as bytes: {read_back_text[:100]}...")
            else:
                print(f"Successfully read back TEST.md as string: {read_back[:100]}...")
        except Exception as read_error:
            print(f"Error reading back TEST.md: {read_error}")
            
            # Try without leading slash
            try:
                read_back2 = vfs.get('TEST.md')
                if isinstance(read_back2, bytes):
                    read_back_text2 = read_back2.decode('utf-8')
                    print(f"Successfully read back TEST.md (no slash) as bytes: {read_back_text2[:100]}...")
                else:
                    print(f"Successfully read back TEST.md (no slash) as string: {read_back2[:100]}...")
            except Exception as read_error2:
                print(f"Error reading back TEST.md (no slash): {read_error2}")
        
    except Exception as e:
        print(f"Error putting TEST.md: {e}")
    
    # Stop services
    print("\nStopping services...")
    textcase.stop_services()
    print("Services stopped")
    
    print("=== Test completed ===")

if __name__ == '__main__':
    main()