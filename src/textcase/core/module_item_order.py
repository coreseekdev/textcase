#
# Copyright 2025 coreseek.com
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
"""Default implementation of ModuleOrder."""

import os
import re
import yaml
from pathlib import Path
from typing import Dict, List, Optional, Set, cast, TYPE_CHECKING

from ..protocol.vfs import VFS
from ..protocol.module import CaseItem, ModuleOrder, Module

if TYPE_CHECKING:
    from .module import YamlModule

class YamlOrder(ModuleOrder):
    """Order implementation using YAML files.
    
    If index.yml exists, it will be used to determine the order of files.
    Otherwise, files will be sorted by creation time.
    Only files starting with the configured prefix will be included.

    Order 不完全是排序，如存在 index.yml 的 outline 节时，允许通过锁进（YML 里面的 sub item ) 描述父子关系。

    index.yml 中需要记录下一个候选的 item id ( 不带 prefix 的流水号 )

    """
    
    def __init__(self, module: 'Module'):
        """Initialize with a module.
        
        Args:
            module: The module this order belongs to.
        """
        self._module = module
        self.path = module.path
        self.vfs = module._vfs  # Accessing protected member, but this is within the same package
        self._index_file = self.path / 'index.yml'
        self._items: Optional[List[CaseItem]] = None
        self._prefix: str = ''  # Will be set from module config
        self._case_item_cache: Dict[str, CaseItem] = {}  # Cache for CaseItem objects
        
        # Set prefix from module config
        if hasattr(module, 'prefix') and module.prefix:
            self.set_prefix(module.prefix)
    
    def _get_file_creation_time(self, item: CaseItem) -> float:
        """Get the creation time of a file.
        
        Args:
            item: The CaseItem to get the creation time for.
                
        Returns:
            The creation time as a float, or infinity if not available.
        """
        try:
            # Get the filename from the CaseItem
            filename = f"{item.key}.md"  # Assuming .md extension, adjust if needed
            stat = self.vfs.stat(self.path / filename)
            return stat.st_ctime
        except Exception:
            return float('inf')
    
    def _get_files_sorted_by_creation(self) -> List[CaseItem]:
        """Get files in the directory sorted by creation time.
        
        Returns:
            List of CaseItem objects sorted by creation time.
        """
        try:
            # Get all files in the directory
            files = []
            for entry_name in self.vfs.listdir_names(self.path):
                entry_path = self.path / entry_name
                if self.vfs.isfile(entry_path) and entry_name.startswith(self._prefix):
                    files.append(entry_name)
            
            # Create CaseItem objects for all files
            case_items = [self._create_case_item(Path(f)) for f in files]
            
            # Sort by creation time
            return sorted(case_items, key=self._get_file_creation_time)
        except Exception as e:
            print(f"Error getting files sorted by creation time: {e}")
            return []
    
    def _create_case_item(self, path: Path) -> CaseItem:
        """Create a CaseItem from a Path.
        
        Args:
            path: The path to create a CaseItem for.
                
        Returns:
            A CaseItem representing the path.
        """
        # Use the filename without extension as the ID
        item_id = path.stem
        if item_id in self._case_item_cache:
            return self._case_item_cache[item_id]
        
        # Get the prefix from the parent directory name or path
        prefix = path.parent.name.upper()
        
        # Get settings from the module if available
        # settings = {}
        # if hasattr(self, '_module') and hasattr(self._module, 'config') and hasattr(self._module.config, 'settings'):
        settings = dict(self._module.config.settings)
        
        # Use the factory function to create the appropriate case item
        from .case_item import create_case_item
        case_item = create_case_item(
            prefix=prefix,
            id=item_id,
            settings=settings,
            path=path
        )
        
        self._case_item_cache[item_id] = case_item
        return case_item
        
    def _load_items(self) -> List[CaseItem]:
        """Load items from the index file or sort by creation time."""
        if self._items is not None:
            return self._items
            
        if self.vfs.exists(self._index_file):
            try:
                with self.vfs.open(self._index_file, 'r') as f:
                    data = yaml.safe_load(f)
                    
                if not isinstance(data, dict):
                    return self._get_files_sorted_by_creation()
                    
                # Get the outline if it exists
                outline = data.get('outline', [])
                if not outline:
                    return self._get_files_sorted_by_creation()
                    
                # Get all files that match the prefix
                existing_files = {f.name for f in self.vfs.scandir(self.path) 
                               if self.vfs.isfile(f) and f.name.startswith(self._prefix)}
                
                # Parse the outline
                items = self._parse_outline(outline, existing_files)
                
                # If no items were found in the outline, fall back to file system order
                if not items:
                    return self._get_files_sorted_by_creation()
                    
                # Add any files that weren't in the outline
                outline_files = {str(item) for item in items}
                for filename in existing_files - outline_files:
                    items.append(self._create_case_item(Path(filename)))
                
                self._items = items
                return items
                
            except Exception as e:
                print(f"Error loading index.yml: {e}")
                return self._get_files_sorted_by_creation()
        else:
            return self._get_files_sorted_by_creation()
        
    def _parse_outline(self, outline: list, existing_files: set) -> List[CaseItem]:
        """Parse a hierarchical outline structure into a flat list of CaseItems.
        
        Args:
            outline: The outline structure from the YAML file
            existing_files: Set of existing files to validate against
            
        Returns:
            List of CaseItems in the order they appear in the outline
        """
        result = []
        
        def process_item(item):
            if isinstance(item, dict):
                for key, value in item.items():
                    if key in existing_files:
                        result.append(self._create_case_item(Path(key)))
                    if isinstance(value, list):
                        for subitem in value:
                            process_item(subitem)
            elif isinstance(item, str) and item in existing_files:
                result.append(self._create_case_item(Path(item)))
            elif isinstance(item, list):
                for subitem in item:
                    process_item(subitem)
        
        for item in outline:
            process_item(item)
            
        return result
    
    def _save_items(self) -> None:
        """Save the current order to the index file."""
        if self._items is None:
            return
            
        # Create a header with instructions
        header = """# THIS FILE IS USED TO DEFINE THE ORDER OF ITEMS
# MANUALLY INDENT, DEDENT, & MOVE ITEMS TO THEIR DESIRED LEVEL
# A NEW ITEM WILL BE ADDED FOR ANY UNKNOWN IDS, i.e. - new:
# THE COMMENT WILL BE USED AS THE ITEM TEXT FOR NEW ITEMS
#######################################################################
"""
        
        # Create the data structure with item keys
        data = {
            'initial': '1.0',  # Document version
            'outline': [str(item.key) for item in self._items]  # Use the item's key
        }
        
        # Save to index.yml with the header
        with self.vfs.open(self._index_file, 'w') as f:
            f.write(header)
            yaml.safe_dump(data, f, default_flow_style=False, sort_keys=False)
    
    def set_prefix(self, prefix: str) -> None:
        """Set the prefix for filtering files."""
        self._prefix = prefix
        # Invalidate cache to force reload with new prefix
        self._items = None
    
    def get_ordered_items(self) -> List[CaseItem]:
        """Get items in their defined order.
        
        Returns:
            A list of CaseItem objects in their defined order.
        """
        # Ensure we have the latest files that match the prefix
        self._items = None
        return self._load_items().copy()
    
    def set_ordered_items(self, items: List[CaseItem]) -> None:
        """Set the order of items.
        
        Args:
            items: List of CaseItem objects to include in the order. Only files that start with
                  the current prefix will be included.
        """
        # Convert items to Path objects for filtering
        filtered_items = []
        for item in items:
            try:
                path = Path(str(item))
                if (path.name.startswith(self._prefix) and 
                    self.vfs.exists(self.path / path) and 
                    self.vfs.isfile(self.path / path)):
                    filtered_items.append(self._create_case_item(path))
            except (TypeError, ValueError):
                continue
        
        # Keep any existing items that match the prefix but aren't in the new list
        current_items = {str(item) for item in self._load_items()}
        new_items = {str(item) for item in filtered_items}
        
        # Add any items that match the prefix but weren't in the new list
        for item_str in current_items - new_items:
            if item_str.startswith(self._prefix):
                filtered_items.append(self._create_case_item(Path(item_str)))
        
        self._items = filtered_items
        self._save_items()
    
    def add_item(self, item: CaseItem) -> None:
        """Add an item to the order if it matches the prefix.
        
        Args:
            item: The CaseItem to add. Will only be added if it starts with the prefix.
        """
        try:
            item_path = Path(str(item))
            if not item_path.name.startswith(self._prefix):
                return
                
            items = self._load_items()
            if item not in items and self.vfs.exists(self.path / item_path) and self.vfs.isfile(self.path / item_path):
                items.append(self._create_case_item(item_path))
                self._items = items
                self._save_items()
        except (TypeError, ValueError):
            return
            
    # Alias for backward compatibility
    def append_item(self, item: CaseItem) -> None:
        """Alias for add_item.
        
        Args:
            item: The CaseItem to add.
        """
        self.add_item(item)
    
    def remove_item(self, item: CaseItem) -> None:
        """Remove an item from the order.
        
        Args:
            item: The CaseItem to remove.
        """
        items = self._load_items()
        if item in items:
            items.remove(item)
            self._items = items
            self._save_items()
            
    def get_next_item_id(self, prefix: str) -> str:
        """Get the next available item ID for the given prefix.
        
        The ID is a monotonically increasing sequence number based on existing files
        in the directory with the pattern 'prefixNNN.md'. It will find the highest
        existing sequence number and return the next one.
        
        Args:
            prefix: The prefix to use for finding existing files (e.g., 'REQ')
            
        Returns:
            The next available sequence number as a string, formatted according to
            the module's settings (e.g., '001' if digits=3)
        """
        # Get module settings for formatting directly from the module
        settings = self._module.config.settings
        
        # Get formatting parameters
        digits = settings.get('digits', 3)  # Default to 3 digits
        separator = settings.get('sep', '')  # Default to no separator
        
        # Find all files that match the pattern: prefix + separator + digits + .md
        # Example: REQ001.md or REQ-001.md depending on separator
        max_id = 0
        pattern = f"^{re.escape(prefix)}{re.escape(separator)}(\\d+)\.md$"
        
        try:
            # List all files in the directory
            for entry in self.vfs.listdir_names(self.path):
                match = re.match(pattern, entry)
                if match:
                    # Extract the numeric part and convert to int
                    num_id = int(match.group(1))
                    max_id = max(max_id, num_id)
        except Exception as e:
            print(f"Error finding next item ID: {e}")
            # If there's an error, start from 1
            max_id = 0
        
        # Increment to get the next ID
        next_id = max_id + 1
        
        # Format with the specified number of digits
        formatted_id = f"{next_id:0{digits}d}"
        
        return formatted_id
