"""Case item factory and utilities for textcase."""

from pathlib import Path
from typing import Dict, Any, Optional

from ..protocol.module import CaseItem
from .markdown_item import MarkdownItem


def create_case_item(prefix: str, id: str, settings: Dict[str, Any] = None, path: Optional[Path] = None) -> CaseItem:
    """Factory function to create the appropriate CaseItem based on file extension or other criteria.
    
    This function examines the provided parameters and returns the most appropriate
    CaseItem implementation. Currently, it supports MarkdownItem for markdown files.
    
    Args:
        prefix: The prefix for the document (e.g., 'REQ')
        id: The unique identifier for the document
        settings: Optional settings dictionary containing formatting options
        path: Optional path to the document file
        
    Returns:
        An appropriate CaseItem implementation
    """
    # Check if path exists and has a supported extension
    markdown_extensions = ['.md', '.markdown']
    
    # If path is provided, use its extension to determine the item type
    if path and path.suffix.lower() in markdown_extensions:
        return MarkdownItem(id=id, prefix=prefix, settings=settings or {}, path=path)
    
    # Default to MarkdownItem for now, even without a path
    return MarkdownItem(id=id, prefix=prefix, settings=settings or {}, path=path)
