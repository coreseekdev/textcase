"""Collection Usage Examples

This module provides examples of how to use the resource collection system.
"""

from pathlib import PurePosixPath
from typing import Any, Dict

from ..client.vfs_client import VFSClient
from . import CollectionFactory, configure_default_factory
from .collection import ResourceCollectionImpl


def example_collection_construction(vfs_client: VFSClient, repo_root: str) -> None:
    """Example of proper collection construction using class methods.
    
    This example demonstrates the correct way to create and load collections
    using dedicated class methods instead of direct constructor calls.
    
    Args:
        vfs_client: VFS client for file operations
        repo_root: Path to git repository root
    """
    # For creating NEW collections, use create() class method
    new_collection = ResourceCollectionImpl.create(
        name='new-requirements',
        path=PurePosixPath(repo_root) / 'case' / 'new-requirements',
        vfs=vfs_client,
        parent=None
    )
    print(f"Created new collection: {new_collection.name}")
    
    # Example with custom configuration
    from .config import CollectionConfig
    custom_config = CollectionConfig(
        name='custom-docs',
        prefix='DOC',
        num=4,
        sep='-',
        suffix='.md',
        tags={'draft': 'Draft documents', 'final': 'Final documents'}
    )
    
    custom_collection = ResourceCollectionImpl.create(
        name='custom-docs',
        path=PurePosixPath(repo_root) / 'case' / 'custom-docs',
        vfs=vfs_client,
        parent=None,
        config=custom_config
    )
    print(f"Created custom collection: {custom_collection.name} with prefix: {custom_collection.config.prefix}")
    
    # Example with force parameter (reinitialize existing collection)
    try:
        forced_collection = ResourceCollectionImpl.create(
            name='existing-collection',
            path=PurePosixPath(repo_root) / 'case' / 'existing-collection',
            vfs=vfs_client,
            parent=None,
            force=True  # This will reinitialize even if collection exists
        )
        print(f"Force-created collection: {forced_collection.name}")
    except Exception as e:
        print(f"Force creation example: {e}")
    
    # For loading EXISTING collections, use from_existing() class method
    try:
        existing_collection = ResourceCollectionImpl.from_existing(
            name='existing-requirements',
            path=PurePosixPath(repo_root) / 'case' / 'existing-requirements',
            vfs=vfs_client,
            parent=None
        )
        print(f"Loaded existing collection: {existing_collection.name}")
    except FileNotFoundError:
        print("Existing collection not found - this is expected for new repositories")
    
    # AVOID direct constructor usage - this is now for internal use only:
    # collection = ResourceCollectionImpl(name, path, vfs, parent)  # DON'T DO THIS
    
    # AVOID deprecated create_new method - use create() instead:
    # collection = ResourceCollectionImpl.create_new(name, path, vfs, parent)  # DEPRECATED
    
    print("Collection construction example completed.")


def example_basic_usage(vfs_client: VFSClient, repo_root: str) -> None:
    """Example of basic collection usage.
    
    Args:
        vfs_client: VFS client for file operations
        repo_root: Path to git repository root
    """
    # Configure the factory
    factory = configure_default_factory(vfs_client)
    
    # Get or create a collection manager
    manager = factory.get_manager(repo_root)
    
    # Create a requirements collection
    req_collection = manager.create_collection(
        name='requirements',
        parent=None  # Root level collection
    )
    
    # Configure the collection
    config = req_collection.config
    config.prefix = 'REQ'
    config.num = 3
    config.sep = '-'
    config.suffix = '.md'
    req_collection._save_config()
    
    # Add tags to the collection
    req_collection.add_tag('functional', 'Functional requirements')
    req_collection.add_tag('non-functional', 'Non-functional requirements')
    req_collection.add_tag('business', 'Business requirements')
    
    # Create some requirement items
    req1 = req_collection.add_item('REQ001')
    req1.write_content('# User Authentication\n\nThe system shall provide user authentication.')
    req1.add_tag('functional')
    
    req2 = req_collection.add_item('REQ002')
    req2.write_content('# Performance\n\nThe system shall respond within 2 seconds.')
    req2.add_tag('non-functional')
    
    # Create a sub-collection for detailed requirements
    detailed_req = manager.create_collection(
        name='detailed-requirements',
        parent='requirements'
    )
    
    # Set as default collection
    manager.set_default_collection('requirements')
    
    print(f"Created collection: {req_collection.name}")
    print(f"Items: {req_collection.list_items()}")
    print(f"Tags: {req_collection.list_tags()}")


