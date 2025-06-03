"""URI protocol package.

This package contains protocol interfaces for URI and resource functionality.
"""

from __future__ import annotations

# Import all protocols from submodules
from .uri import (
    URI,
    URIResolver,
    ResourceType
)

from .resource import (
    Resource,
    ResourceMetadata,
    ResourceContent,
    ResourceReference,
    ResourceRegistry
)

# Re-export all symbols
__all__ = [
    # URI protocols
    'URI',
    'URIResolver',
    'ResourceType',
    
    # Resource protocols
    'Resource',
    'ResourceMetadata',
    'ResourceContent',
    'ResourceReference',
    'ResourceRegistry'
]
