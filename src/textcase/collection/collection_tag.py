"""Tag Management for Resource Collections

This module provides tag management functionality for resource collections,
encapsulating operations related to specific tag files.
"""

from pathlib import PurePosixPath
from typing import Dict, List, Optional, Set, TypeVar

from ..client import VFSClient, VFSClientException
from ..proto.resource_collection_protocol import ResourceCollection

T = TypeVar('T')


class TagManager:
    """Manager for a specific tag in a resource collection.
    
    This class encapsulates operations related to a specific tag file,
    providing methods to add, remove, and query items associated with the tag.
    """
    
    # File extension for tag files
    TAG_FILE_EXTENSION: str = '.list'
    
    def __init__(self, tag: str, collection: 'ResourceCollection[T]', vfs: VFSClient):
        """Initialize a tag manager.
        
        Args:
            tag: The tag name this manager is responsible for
            collection: The parent collection
            vfs: VFS client for file operations
        """
        self._tag = tag
        self._collection = collection
        self._vfs = vfs
        self._items: Optional[Set[str]] = None  # Cache of item names with this tag
    
    @property
    def tag(self) -> str:
        """Get the tag name."""
        return self._tag
    
    @property
    def tag_file_path(self) -> PurePosixPath:
        """Get the path to the tag file."""
        return self._collection.path / f"{self._tag}{self.TAG_FILE_EXTENSION}"
    
    def exists(self) -> bool:
        """Check if the tag file exists.
        
        Returns:
            True if the tag file exists, False otherwise
        """
        try:
            info = self._vfs.info(self.tag_file_path)
            return info is not None
        except VFSClientException:
            return False
    
    def create(self) -> None:
        """Create the tag file if it doesn't exist."""
        if not self.exists():
            try:
                self._vfs.put(self.tag_file_path, b'', create_if_missing=True)
            except VFSClientException as e:
                raise VFSClientException(
                    'TagCreateError',
                    f'Failed to create tag file {self.tag_file_path}: {e}'
                )
    
    def delete(self) -> bool:
        """Delete the tag file.
        
        Returns:
            True if the file was deleted, False if it didn't exist
        """
        if not self.exists():
            return False
        
        try:
            self._vfs.remove(self.tag_file_path, force=True)
            self._items = None  # Clear cache
            return True
        except VFSClientException:
            return False
    
    def get_items(self) -> Set[str]:
        """Get all item names associated with this tag.
        
        Returns:
            A set of item names that have this tag
        """
        if self._items is not None:
            return self._items.copy()
        
        items = set()
        if self.exists():
            try:
                content = self._vfs.get_text(self.tag_file_path, encoding='utf-8')
                if content:
                    items = {line.strip() for line in content.splitlines() if line.strip()}
            except VFSClientException:
                pass  # Return empty set on error
        
        self._items = items
        return items.copy()
    
    def add_item(self, item_name: str) -> bool:
        """Add an item to this tag.
        
        Args:
            item_name: The name of the item to add
            
        Returns:
            True if the item was added, False if it was already tagged
        """
        items = self.get_items()
        if item_name in items:
            return False
        
        # Add to cache
        items.add(item_name)
        self._items = items
        
        # Update file
        try:
            # Create file if it doesn't exist
            self.create()
            
            # Read existing content
            try:
                content = self._vfs.get_text(self.tag_file_path, encoding='utf-8')
                lines = [line.strip() for line in content.splitlines() if line.strip()]
            except VFSClientException:
                lines = []
            
            # Add item and sort
            if item_name not in lines:
                lines.append(item_name)
                lines.sort()  # Keep sorted for consistency
            
            # Write back to file
            new_content = '\n'.join(lines) + ('\n' if lines else '')
            self._vfs.put(self.tag_file_path, new_content.encode('utf-8'), create_if_missing=True)
            return True
            
        except VFSClientException as e:
            raise VFSClientException(
                'TagUpdateError',
                f'Failed to update tag file {self.tag_file_path}: {e}'
            )
    
    def remove_item(self, item_name: str) -> bool:
        """Remove an item from this tag.
        
        Args:
            item_name: The name of the item to remove
            
        Returns:
            True if the item was removed, False if it wasn't tagged
        """
        items = self.get_items()
        if item_name not in items:
            return False
        
        # Remove from cache
        items.remove(item_name)
        self._items = items
        
        # Update file
        try:
            if not self.exists():
                return False
                
            # Read existing content
            try:
                content = self._vfs.get_text(self.tag_file_path, encoding='utf-8')
                lines = [line.strip() for line in content.splitlines() if line.strip()]
            except VFSClientException:
                return False
            
            # Remove item
            if item_name in lines:
                lines.remove(item_name)
            
            # Write back to file
            new_content = '\n'.join(lines) + ('\n' if lines else '')
            self._vfs.put(self.tag_file_path, new_content.encode('utf-8'), create_if_missing=True)
            return True
            
        except VFSClientException as e:
            raise VFSClientException(
                'TagUpdateError',
                f'Failed to update tag file {self.tag_file_path}: {e}'
            )
    
    def has_item(self, item_name: str) -> bool:
        """Check if an item has this tag.
        
        Args:
            item_name: The name of the item to check
            
        Returns:
            True if the item has this tag, False otherwise
        """
        return item_name in self.get_items()
    
    def clear(self) -> None:
        """Remove all items from this tag."""
        try:
            if self.exists():
                self._vfs.put(self.tag_file_path, b'', create_if_missing=True)
            self._items = set()  # Clear cache
        except VFSClientException as e:
            raise VFSClientException(
                'TagClearError',
                f'Failed to clear tag file {self.tag_file_path}: {e}'
            )