def example_project_setup(vfs_client: VFSClient, repo_root: str) -> None:
    """Example of setting up a complete project with default collections.
    
    Args:
        vfs_client: VFS client for file operations
        repo_root: Path to git repository root
    """
    factory = CollectionFactory(vfs_client)
    
    # Set up default collections for a software project
    manager = factory.setup_default_collections(repo_root)
    
    # Get the collections
    requirements = manager.get_collection('requirements')
    design = manager.get_collection('design')
    tests = manager.get_collection('tests')
    
    if requirements:
        # Add some requirement items
        req1 = requirements.add_item(requirements.get_next_item_name())
        req1.write_content('# User Registration\n\nUsers shall be able to register accounts.')
        req1.add_tag('functional')
        
        req2 = requirements.add_item(requirements.get_next_item_name())
        req2.write_content('# Security\n\nPasswords shall be encrypted.')
        req2.add_tag('non-functional')
    
    if design:
        # Add design documents
        arch = design.add_item(design.get_next_item_name())
        arch.write_content('# System Architecture\n\nMicroservices architecture.')
        arch.add_tag('architecture')
    
    if tests:
        # Add test cases
        test1 = tests.add_item(tests.get_next_item_name())
        test1.write_content('# Test User Registration\n\nVerify user can register.')
        test1.add_tag('unit')
    
    print("Project setup complete!")
    print(f"Collections: {manager.list_collections()}")
    print(f"Root collection: {manager.root_collection.name if manager.root_collection else 'None'}")


def example_search_and_filter(vfs_client: VFSClient, repo_root: str) -> None:
    """Example of searching and filtering items across collections.
    
    Args:
        vfs_client: VFS client for file operations
        repo_root: Path to git repository root
    """
    factory = CollectionFactory(vfs_client)
    manager = factory.get_manager(repo_root)
    
    # Search for items containing 'user' across all collections
    results = manager.search_items_across_collections('user')
    
    print("Search results for 'user':")
    for collection_name, items in results.items():
        print(f"  {collection_name}:")
        for item in items:
            print(f"    - {item.name}: {item.tags}")
    
    # Search for functional requirements specifically
    functional_results = manager.search_items_across_collections(
        query='',
        tags={'functional'},
        collections=['requirements']
    )
    
    print("\nFunctional requirements:")
    for collection_name, items in functional_results.items():
        for item in items:
            print(f"  - {item.name}")


def example_collection_hierarchy(vfs_client: VFSClient, repo_root: str) -> None:
    """Example of working with collection hierarchies.
    
    Args:
        vfs_client: VFS client for file operations
        repo_root: Path to git repository root
    """
    factory = CollectionFactory(vfs_client)
    manager = factory.get_manager(repo_root)
    
    # Create a hierarchy: project -> modules -> components
    project_coll = manager.create_collection('project')
    
    # Create module collections
    auth_module = manager.create_collection('auth-module', parent='project')
    user_module = manager.create_collection('user-module', parent='project')
    
    # Create component collections
    auth_api = manager.create_collection('auth-api', parent='auth-module')
    auth_db = manager.create_collection('auth-db', parent='auth-module')
    
    # Move a collection to a different parent
    manager.move_collection('auth-db', 'user-module')
    
    # Find collection paths
    auth_api_path = manager.find_collection_path('auth-api')
    auth_db_path = manager.find_collection_path('auth-db')
    
    print(f"Auth API path: {' -> '.join(auth_api_path) if auth_api_path else 'Not found'}")
    print(f"Auth DB path: {' -> '.join(auth_db_path) if auth_db_path else 'Not found'}")
    
    # List all collections
    print("\nAll collections:")
    for collection in manager.iter_all_collections():
        path = manager.find_collection_path(collection.name)
        indent = '  ' * (len(path) - 1) if path else ''
        print(f"{indent}- {collection.name}")


def example_item_management(vfs_client: VFSClient, repo_root: str) -> None:
    """Example of advanced item management.
    
    Args:
        vfs_client: VFS client for file operations
        repo_root: Path to git repository root
    """
    factory = CollectionFactory(vfs_client)
    manager = factory.get_manager(repo_root)
    
    # Get or create a collection
    collection = manager.get_collection('requirements')
    if not collection:
        collection = manager.create_collection('requirements')
        collection.add_tag('high-priority', 'High priority items')
        collection.add_tag('reviewed', 'Items that have been reviewed')
    
    # Create an item with metadata
    item = collection.add_item('REQ-SPECIAL-001')
    item.write_content('# Special Requirement\n\nThis is a special requirement.')
    
    # Add tags and metadata
    item.add_tag('high-priority')
    item.set_metadata('author', 'John Doe')
    item.set_metadata('created_date', '2024-01-15')
    item.set_metadata('version', '1.0')
    
    # Read item information
    print(f"Item: {item.name}")
    print(f"Tags: {item.tags}")
    print(f"Author: {item.get_metadata('author')}")
    print(f"Created: {item.get_metadata('created_date')}")
    print(f"File path: {item.get_file_path()}")
    print(f"Content preview: {item.read_content()[:50]}...")
    
    # Get items by tag
    high_priority_items = collection.get_items_by_tag('high-priority')
    print(f"\nHigh priority items: {[item.name for item in high_priority_items]}")
    
    # Generate next item name
    next_name = collection.get_next_item_name()
    print(f"Next available item name: {next_name}")


if __name__ == '__main__':
    # This would be used for testing the examples
    # Note: In real usage, you would get the VFS client from your application
    pass