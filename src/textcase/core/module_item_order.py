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
import yaml
from pathlib import Path
from typing import Dict, List, Optional, Set, cast

from ..protocol.vfs import VFS
from ..protocol.module import CaseItem, ModuleOrder

class YamlOrder(ModuleOrder):
    """Order implementation using YAML files.
    
    If index.yml exists, it will be used to determine the order of files.
    Otherwise, files will be sorted by creation time.
    Only files starting with the configured prefix will be included.

    Order 不完全是排序，如存在 index.yml 的 outline 节时，允许通过锁进（YML 里面的 sub item ) 描述父子关系。

    index.yml 中需要记录下一个候选的 item id ( 不带 prefix 的流水号 )

    """
    
    def __init__(self, path: Path, vfs: VFS):
        """Initialize with module path and VFS.
        
        Args:
            path: The base path for this order.
            vfs: The virtual filesystem to use for operations.
        """
        self.path = path
        self.vfs = vfs
        self._index_file = path / 'index.yml'
        self._items: Optional[List[CaseItem]] = None
        self._prefix: str = ''  # Will be set when config is loaded
        self._case_item_cache: Dict[str, CaseItem] = {}  # Cache for CaseItem objects
    
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
            for entry in self.vfs.scandir(self.path):
                if self.vfs.isfile(entry) and entry.name.startswith(self._prefix):
                    files.append(entry)
            
            # Create CaseItem objects for all files
            case_items = [self._create_case_item(Path(f.name)) for f in files]
            
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
            
        from .module_item import CaseItemBase
        
        # Create a CaseItem using CaseItemBase
        case_item = CaseItemBase(
            id=item_id,
            prefix=path.parent.name,
            _path=path  # Store the path as an attribute
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