class CollectionTagManager:
    """Manager for all tags in a resource collection.
    
    This class provides a factory for creating TagManager instances
    for specific tags and manages the collection's tag configuration.
    """
    
    def __init__(self, collection: 'ResourceCollection[T]', vfs: VFSClient):
        """Initialize a collection tag manager.
        
        Args:
            collection: The parent collection
            vfs: VFS client for file operations
        """
        self._collection = collection
        self._vfs = vfs
        self._tag_managers: Dict[str, TagManager] = {}
    
    def get_tag_manager(self, tag: str) -> TagManager:
        """Get a tag manager for a specific tag.
        
        Args:
            tag: The tag name
            
        Returns:
            A TagManager instance for the specified tag
        """
        if tag not in self._tag_managers:
            self._tag_managers[tag] = TagManager(tag, self._collection, self._vfs)
        return self._tag_managers[tag]
    
    def add_tag(self, tag: str, description: Optional[str] = None) -> TagManager:
        """Add a new tag to the collection.
        
        Args:
            tag: The tag name
            description: Optional description for the tag
            
        Returns:
            A TagManager instance for the new tag
        """
        # Update config
        config = self._collection.config
        config.tags[tag] = description
        self._collection._save_config() # FIXME: 需要考虑多次修改、添加
        
        # Create tag manager and ensure file exists
        tag_manager = self.get_tag_manager(tag)
        tag_manager.create()
        return tag_manager
    
    def remove_tag(self, tag: str) -> bool:
        """Remove a tag from the collection.
        
        Args:
            tag: The tag name to remove
            
        Returns:
            True if the tag was removed, False if it didn't exist
        """
        config = self._collection.config
        if tag not in config.tags:
            return False
        
        # Remove from all items first
        for item in self._collection.iter_items():
            if item.has_tag(tag):
                item.remove_tag(tag)
        
        # Remove from config
        del config.tags[tag]
        self._collection._save_config()   # FIXME: 考虑多次添加，删除，保存配置的调用外置
        
        # Delete tag file
        tag_manager = self.get_tag_manager(tag)
        tag_manager.delete()
        
        # Remove from cache
        if tag in self._tag_managers:
            del self._tag_managers[tag]
        
        return True
    
    def has_tag(self, tag: str) -> bool:
        """Check if a tag exists in the collection.
        
        Args:
            tag: The tag name to check
            
        Returns:
            True if the tag exists, False otherwise
        """
        return tag in self._collection.config.tags
    
    def list_tags(self) -> List[str]:
        """List all tags in the collection.
        
        Returns:
            A list of tag names
        """
        return list(self._collection.config.tags.keys())
    
    def get_items_by_tag(self, tag: str) -> List[str]:
        """Get all item names that have a specific tag.
        
        Args:
            tag: The tag to filter by
            
        Returns:
            A list of item names with the specified tag
        """
        if not self.has_tag(tag):
            return []
        
        tag_manager = self.get_tag_manager(tag)
        return list(tag_manager.get_items())
    
    def get_item_tags(self, item_name: str) -> Set[str]:
        """Get all tags for an item.
        
        Args:
            item_name: The name of the item
            
        Returns:
            A set of tags associated with the item
        """
        tags = set()
        
        # Check each tag to see if it contains this item
        for tag_name in self.list_tags():
            tag_manager = self.get_tag_manager(tag_name)
            if tag_manager.has_item(item_name):
                tags.add(tag_name)
                
        return tags
    
    def update_item_tag(self, item_name: str, tag: str, add: bool) -> None:
        """Update a tag for an item.
        
        Args:
            item_name: The name of the item
            tag: The tag name
            add: True to add the tag, False to remove it
        """
        if not self.has_tag(tag):
            if not add:
                return  # Nothing to do if removing a non-existent tag
            self.add_tag(tag)  # Create the tag if adding and it doesn't exist
        
        tag_manager = self.get_tag_manager(tag)
        if add:
            tag_manager.add_item(item_name)
        else:
            tag_manager.remove_item(item_name)
    
    def clear_tags(self) -> None:
        """Remove all tags from the collection."""
        # Get a copy of tags since we'll be modifying during iteration
        tags = self.list_tags()
        
        for tag in tags:
            self.remove_tag(tag)
        
        # Clear cache
        self._tag_managers.clear()
    
    def get_all_tags(self) -> Dict[str, Set[str]]:
        """Get all tags and their associated item names.
        
        Returns:
            Dictionary mapping tag names to sets of item names
        """
        result = {}
        
        for tag in self.list_tags():
            tag_manager = self.get_tag_manager(tag)
            result[tag] = tag_manager.get_items()
        
        return result