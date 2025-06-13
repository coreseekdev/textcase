#!/usr/bin/env python3
"""
Demo script for updated TextCaseFactory and TextCase classes.

This script demonstrates:
1. TextCaseFactory string representation
2. Using get() method with different file paths
3. Automatic Git repository detection
4. Fallback behavior when no Git repository is found
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
    print("=== TextCaseFactory Updated Demo ===")
    print()
    
    # Test 1: Factory string representation
    print("1. Testing TextCaseFactory string representation:")
    factory_default = TextCaseFactory()
    factory_with_config = TextCaseFactory('/path/to/config.yml')
    
    print(f"   Default factory: {factory_default}")
    print(f"   Factory with config: {factory_with_config}")
    print()
    
    # Test 2: Get TextCase from project root (should find Git repo)
    print("2. Testing get() with project root (Git repo):")
    try:
        textcase_from_root = factory_default.get(project_root)
        repo_info = textcase_from_root.get_repo_info()
        
        print(f"   TextCase instance: {textcase_from_root}")
        print(f"   Repository root: {repo_info['repo_root_path']}")
        print(f"   VFS root: {repo_info['vfs_root_path']}")
        
        if repo_info['git_info']:
            git_info = repo_info['git_info']
            print(f"   Git repo root: {git_info['repo_root']}")
            print(f"   Is submodule: {git_info['is_submodule']}")
        else:
            print("   No Git repository detected")
    except Exception as e:
        print(f"   Error: {e}")
    print()
    
    # Test 3: Get TextCase from a file in the project
    print("3. Testing get() with a file path in Git repo:")
    try:
        test_file = project_root / 'src' / 'textcase' / 'textcase.py'
        textcase_from_file = factory_default.get(test_file)
        repo_info = textcase_from_file.get_repo_info()
        
        print(f"   Input file: {test_file}")
        print(f"   TextCase instance: {textcase_from_file}")
        print(f"   Repository root: {repo_info['repo_root_path']}")
        
        if repo_info['git_info']:
            git_info = repo_info['git_info']
            print(f"   Git repo root: {git_info['repo_root']}")
    except Exception as e:
        print(f"   Error: {e}")
    print()
    
    # Test 4: Get TextCase from a non-Git directory (fallback behavior)
    print("4. Testing get() with non-Git directory (fallback):")
    try:
        # Use temp directory or user home as non-Git path
        non_git_path = Path.home()
        textcase_from_non_git = factory_default.get(non_git_path)
        repo_info = textcase_from_non_git.get_repo_info()
        
        print(f"   Input path: {non_git_path}")
        print(f"   TextCase instance: {textcase_from_non_git}")
        print(f"   Repository root: {repo_info['repo_root_path']}")
        
        if repo_info['git_info']:
            git_info = repo_info['git_info']
            print(f"   Git repo root: {git_info['repo_root']}")
        else:
            print("   No Git repository detected (expected for non-Git path)")
    except Exception as e:
        print(f"   Error: {e}")
    print()
    
    # Test 5: Test configuration and services
    print("5. Testing configuration and services:")
    try:
        textcase = factory_default.get(project_root)
        
        # Test configuration
        vfs_root = textcase.get_config_value('vfs.root_path')
        git_enabled = textcase.get_config_value('vfs.enable_git_repo')
        
        print(f"   VFS root path: {vfs_root}")
        print(f"   Git enabled: {git_enabled}")
        
        # Test setting a config value
        old_value = textcase.set_config_value('test.demo_key', 'demo_value')
        new_value = textcase.get_config_value('test.demo_key')
        print(f"   Set test config - old: {old_value}, new: {new_value}")
        
        # Test services
        print("   Starting services...")
        textcase.start_services()
        
        vfs_endpoint = textcase.get_vfs_endpoint()
        print(f"   VFS endpoint: {vfs_endpoint}")
        
        print("   Stopping services...")
        textcase.stop_services()
        print("   Services stopped successfully")
        
    except Exception as e:
        print(f"   Error: {e}")
    
    print()
    print("=== Demo completed ===")

if __name__ == '__main__':
    main()