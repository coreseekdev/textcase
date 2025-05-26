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
from typing import Dict, List, Optional, Set

from ..protocol.vfs import VFS

class YamlOrder:
    """Order implementation using YAML files.
    
    If index.yml exists, it will be used to determine the order of files.
    Otherwise, files will be sorted by creation time.
    Only files starting with the configured prefix will be included.
    """
    
    def __init__(self, path: Path, vfs: VFS):
        """Initialize with module path and VFS."""
        self.path = path
        self.vfs = vfs
        self._index_file = path / 'index.yml'
        self._items: Optional[List[Path]] = None
        self._prefix: str = ''  # Will be set when config is loaded
    
    def _get_file_creation_time(self, path: Path) -> float:
        """Get the creation time of a file."""
        try:
            stat = self.vfs.stat(path)
            return stat.st_ctime
        except Exception:
            return float('inf')
    
    def _get_files_sorted_by_creation(self) -> List[Path]:
        """Get files in the directory sorted by creation time."""
        if not self.vfs.exists(self.path) or not self.vfs.isdir(self.path):
            return []
            
        # Get all files that start with the prefix and are not hidden
        files = []
        try:
            for entry in self.vfs.listdir(self.path):
                entry_path = self.path / entry
                # Skip directories and hidden files
                if (self.vfs.isfile(entry_path) and 
                    not entry.startswith('.') and 
                    (not self._prefix or entry.startswith(self._prefix))):
                    files.append(Path(entry))
            
            # Sort by creation time (oldest first)
            files.sort(key=lambda f: self._get_file_creation_time(self.path / f))
        except Exception as e:
            print(f"Warning: Failed to list directory {self.path}: {e}")
            return []
            
        return files
    
    def _load_items(self) -> List[Path]:
        """Load items from the index file or sort by creation time."""
        if self._items is not None:
            return self._items
            
        # Try to load order from index.yml
        if self.vfs.exists(self._index_file):
            try:
                with self.vfs.open(self._index_file, 'r') as f:
                    data = yaml.safe_load(f) or {}
                
                # If index.yml has an 'order' key, use it
                if 'order' in data and isinstance(data['order'], list):
                    # Get existing files that match the prefix
                    existing_files = set()
                    if self.vfs.exists(self.path) and self.vfs.isdir(self.path):
                        try:
                            for entry in self.vfs.listdir(self.path):
                                entry_path = self.path / entry
                                if (self.vfs.isfile(entry_path) and 
                                    not entry.startswith('.') and 
                                    (not self._prefix or entry.startswith(self._prefix))):
                                    existing_files.add(entry)
                        except Exception as e:
                            print(f"Warning: Failed to list directory {self.path}: {e}")
                    
                    # Filter the order list to only include existing files that match the prefix
                    ordered_items = []
                    for item in data['order']:
                        item_str = str(item)
                        if (item_str in existing_files and 
                            (not self._prefix or item_str.startswith(self._prefix))):
                            ordered_items.append(Path(item_str))
                    
                    self._items = ordered_items
                    return self._items
                    
            except Exception as e:
                print(f"Warning: Failed to load order from index.yml: {e}")
        
        # Fall back to creation time sorting
        self._items = self._get_files_sorted_by_creation()
        return self._items
    
    def _save_items(self) -> None:
        """Save items to the index.yml file."""
        if self._items is None:
            return
            
        # Create a simple structure with just the order
        data = {'order': [str(item) for item in self._items]}
        
        # Save to index.yml
        with self.vfs.open(self._index_file, 'w') as f:
            yaml.safe_dump(data, f, default_flow_style=False)
    
    def set_prefix(self, prefix: str) -> None:
        """Set the prefix for filtering files."""
        self._prefix = prefix
        # Invalidate cache to force reload with new prefix
        self._items = None
    
    def get_ordered_items(self) -> List[Path]:
        """Get items in their defined order.
        
        Returns:
            List of paths to files that match the prefix, in the defined order.
        """
        # Ensure we have the latest files that match the prefix
        self._items = None
        return self._load_items().copy()
    
    def set_ordered_items(self, items: List[Path]) -> None:
        """Set the order of items.
        
        Args:
            items: List of paths to include in the order. Only files that start with
                  the current prefix will be included.
        """
        # Filter items to only include those that match the current prefix
        filtered_items = [
            Path(item) for item in items 
            if str(item).startswith(self._prefix) and 
               self.vfs.exists(self.path / item) and 
               self.vfs.isfile(self.path / item)
        ]
        
        # Keep any existing items that match the prefix but aren't in the new list
        current_items = {str(item) for item in self._load_items()}
        new_items = {str(item) for item in filtered_items}
        
        # Add any items that match the prefix but weren't in the new list
        for item in current_items - new_items:
            if item.startswith(self._prefix):
                filtered_items.append(Path(item))
        
        self._items = filtered_items
        self._save_items()
    
    def add_item(self, item: Path) -> None:
        """Add an item to the order if it matches the prefix.
        
        Args:
            item: The item to add. Will only be added if it starts with the prefix.
        """
        item = Path(item)
        if not str(item).startswith(self._prefix):
            return
            
        items = self._load_items()
        if item not in items and self.vfs.exists(self.path / item) and self.vfs.isfile(self.path / item):
            items.append(item)
            self._items = items
            self._save_items()
            
    # Alias for backward compatibility
    append_item = add_item
    
    def remove_item(self, item: Path) -> None:
        """Remove an item from the order.
        
        Args:
            item: The item to remove.
        """
        items = self._load_items()
        item = Path(item)
        if item in items:
            items.remove(item)
            self._items = items
            self._save_items()
