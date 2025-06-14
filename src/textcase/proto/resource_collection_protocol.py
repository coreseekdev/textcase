"""Resource Collection Protocol

This module defines the protocol interface for generic resource collections.
It provides abstractions for managing collections of items with tagging and
sub-collection support.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Set, TypeVar, Generic, Protocol, Iterator


# Generic type for collection items
T = TypeVar('T')


class InvalidCollectionError(Exception):
    """Exception raised when a collection is invalid or cannot be loaded.
    
    This exception is raised when a collection directory does not contain
    the required configuration file or has an invalid structure.
    """
    pass


class ResourceItem(Protocol[T]):
    """Protocol for items that can be stored in a resource collection.
    
    This protocol defines the interface that all collection items must follow.
    Items are generic and can represent any type of resource.
    """
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Get the unique name of this item within its collection.
        
        Returns:
            The item's name (must be unique within the collection)
        """
        ...
    
    @property
    @abstractmethod
    def tags(self) -> Set[str]:
        """Get the tags assigned to this item.
        
        Returns:
            Set of tag names assigned to this item
        """
        ...
    
    @abstractmethod
    def assign_tag(self, tag: str) -> None:
        """Assign a tag to this item.
        
        Args:
            tag: Tag name to assign
        """
        ...
    
    @abstractmethod
    def unassign_tag(self, tag: str) -> None:
        """Remove a tag from this item.
        
        Args:
            tag: Tag name to remove
        """
        ...
    
    @abstractmethod
    def has_tag(self, tag: str) -> bool:
        """Check if this item has a specific tag.
        
        Args:
            tag: Tag name to check
            
        Returns:
            True if the item has the tag, False otherwise
        """
        ...


