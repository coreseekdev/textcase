"""Markdown document item implementation for textcase."""

from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple

from .module_item import FileDocumentItem
from ..protocol.module import CaseItem


class MarkdownItem(FileDocumentItem):
    """Represents a Markdown document item stored in the filesystem.
    
    This class extends FileDocumentItem to provide Markdown-specific functionality,
    such as creating links between documents.
    
    Args:
        id: The unique identifier for the document
        prefix: The prefix for the document (e.g., 'REQ')
        settings: Optional settings dictionary containing formatting options
        path: Optional path to the markdown file
    """
    
    _id: str
    _prefix: str
    settings: Dict[str, Any]
    _path: Optional[Path] = None
    
    def __init__(self, id: str, prefix: str, settings: Dict[str, Any] = None, path: Optional[Path] = None):
        """Initialize the markdown item."""
        super().__init__(id=id, prefix=prefix, settings=settings or {})
        self._path = path
    
    @property
    def path(self) -> Optional[Path]:
        """Get the path to the markdown file."""
        return self._path
    
    @path.setter
    def path(self, value: Path):
        """Set the path to the markdown file."""
        self._path = value
    
    def make_link(self, target: CaseItem, label: Optional[str] = None) -> bool:
        """Create a link from this document to the target document.
        
        This method appends a link reference to the end of the markdown file.
        
        Args:
            target: The target CaseItem to link to
            label: Optional label for the link, defaults to target's key
            
        Returns:
            True if the link was successfully created, False otherwise
            
        Raises:
            ValueError: If the document path is not set
            FileNotFoundError: If the document file does not exist
        """
        if not self._path:
            raise ValueError(f"Document path not set for {self.key}")
        
        if not self._path.exists():
            raise FileNotFoundError(f"Document {self.key} not found at {self._path}")
        
        # Use the provided label or default to the target's key
        link_label = label or target.key
        
        # Format the link entry to append to the file
        link_entry = f"\nLINK: {target.key}"
        
        # Append the link to the file
        with open(self._path, 'a', encoding='utf-8') as f:
            f.write(link_entry)
        
        return True
    
    def get_links(self) -> List[Tuple[str, str]]:
        """Get all links defined in this document.
        
        Returns:
            A list of tuples containing (target_key, label)
            
        Raises:
            ValueError: If the document path is not set
            FileNotFoundError: If the document file does not exist
        """
        if not self._path:
            raise ValueError(f"Document path not set for {self.key}")
        
        if not self._path.exists():
            raise FileNotFoundError(f"Document {self.key} not found at {self._path}")
        
        links = []
        
        # Read the file and extract links
        with open(self._path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        # Find all lines starting with "LINK: "
        for line in content.splitlines():
            if line.startswith("LINK: "):
                target_key = line[6:].strip()  # Remove "LINK: " prefix
                links.append((target_key, target_key))  # Using target_key as label for now
                
        return links

