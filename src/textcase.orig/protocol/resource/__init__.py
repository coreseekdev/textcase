"""Resource protocol package.

This package contains protocol interfaces for resources, modules, and documents.
"""

from __future__ import annotations

# Import all protocols from submodules
from .base import (
    ItemBase,
    ItemCollection,
    ModuleBase,
    ModuleConfigBase
)

from .document import (
    DocumentTag,
    DocumentItem,
    DocumentModuleConfig,
    DocumentModuleBase,
    DocumentModule,
    Project,
    ProjectConfig,
    ProjectOutline
)

from .module import (
    # Legacy names for backward compatibility
    Module,
    ModuleConfig,
    ModuleOrder,
    ModuleTagging,
    ProjectTags,
    CaseItem,
    DocumentCaseItem
)

from .file_item import (
    FileItem,
    FileModule,
    SourceCodeItem,
    SourceModule
)

# Re-export all symbols
__all__ = [
    # Base protocols
    'ItemBase',
    'ItemCollection',
    'ModuleBase',
    'ModuleConfigBase',
    
    # Document protocols
    'DocumentTag',
    'DocumentItem',
    'DocumentModuleConfig',
    'DocumentModuleBase',
    'DocumentModule',
    'Project',
    'ProjectConfig',
    'ProjectOutline',
    
    # File item protocols
    'FileItem',
    'FileModule',
    'SourceCodeItem',
    'SourceModule',
    
    # Legacy names for backward compatibility
    'Module',
    'ModuleConfig',
    'ModuleOrder',
    'ModuleTagging',
    'ProjectTags',
    'CaseItem',
    'DocumentCaseItem'
]
