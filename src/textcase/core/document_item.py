"""Document item implementation for textcase."""

from dataclasses import dataclass
from typing import Optional, Tuple


@dataclass(frozen=True)
class DocumentItem:
    """Represents a document item with a prefix and ID.
    
    This class provides a way to uniquely identify document items within the system
    using a combination of prefix and ID.
    """
    prefix: str
    id: str
    
    @classmethod
    def from_key(cls, key: str) -> 'DocumentItem':
        """Create a DocumentItem from a storage key.
        
        Args:
            key: A string in the format "prefix:id"
            
        Returns:
            A new DocumentItem instance.
            
        Raises:
            ValueError: If the key is not in the correct format.
        """
        parts = key.split(':', 1)
        if len(parts) != 2:
            raise ValueError(f"Invalid item key format: {key}. Expected 'prefix:id'")
        return cls(prefix=parts[0], id=parts[1])
    
    @property
    def key(self) -> str:
        """Get the storage key for this item."""
        return f"{self.prefix}:{self.id}"
    
    def __str__(self) -> str:
        return self.key
