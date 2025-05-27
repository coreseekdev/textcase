"""Document item implementation for textcase."""

from dataclasses import dataclass, field
from typing import Dict, Any, Optional, ClassVar, Protocol, runtime_checkable

from ..protocol.module import CaseItem as CaseItemProtocol, DocumentCaseItem as DocumentCaseItemProtocol


class CaseItemBase(CaseItemProtocol):
    """Base implementation of the CaseItem protocol.
    
    This class provides a default implementation of the CaseItem protocol
    that can be used as a base class or mixin for concrete implementations.
    """
    
    def __init__(self, id: str, prefix: str, **kwargs):
        """Initialize the case item.
        
        Args:
            id: The unique identifier for the item
            prefix: The prefix for the item (e.g., 'REQ')
            **kwargs: Additional attributes to set on the instance
        """
        self._id = id
        self._prefix = prefix
        for key, value in kwargs.items():
            setattr(self, key, value)
    
    @property
    def id(self) -> str:
        """Get the item's ID."""
        return self._id
    
    @property
    def prefix(self) -> str:
        """Get the item's prefix."""
        return self._prefix
    
    @property
    def key(self) -> str:
        """Get the item's unique key (prefix:id)."""
        return f"{self.prefix}:{self.id}"
    
    def __str__(self) -> str:
        return self.key
    
    def __eq__(self, other: object) -> bool:
        if not isinstance(other, (CaseItemBase, str)):
            return False
        return str(self) == str(other)
    
    def __hash__(self) -> int:
        return hash(str(self))

class FileDocumentItem(DocumentCaseItemProtocol, CaseItemBase):
    """Represents a document item stored in the filesystem.
    
    This class implements the CaseItem protocol and provides filesystem-specific
    functionality and formatting options.
    
    Args:
        id: The unique identifier for the document
        prefix: The prefix for the document (e.g., 'REQ')
        settings: Optional settings dictionary containing formatting options
    """
    _id: str
    _prefix: str
    settings: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Validate the document item after initialization."""
        if not self._id:
            raise ValueError("Document ID cannot be empty")
        if not self._prefix:
            raise ValueError("Prefix cannot be empty")
    
    @property
    def id(self) -> str:
        """Get the item's ID."""
        return self._id
        
    @property
    def prefix(self) -> str:
        """Get the item's prefix."""
        return self._prefix
        
    @property
    def sep(self) -> str:
        """Get the separator from settings or default to '-'."""
        return self.settings.get('sep', '-')
    
    @property
    def key(self) -> str:
        """Get the storage key for this item in the format 'prefix{sep}id'.
        
        The ID will be zero-padded according to the 'digits' setting if provided.
        """
        # Get the ID part, potentially zero-padded
        id_part = self._id
        if 'digits' in self.settings and self.settings['digits'] is not None:
            try:
                # Only pad if the ID is numeric
                int_id = int(id_part)
                id_part = f"{int_id:0{self.settings['digits']}d}"
            except (ValueError, TypeError):
                pass  # If ID is not numeric, use as is
                
        # Construct the key using the separator
        sep = self.settings.get('sep', '-')
        return f"{self._prefix}{sep}{id_part}"
    
    @property
    def display_id(self) -> str:
        """Get the display ID (same as key)."""
        return self.key
        
    def __str__(self) -> str:
        return self.key
        
    def __eq__(self, other: object) -> bool:
        if not isinstance(other, (FileDocumentItem, str)):
            return False
        return str(self) == str(other)
        
    def __hash__(self) -> int:
        return hash(str(self))
    
    @property
    def sep(self) -> str:
        """Get the separator from settings or default to '-'."""
        return self.settings.get('sep', '-')
    
    @property
    def key(self) -> str:
        """Get the storage key for this item in the format 'prefix{sep}id'.
        
        The ID will be zero-padded according to the 'digits' setting if provided.
        """
        # Get the ID part, potentially zero-padded
        id_part = self.id
        if 'digits' in self.settings and self.settings['digits'] is not None:
            try:
                # Only pad if the ID is numeric
                int_id = int(id_part)
                id_part = f"{int_id:0{self.settings['digits']}d}"
            except (ValueError, TypeError):
                pass  # If ID is not numeric, use as is
                
        # Construct the key using the separator
        sep = self.settings.get('sep', '-')
        return f"{self.prefix}{sep}{id_part}"
    
    @property
    def display_id(self) -> str:
        """Get the display ID (same as key)."""
        return self.key
