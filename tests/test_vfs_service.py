#!/usr/bin/env python3
"""Test VFS service functionality."""

import unittest
import tempfile
import os
import sys
from pathlib import Path

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from textcase.core import VFSService, LocalFS, GitRepoFS, EditManager
from pathlib import PurePosixPath


class TestVFSService(unittest.TestCase):
    """Test VFS service functionality."""
    
    def setUp(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.vfs_service = VFSService(self.temp_dir)
        
        # Create test files
        self.test_file = os.path.join(self.temp_dir, "test.txt")
        with open(self.test_file, 'w') as f:
            f.write("Hello, World!\nThis is a test file.")
        
        self.test_dir = os.path.join(self.temp_dir, "subdir")
        os.makedirs(self.test_dir)
        
        self.sub_file = os.path.join(self.test_dir, "sub.txt")
        with open(self.sub_file, 'w') as f:
            f.write("Subdirectory file content.")
    
    def tearDown(self):
        """Clean up test environment."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_service_name(self):
        """Test service name method."""
        result = self.vfs_service.name()
        self.assertEqual(result, "VFSService")
    
    def test_info(self):
        """Test file info method."""
        result = self.vfs_service.info("/test.txt")
        self.assertTrue(result['success'])
        self.assertEqual(result['info']['type'], 'file')
        self.assertIn('size', result['info'])
    
    def test_list(self):
        """Test directory listing."""
        result = self.vfs_service.list("/")
        self.assertTrue(result['success'])
        self.assertIn('/test.txt', result['items'])
        self.assertIn('/subdir', result['items'])
    
    def test_get_text(self):
        """Test reading file as text."""
        result = self.vfs_service.get_text("/test.txt")
        self.assertTrue(result['success'])
        self.assertIn("Hello, World!", result['content'])
    
    def test_put_and_get(self):
        """Test writing and reading file."""
        # Write a new file
        put_result = self.vfs_service.put("/new_file.txt", "New file content!", "text")
        self.assertTrue(put_result['success'])
        
        # Read it back
        get_result = self.vfs_service.get_text("/new_file.txt")
        self.assertTrue(get_result['success'])
        self.assertEqual(get_result['content'], "New file content!")
    
    def test_patch_operations(self):
        """Test patch operations."""
        # Create a session
        session_result = self.vfs_service.create_session("test_session")
        self.assertTrue(session_result['success'])
        session_id = session_result['session_id']
        
        # Apply a patch
        patch_result = self.vfs_service.patch("/test.txt", 0, 5, "Hi", session_id, "text")
        self.assertTrue(patch_result['success'])
        
        # Read file with patch applied
        patched_content = self.vfs_service.get_text("/test.txt")
        self.assertTrue(patched_content['success'])
        self.assertTrue(patched_content['content'].startswith("Hi"))
        
        # Commit the patch
        commit_result = self.vfs_service.commit(session_id=session_id)
        self.assertTrue(commit_result['success'])
        
        # Verify the change is persisted
        final_content = self.vfs_service.get_text("/test.txt")
        self.assertTrue(final_content['success'])
        self.assertTrue(final_content['content'].startswith("Hi"))
    
    def test_session_management(self):
        """Test session management."""
        # Create a session
        session_result = self.vfs_service.create_session("test_session")
        self.assertTrue(session_result['success'])
        session_id = session_result['session_id']
        
        # List sessions
        sessions_result = self.vfs_service.list_sessions()
        self.assertTrue(sessions_result['success'])
        self.assertEqual(len(sessions_result['sessions']), 1)
        self.assertEqual(sessions_result['sessions'][0]['session_id'], session_id)
        
        # Close session
        close_result = self.vfs_service.close_session(session_id)
        self.assertTrue(close_result['success'])
        
        # Verify session is closed
        sessions_result = self.vfs_service.list_sessions()
        self.assertTrue(sessions_result['success'])
        self.assertEqual(len(sessions_result['sessions']), 0)


class TestLocalFS(unittest.TestCase):
    """Test LocalFS functionality."""
    
    def setUp(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.edit_manager = EditManager(os.path.join(self.temp_dir, '.patches'))
        self.local_fs = LocalFS(self.temp_dir, self.edit_manager)
        
        # Create test file
        self.test_file = os.path.join(self.temp_dir, "test.txt")
        with open(self.test_file, 'w') as f:
            f.write("Original content")
    
    def tearDown(self):
        """Clean up test environment."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_name(self):
        """Test VFS name."""
        name = self.local_fs.name()
        self.assertTrue(name.startswith("local:"))
    
    def test_readonly(self):
        """Test readonly property."""
        self.assertFalse(self.local_fs.readonly())
    
    def test_info(self):
        """Test file info."""
        info = self.local_fs.info(PurePosixPath("test.txt"))
        self.assertEqual(info['type'], 'file')
        self.assertIn('size', info)
    
    def test_list(self):
        """Test directory listing."""
        items = self.local_fs.list(PurePosixPath("."))
        self.assertIn(PurePosixPath("test.txt"), items)
    
    def test_get_put(self):
        """Test get and put operations."""
        # Read existing file
        content = self.local_fs.get(PurePosixPath("test.txt"))
        self.assertEqual(content, b"Original content")
        
        # Write new file
        self.local_fs.put(PurePosixPath("new.txt"), b"New content")
        
        # Read new file
        new_content = self.local_fs.get(PurePosixPath("new.txt"))
        self.assertEqual(new_content, b"New content")
    
    def test_patch_commit_abort(self):
        """Test patch, commit, and abort operations."""
        # Apply a patch
        op_id = self.local_fs.patch(PurePosixPath("test.txt"), (0, 8), b"Modified")
        self.assertIsInstance(op_id, str)
        
        # Read with patch applied
        patched_content = self.local_fs.get(PurePosixPath("test.txt"))
        self.assertEqual(patched_content, b"Modified content")
        
        # Commit the patch
        success, message = self.local_fs.commit(op_id)
        self.assertTrue(success)
        
        # Verify the change is persisted
        with open(self.test_file, 'rb') as f:
            file_content = f.read()
        self.assertEqual(file_content, b"Modified content")
        
        # Test abort with a new patch
        op_id2 = self.local_fs.patch(PurePosixPath("test.txt"), (0, 8), b"Aborted")
        
        # Abort the patch
        success, message = self.local_fs.abort(op_id2)
        self.assertTrue(success)
        
        # Verify the change is not applied
        final_content = self.local_fs.get(PurePosixPath("test.txt"))
        self.assertEqual(final_content, b"Modified content")  # Should still be the committed version


if __name__ == '__main__':
    unittest.main()