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
    # For now, we only support markdown files
    # path 的扩展名应该作为全局配置项
    if path and path.suffix.lower() in ('.md', '.markdown'):
        return MarkdownItem(id=id, prefix=prefix, settings=settings or {}, path=path)
    
    # Default to MarkdownItem for now, even without a path
    return MarkdownItem(id=id, prefix=prefix, settings=settings or {}, path=path)
