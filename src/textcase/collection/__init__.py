"""Resource Collection Implementation

This module provides concrete implementations of the resource collection protocols
defined in textcase.proto.resource_collection_protocol.

The implementation follows the design patterns from the original textcase.orig.core
module, using VFS for all file operations and YAML for configuration storage.
"""

from .collection_manager import ResourceCollectionManagerImpl
from .collection import ResourceCollectionImpl
from .item import ResourceItemImpl
from .config import CollectionConfig
from .factory import CollectionFactory 

__all__ = [
    'ResourceCollectionManagerImpl',
    'ResourceCollectionImpl', 
    'ResourceItemImpl',
    'CollectionConfig',
    'CollectionFactory',
]

# Convenience aliases for easier imports
CollectionManager = ResourceCollectionManagerImpl
Collection = ResourceCollectionImpl
Item = ResourceItemImpl
Factory = CollectionFactory