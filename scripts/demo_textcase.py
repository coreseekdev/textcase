#!/usr/bin/env python3
"""
TextCase Demo Script

This script demonstrates how to use TextCase and TextCaseFactory.
"""

import os
import sys
from pathlib import Path

# Add src to Python path
script_dir = Path(__file__).parent
project_root = script_dir.parent
src_path = project_root / "src"
sys.path.insert(0, str(src_path))

from textcase.textcase import TextCaseFactory, TextCase


def main():
    """Demonstrate TextCase usage."""
    print("TextCase Demo")
    print("=============")
    
    # Get current project root as demo repository
    repo_root = str(project_root)
    print(f"Using repository root: {repo_root}")
    
    # Create TextCase factory
    print("\n1. Creating TextCase factory...")
    factory = TextCaseFactory()
    print(f"Factory created: {factory}")
    
    # Create TextCase instance
    print("\n2. Creating TextCase instance...")
    textcase = factory.create(repo_root)
    print(f"TextCase created: {textcase}")
    
    # Display repository information
    print("\n3. Repository information:")
    repo_info = textcase.get_repo_info()
    for key, value in repo_info.items():
        if key == 'git_info' and value:
            print(f"  {key}:")
            for git_key, git_value in value.items():
                print(f"    {git_key}: {git_value}")
        else:
            print(f"  {key}: {value}")
    
    # Display configuration
    print("\n4. Configuration:")
    vfs_root = textcase.get_config_value('vfs.root_path')
    vfs_git_enabled = textcase.get_config_value('vfs.enable_git_repo')
    print(f"  VFS Root Path: {vfs_root}")
    print(f"  VFS Git Enabled: {vfs_git_enabled}")
    
    # Test configuration setting
    print("\n5. Testing configuration setting:")
    old_value = textcase.set_config_value('demo.test_key', 'test_value')
    new_value = textcase.get_config_value('demo.test_key')
    print(f"  Set 'demo.test_key' to '{new_value}' (previous: {old_value})")
    
    # Start services
    print("\n6. Starting services...")
    try:
        textcase.start_services()
        print("  Services started successfully")
        
        # Get VFS endpoint
        vfs_endpoint = textcase.get_vfs_endpoint()
        print(f"  VFS endpoint: {vfs_endpoint}")
        
    except Exception as e:
        print(f"  Error starting services: {e}")
    finally:
        # Stop services
        print("\n7. Stopping services...")
        try:
            textcase.stop_services()
            print("  Services stopped successfully")
        except Exception as e:
            print(f"  Error stopping services: {e}")
    
    print("\nDemo completed!")


if __name__ == "__main__":
    main()