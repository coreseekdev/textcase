#!/usr/bin/env python3
"""Example demonstrating VFS service usage."""

import sys
import os
import time
import tempfile
from pathlib import Path

# Add the src directory to the path so we can import textcase
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from textcase.core import service_registry
from textcase.cli.client import TextCaseClient
import zerorpc


def test_vfs_service():
    """Test the VFS service functionality."""
    print("=== VFS Service Test ===")
    
    # Create a temporary directory for testing
    with tempfile.TemporaryDirectory() as temp_dir:
        print(f"Using temporary directory: {temp_dir}")
        
        # Create some test files
        test_file = os.path.join(temp_dir, "test.txt")
        with open(test_file, 'w') as f:
            f.write("Hello, VFS World!\nThis is a test file.")
        
        test_dir = os.path.join(temp_dir, "subdir")
        os.makedirs(test_dir)
        
        sub_file = os.path.join(test_dir, "sub.txt")
        with open(sub_file, 'w') as f:
            f.write("This is a subdirectory file.")
        
        # Start VFS service
        print("\n1. Starting VFS service...")
        endpoint = service_registry.get_service("vfs")
        print(f"VFS service started at: {endpoint}")
        
        # Connect to the service
        client = zerorpc.Client()
        client.connect(endpoint)
        
        try:
            # Test service name
            print("\n2. Testing service name...")
            name = client.name()
            print(f"Service name: {name}")
            
            # Test mount operations
            print("\n3. Testing mount operations...")
            
            # Mount the temp directory
            result = client.mount("/test", temp_dir)
            print(f"Mount result: {result}")
            
            # List mounts
            mounts_result = client.mounts()
            print(f"Current mounts: {mounts_result}")
            
            # Test file operations
            print("\n4. Testing file operations...")
            
            # List root directory
            list_result = client.list("/test")
            print(f"Root directory listing: {list_result}")
            
            # Get file info
            info_result = client.info("/test/test.txt")
            print(f"File info: {info_result}")
            
            # Read file content
            content_result = client.get_text("/test/test.txt")
            print(f"File content: {content_result}")
            
            # Test patch operations
            print("\n5. Testing patch operations...")
            
            # Create a session
            session_result = client.create_session("test_session")
            print(f"Session created: {session_result}")
            session_id = session_result.get('session_id')
            
            # Apply a patch
            patch_result = client.patch("/test/test.txt", 0, 5, "Hi", session_id, "text")
            print(f"Patch applied: {patch_result}")
            
            # Read file with patch applied
            patched_content = client.get_text("/test/test.txt")
            print(f"Patched content: {patched_content}")
            
            # Commit the patch
            commit_result = client.commit(session_id=session_id)
            print(f"Commit result: {commit_result}")
            
            # Read file after commit
            final_content = client.get_text("/test/test.txt")
            print(f"Final content: {final_content}")
            
            # Test put operation
            print("\n6. Testing put operation...")
            put_result = client.put("/test/new_file.txt", "This is a new file!", "text")
            print(f"Put result: {put_result}")
            
            # Verify the new file
            new_file_content = client.get_text("/test/new_file.txt")
            print(f"New file content: {new_file_content}")
            
            # Test directory listing with new file
            final_list = client.list("/test")
            print(f"Final directory listing: {final_list}")
            
            print("\n✓ All VFS tests passed!")
            
        except Exception as e:
            print(f"\n✗ VFS test failed: {e}")
            import traceback
            traceback.print_exc()
        
        finally:
            client.close()


def test_git_repo_vfs():
    """Test VFS with a git repository."""
    print("\n=== Git Repo VFS Test ===")
    
    # Check if we're in a git repository
    current_dir = os.getcwd()
    git_dir = os.path.join(current_dir, '.git')
    
    if not os.path.exists(git_dir):
        print("Not in a git repository, skipping git repo test.")
        return
    
    print(f"Testing with git repository: {current_dir}")
    
    # Start VFS service
    endpoint = service_registry.get_service("git-repo")
    
    # Connect to the service
    client = zerorpc.Client()
    client.connect(endpoint)
    
    try:
        # Mount the current git repo
        result = client.mount("/repo", current_dir)
        print(f"Mount result: {result}")
        
        # List repository root
        list_result = client.list("/repo")
        print(f"Repository listing: {list_result}")
        
        # Try to access a git tree (if we have commits)
        try:
            import subprocess
            # Get the latest commit hash
            result = subprocess.run(['git', 'rev-parse', 'HEAD'], 
                                  capture_output=True, text=True, cwd=current_dir)
            if result.returncode == 0:
                commit_hash = result.stdout.strip()
                print(f"Latest commit: {commit_hash}")
                
                # List git tree
                git_tree_list = client.list(f"/repo/.git/{commit_hash}")
                print(f"Git tree listing: {git_tree_list}")
                
                # Try to read a file from git tree
                if git_tree_list.get('success') and git_tree_list.get('items'):
                    first_item = git_tree_list['items'][0]
                    if not first_item.endswith('/'):
                        git_file_content = client.get_text(f"/repo/.git/{commit_hash}/{first_item}")
                        print(f"Git file content preview: {str(git_file_content)[:200]}...")
        
        except Exception as e:
            print(f"Git tree access test failed: {e}")
        
        print("\n✓ Git repo VFS test completed!")
        
    except Exception as e:
        print(f"\n✗ Git repo VFS test failed: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        client.close()


def main():
    """Run VFS service examples."""
    print("VFS Service Examples")
    print("====================")
    
    try:
        # Test basic VFS functionality
        test_vfs_service()
        
        # Test git repository functionality
        test_git_repo_vfs()
        
    except KeyboardInterrupt:
        print("\nInterrupted by user")
    except Exception as e:
        print(f"\nExample failed: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # Clean up services
        print("\nCleaning up services...")
        service_registry.stop_all_services()
        print("Done.")


if __name__ == "__main__":
    main()