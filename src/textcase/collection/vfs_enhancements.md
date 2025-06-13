# VFS Client Enhancements for Collection System

## Current VFS Interface Analysis

The current `VFSClient` provides the following operations:

### Available Methods
- `info(path)` - Get path information
- `list(path, option)` - List directory contents
- `get(path)` - Read file as bytes
- `get_text(path, encoding)` - Read file as text
- `put(path, content, create_if_missing)` - Write file
- `patch(path, range_tuple, content, session_id)` - Apply patches
- `commit(message, op_id, session_id)` - Commit changes
- `abort(op_id, session_id)` - Abort changes
- `create_session()` - Create edit session
- `list_sessions()` - List active sessions
- `name()` - Get service name
- `readonly()` - Check if read-only

## Missing Operations for Collection System

The collection system requires additional operations that are not currently available:

### 1. File Deletion
**Required for**: Removing items and tag files

```python
def delete(self, path: Union[str, PurePosixPath]) -> bool:
    """Delete a file or directory.
    
    Args:
        path: Path to delete
        
    Returns:
        True if deletion was successful, False otherwise
        
    Raises:
        VFSClientException: If deletion fails due to permissions or other errors
    """
```

### 2. Directory Creation
**Required for**: Creating collection directories

```python
def mkdir(self, path: Union[str, PurePosixPath], parents: bool = True) -> bool:
    """Create a directory.
    
    Args:
        path: Directory path to create
        parents: Create parent directories if they don't exist
        
    Returns:
        True if creation was successful, False if directory already exists
        
    Raises:
        VFSClientException: If creation fails due to permissions or other errors
    """
```

### 3. Path Existence Check (Convenience)
**Required for**: Simplified existence checking

```python
def exists(self, path: Union[str, PurePosixPath]) -> bool:
    """Check if a path exists.
    
    Args:
        path: Path to check
        
    Returns:
        True if path exists, False otherwise
    """
    try:
        info = self.info(path)
        return info is not None
    except VFSClientException:
        return False
```

### 4. Path Type Checking (Convenience)
**Required for**: Distinguishing files from directories

```python
def is_file(self, path: Union[str, PurePosixPath]) -> bool:
    """Check if path is a file.
    
    Args:
        path: Path to check
        
    Returns:
        True if path is a file, False otherwise
    """
    try:
        info = self.info(path)
        return info and info.get('type') == 'file'
    except VFSClientException:
        return False

def is_dir(self, path: Union[str, PurePosixPath]) -> bool:
    """Check if path is a directory.
    
    Args:
        path: Path to check
        
    Returns:
        True if path is a directory, False otherwise
    """
    try:
        info = self.info(path)
        return info and info.get('type') == 'directory'
    except VFSClientException:
        return False
```

## Current Workarounds in Collection Implementation

Until these enhancements are available, the collection system uses the following workarounds:

### 1. File Deletion Workaround
```python
# In ResourceItemImpl.delete() and ResourceCollectionImpl.remove_tag()
# Currently: pass  # TODO: Implement file deletion when VFS supports it

# Workaround: Mark files for deletion by writing empty content
def _mark_for_deletion(self, path: PurePosixPath) -> None:
    """Mark a file for deletion by writing special content."""
    try:
        self._vfs.put(path, b'# DELETED - Remove this file', create_if_missing=False)
    except VFSClientException:
        pass  # File might not exist
```

### 2. Directory Creation Workaround
```python
# In ResourceCollectionImpl._ensure_directory_exists()
# Currently: pass  # Directory creation assumed to work via put()

# Workaround: Create directory by putting a placeholder file
def _ensure_directory_exists(self) -> None:
    """Ensure collection directory exists by creating a placeholder."""
    placeholder_path = self._path / '.directory_placeholder'
    try:
        info = self._vfs.info(self._path)
        if not info:
            # Create placeholder to ensure directory exists
            self._vfs.put(placeholder_path, b'', create_if_missing=True)
    except VFSClientException:
        # Try to create placeholder anyway
        try:
            self._vfs.put(placeholder_path, b'', create_if_missing=True)
        except VFSClientException:
            pass  # Directory creation failed
```

## Implementation Priority

### High Priority (Critical for Core Functionality)
1. **`delete()`** - Essential for item and tag removal
2. **`mkdir()`** - Essential for collection creation

### Medium Priority (Convenience Methods)
3. **`exists()`** - Can be implemented using `info()` but adds convenience
4. **`is_file()` / `is_dir()`** - Can be implemented using `info()` but adds clarity

## Server-Side Implementation Notes

For the VFS server implementation, these methods would need to:

### `delete(path)`
- Support both file and directory deletion
- Handle recursive directory deletion safely
- Respect VFS mount boundaries
- Integrate with version control systems if applicable

### `mkdir(path, parents=True)`
- Create directory hierarchies
- Handle existing directories gracefully
- Set appropriate permissions
- Integrate with version control systems if applicable

## Backward Compatibility

All proposed enhancements are additive and maintain full backward compatibility with existing VFS client code.

## Testing Requirements

Once these enhancements are implemented, the collection system should be tested with:

1. **File Operations**
   - Create, read, update, delete items
   - Tag file management
   - Configuration file handling

2. **Directory Operations**
   - Collection creation and removal
   - Nested collection hierarchies
   - Path resolution

3. **Error Handling**
   - Permission denied scenarios
   - Non-existent path operations
   - Concurrent access patterns

4. **Integration Testing**
   - Full collection lifecycle
   - Cross-collection operations
   - Manager persistence and recovery