class ResourceCollection(Protocol[T]):
    """Protocol for resource collections.
    
    A resource collection manages a set of named items and supports:
    - Sub-collections (logical children, not subset relationships)
    - Tag-based item organization
    - Unique item naming within the collection
    """
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Get the name of this collection.
        
        Returns:
            Collection name
        """
        ...
    
    @property
    @abstractmethod
    def items(self) -> Dict[str, ResourceItem[T]]:
        """Get all items in this collection.
        
        Returns:
            Dictionary mapping item names to item instances
        """
        ...
    
    @property
    @abstractmethod
    def collections(self) -> Dict[str, 'ResourceCollection[T]']:
        """Get all sub-collections of this collection.
        
        Sub-collections are logical children and do not have subset
        relationships with the parent collection's items.
        
        Returns:
            Dictionary mapping sub-collection names to collection instances
        """
        ...
    
    @property
    @abstractmethod
    def tags(self) -> Dict[str, Set[str]]:
        """Get all tags and their associated item names.
        
        Tags represent logical subsets of items within this collection.
        
        Returns:
            Dictionary mapping tag names to sets of item names
        """
        ...
    
    # Item management
    @abstractmethod
    def add_item(self, item: ResourceItem[T]) -> None:
        """Add an item to this collection.
        
        Args:
            item: Item to add
            
        Raises:
            ValueError: If an item with the same name already exists
        """
        ...
    
    @abstractmethod
    def remove_item(self, name: str) -> Optional[ResourceItem[T]]:
        """Remove an item from this collection.
        
        Args:
            name: Name of the item to remove
            
        Returns:
            The removed item, or None if not found
        """
        ...
    
    @abstractmethod
    def get_item(self, name: str) -> Optional[ResourceItem[T]]:
        """Get an item by name.
        
        Args:
            name: Name of the item to retrieve
            
        Returns:
            The item if found, None otherwise
        """
        ...
    
    @abstractmethod
    def has_item(self, name: str) -> bool:
        """Check if an item exists in this collection.
        
        Args:
            name: Name of the item to check
            
        Returns:
            True if the item exists, False otherwise
        """
        ...
    
    # Sub-collection management
    @abstractmethod
    def add_collection(self, collection: 'ResourceCollection[T]') -> None:
        """Add a sub-collection to this collection.
        
        Args:
            collection: Sub-collection to add
            
        Raises:
            ValueError: If a sub-collection with the same name already exists
        """
        ...
    
    @abstractmethod
    def remove_collection(self, name: str) -> Optional['ResourceCollection[T]']:
        """Remove a sub-collection from this collection.
        
        Args:
            name: Name of the sub-collection to remove
            
        Returns:
            The removed sub-collection, or None if not found
        """
        ...
    
    @abstractmethod
    def get_collection(self, name: str) -> Optional['ResourceCollection[T]']:
        """Get a sub-collection by name.
        
        Args:
            name: Name of the sub-collection to retrieve
            
        Returns:
            The sub-collection if found, None otherwise
        """
        ...
    
    @abstractmethod
    def has_collection(self, name: str) -> bool:
        """Check if a sub-collection exists.
        
        Args:
            name: Name of the sub-collection to check
            
        Returns:
            True if the sub-collection exists, False otherwise
        """
        ...
    
    # Tag-based queries
    @abstractmethod
    def get_items_by_tag(self, tag: str) -> List[ResourceItem[T]]:
        """Get all items that have a specific tag.
        
        Args:
            tag: Tag name to search for
            
        Returns:
            List of items with the specified tag
        """
        ...
    
    @abstractmethod
    def get_items_by_tags(self, tags: Set[str], match_all: bool = True) -> List[ResourceItem[T]]:
        """Get items that match tag criteria.
        
        Args:
            tags: Set of tag names to search for
            match_all: If True, items must have all tags; if False, any tag
            
        Returns:
            List of items matching the tag criteria
        """
        ...
    
    @abstractmethod
    def get_available_tags(self) -> Set[str]:
        """Get all tags used in this collection.
        
        Returns:
            Set of all tag names used by items in this collection
        """
        ...

    @abstractmethod
    def assign_tag(self, item_name: str, tag: str) -> None:
        """Assign a tag to an item."""
        ...
    
    @abstractmethod
    def unassign_tag(self, item_name: str, tag: str) -> None:
        """Remove a tag from an item."""
        ...

    @abstractmethod
    def has_tag(self, tag: str) -> bool:
        """Check if a tag exists in this collection."""
        ...

    # Iteration support
    @abstractmethod
    def iter_items(self) -> Iterator[ResourceItem[T]]:
        """Iterate over all items in this collection.
        
        Returns:
            Iterator over collection items
        """
        ...
        
    # Collection metadata
    @abstractmethod
    def size(self) -> int:
        """Get the number of items in this collection.
        
        Returns:
            Number of items (not including sub-collections)
        """
        ...
    
    @abstractmethod
    def is_empty(self) -> bool:
        """Check if this collection is empty.
        
        Returns:
            True if the collection has no items and no sub-collections
        """
        ...
    
    @abstractmethod
    def clear(self) -> None:
        """Remove all items and sub-collections from this collection."""
        ...


class ResourceCollectionManager(Protocol[T]):
    """Protocol for managing multiple resource collections.
    
    This protocol provides a higher-level interface for managing
    multiple collections and cross-collection operations. It supports
    hierarchical collection management with root/default collection concepts.
    """
    
    @property
    @abstractmethod
    def root_collection(self) -> ResourceCollection[T]:
        """Get the default collection for operations.
        
        The default collection is used when no specific collection
        is specified in operations.
        
        Returns:
            The default collection instance
        """
        ...
    
    @abstractmethod
    def create_collection(self, name: str, parent: Optional[ResourceCollection[T]] = None) -> ResourceCollection[T]:
        """Create a new collection.
        
        Args:
            name: Name for the new collection
            parent: Optional parent collection. If None, creates at root level
            
        Returns:
            The created collection
            
        Raises:
            ValueError: If a collection with the same name already exists in the parent
        """
        ...
    
    @abstractmethod
    def get_collection(self, name: str, parent: Optional[ResourceCollection[T]] = None) -> Optional[ResourceCollection[T]]:
        """Get a collection by name.
        
        Args:
            name: Name of the collection to retrieve
            parent: Optional parent collection to search in. If None, searches from root
            
        Returns:
            The collection if found, None otherwise
        """
        ...
    
    @abstractmethod
    def remove_collection(self, name: str, parent: Optional[ResourceCollection[T]] = None) -> Optional[ResourceCollection[T]]:
        """Remove a collection.
        
        Args:
            name: Name of the collection to remove
            parent: Optional parent collection. If None, removes from root level
            
        Returns:
            The removed collection, or None if not found
        """
        ...
    
    @abstractmethod
    def add_collection(self, collection: ResourceCollection[T], parent: Optional[ResourceCollection[T]] = None) -> None:
        """Add an existing collection to a parent.
        
        Args:
            collection: Collection to add
            parent: Optional parent collection. If None, adds to root level
            
        Raises:
            ValueError: If a collection with the same name already exists in the parent
        """
        ...
    
    @abstractmethod
    def move_collection(self, name: str, 
                       from_parent: Optional[ResourceCollection[T]] = None,
                       to_parent: Optional[ResourceCollection[T]] = None) -> bool:
        """Move a collection from one parent to another.
        
        Args:
            name: Name of the collection to move
            from_parent: Source parent collection. If None, moves from root
            to_parent: Target parent collection. If None, moves to root
            
        Returns:
            True if the collection was moved successfully, False otherwise
        """
        ...
    
    @abstractmethod
    def list_collections(self, parent: Optional[ResourceCollection[T]] = None) -> List[str]:
        """List collection names under a parent.
        
        Args:
            parent: Optional parent collection. If None, lists root-level collections
            
        Returns:
            List of collection names
        """
        ...
    
    @abstractmethod
    def iter_all_collections(self, include_root: bool = True) -> Iterator[ResourceCollection[T]]:
        """Iterate over all collections in the hierarchy.
        
        This enables traversal without knowing specific collection names.
        
        Args:
            include_root: Whether to include the root collection in iteration
            
        Returns:
            Iterator over all collections in the hierarchy
        """
        ...
    
    @abstractmethod
    def find_collection_path(self, collection: ResourceCollection[T]) -> List[str]:
        """Find the path from root to a specific collection.
        
        Args:
            collection: Collection to find path for
            
        Returns:
            List of collection names representing the path from root
        """
        ...
    
    @abstractmethod
    def search_items_across_collections(self, 
                                      query: str, 
                                      tags: Optional[Set[str]] = None,
                                      root: Optional[ResourceCollection[T]] = None) -> Dict[str, List[ResourceItem[T]]]:
        """Search for items across collections in a hierarchy.
        
        Args:
            query: Search query (implementation-specific)
            tags: Optional tag filter
            root: Optional root collection to start search from. If None, uses manager's root
            
        Returns:
            Dictionary mapping collection names to matching items
        """
        ...