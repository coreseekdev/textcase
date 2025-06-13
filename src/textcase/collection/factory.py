"""Collection Factory

This module provides factory functions and utilities for creating and managing
resource collections with simplified interfaces.
"""

from pathlib import Path, PurePosixPath
from typing import Optional, TypeVar, Union

from ..client.vfs_client import VFSClient
from .collection_manager import ResourceCollectionManagerImpl
from .collection import ResourceCollectionImpl
from .item import ResourceItemImpl

T = TypeVar('T')


class CollectionFactory:
    """Factory for creating and managing resource collections.
    
    This factory provides simplified interfaces for common collection operations
    and handles the complexity of VFS client management.
    """
    
    def __init__(self, vfs_client: VFSClient):
        """Initialize the collection factory.
        
        Args:
            vfs_client: The VFS client to use for all file operations
        """
        self._vfs = vfs_client
        self._managers = {}  # Cache for collection managers by repo root
    
    def get_manager(
        self,
        git_repo_root: Union[Path, PurePosixPath, str]
    ) -> ResourceCollectionManagerImpl[T]:
        """Get or create a collection manager for a git repository.
        
        Args:
            git_repo_root: Path to the git repository root
            
        Returns:
            A ResourceCollectionManager instance for the repository
        """
        # Normalize path
        if isinstance(git_repo_root, str):
            repo_path = PurePosixPath(git_repo_root)
        elif isinstance(git_repo_root, Path):
            repo_path = PurePosixPath(git_repo_root.as_posix())
        else:
            repo_path = git_repo_root
        
        repo_key = str(repo_path)
        
        if repo_key not in self._managers:
            self._managers[repo_key] = ResourceCollectionManagerImpl[T](repo_path, self._vfs)
        
        return self._managers[repo_key]
    
    def create_collection(
        self,
        git_repo_root: Union[Path, PurePosixPath, str],
        name: str,
        parent: Optional[str] = None,
        path: Optional[Union[PurePosixPath, str]] = None
    ) -> ResourceCollectionImpl[T]:
        """Create a new collection in a repository.
        
        Args:
            git_repo_root: Path to the git repository root
            name: Unique name for the collection
            parent: Optional parent collection name
            path: Optional custom path for the collection
            
        Returns:
            The created ResourceCollection
        """
        manager = self.get_manager(git_repo_root)
        return manager.create_collection(name, parent, path)
    
    def get_collection(
        self,
        git_repo_root: Union[Path, PurePosixPath, str],
        name: str
    ) -> Optional[ResourceCollectionImpl[T]]:
        """Get an existing collection from a repository.
        
        Args:
            git_repo_root: Path to the git repository root
            name: The name of the collection to retrieve
            
        Returns:
            The ResourceCollection if found, None otherwise
        """
        manager = self.get_manager(git_repo_root)
        return manager.get_collection(name)
    
    def create_item(
        self,
        git_repo_root: Union[Path, PurePosixPath, str],
        collection_name: str,
        item_name: str,
        data: Optional[T] = None
    ) -> ResourceItemImpl[T]:
        """Create a new item in a collection.
        
        Args:
            git_repo_root: Path to the git repository root
            collection_name: The name of the collection
            item_name: The name of the item to create
            data: Optional data payload for the item
            
        Returns:
            The created ResourceItem
            
        Raises:
            ValueError: If the collection doesn't exist
        """
        collection = self.get_collection(git_repo_root, collection_name)
        if not collection:
            raise ValueError(f"Collection '{collection_name}' not found")
        
        return collection.add_item(item_name, data)
    
    def setup_default_collections(
        self,
        git_repo_root: Union[Path, PurePosixPath, str],
        collections_config: Optional[dict] = None
    ) -> ResourceCollectionManagerImpl[T]:
        """Set up default collections for a new project.
        
        Args:
            git_repo_root: Path to the git repository root
            collections_config: Optional configuration for default collections
            
        Returns:
            The configured ResourceCollectionManager
        """
        manager = self.get_manager(git_repo_root)
        
        # Default collections configuration
        if collections_config is None:
            collections_config = {
                'requirements': {
                    'parent': None,
                    'prefix': 'REQ',
                    'tags': {
                        'functional': 'Functional requirements',
                        'non-functional': 'Non-functional requirements',
                        'business': 'Business requirements'
                    }
                },
                'design': {
                    'parent': None,
                    'prefix': 'DES',
                    'tags': {
                        'architecture': 'Architecture design',
                        'ui': 'User interface design',
                        'api': 'API design'
                    }
                },
                'tests': {
                    'parent': None,
                    'prefix': 'TST',
                    'tags': {
                        'unit': 'Unit tests',
                        'integration': 'Integration tests',
                        'e2e': 'End-to-end tests'
                    }
                }
            }
        
        # Create collections
        for coll_name, config in collections_config.items():
            try:
                collection = manager.create_collection(
                    coll_name,
                    parent=config.get('parent')
                )
                
                # Set up collection configuration
                coll_config = collection.config
                if 'prefix' in config:
                    coll_config.prefix = config['prefix']
                if 'num' in config:
                    coll_config.num = config['num']
                if 'sep' in config:
                    coll_config.sep = config['sep']
                if 'suffix' in config:
                    coll_config.suffix = config['suffix']
                
                coll_config.save(self._vfs)
                
                # Add tags
                if 'tags' in config:
                    for tag_name, tag_desc in config['tags'].items():
                        collection.add_tag(tag_name, tag_desc)
                        
            except ValueError:
                # Collection already exists, skip
                continue
        
        # Set root and default collections
        collections = manager.list_collections()
        if collections:
            if 'requirements' in collections:
                manager.set_root_collection('requirements')
                manager.set_default_collection('requirements')
            else:
                manager.set_root_collection(collections[0])
                manager.set_default_collection(collections[0])
        
        return manager


# Global factory instance (can be configured with different VFS clients)
_default_factory: Optional[CollectionFactory] = None


def get_default_factory() -> Optional[CollectionFactory]:
    """Get the default collection factory.
    
    Returns:
        The default CollectionFactory instance, or None if not configured
    """
    return _default_factory


def set_default_factory(factory: CollectionFactory) -> None:
    """Set the default collection factory.
    
    Args:
        factory: The CollectionFactory instance to use as default
    """
    global _default_factory
    _default_factory = factory


def configure_default_factory(vfs_client: VFSClient) -> CollectionFactory:
    """Configure and set the default collection factory.
    
    Args:
        vfs_client: The VFS client to use for file operations
        
    Returns:
        The configured CollectionFactory instance
    """
    factory = CollectionFactory(vfs_client)
    set_default_factory(factory)
    return factory