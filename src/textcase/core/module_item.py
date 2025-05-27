"""Document item implementation for textcase."""

from dataclasses import dataclass, field
from typing import Dict, Any, Optional, ClassVar


@dataclass(frozen=True)
class DocumentItem:
    """Represents a document item with a prefix and ID.
    
    This class provides a way to uniquely identify document items within the system
    using a combination of prefix and ID, with configurable formatting.
    
    Args:
        id: The unique identifier for the document
        prefix: The prefix for the document (e.g., 'REQ')
        settings: Optional settings dictionary containing 'sep' (default: '-')
    """
    id: str
    prefix: str
    settings: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Validate the document item after initialization."""
        if not self.id:
            raise ValueError("Document ID cannot be empty")
        if not self.prefix:
            raise ValueError("Prefix cannot be empty")
    
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
    
    def __str__(self) -> str:
        return self.key
    
    def __str__(self) -> str:
        return self.key
