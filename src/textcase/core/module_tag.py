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
"""File-based implementation of ModuleTags using files for storage."""

from pathlib import Path
from typing import List, Optional, Set

from ..protocol.module import DocumentCaseItem
from ..protocol.vfs import VFS


class FileBasedModuleTags:
    """File-based implementation for module-level tag storage.
    
    Each tag is stored as a file in the module directory, where the filename is the tag name.
    Each line in the file represents an item key that has that tag.
    """
    
    def __init__(self, path: Path, vfs: VFS, parent_tags: Optional['FileBasedModuleTags'] = None):
        """Initialize with module path, VFS, and optional parent tags.
        
        Args:
            path: The path to the module directory.
            vfs: The virtual filesystem to use for I/O operations.
            parent_tags: Optional parent module's tags for hierarchical tag lookup.
        """
        self.path = path
        self._vfs = vfs
        self.parent_tags = parent_tags
        self._ensure_tag_dir()
    
    def _ensure_tag_dir(self) -> None:
        """Ensure the tag directory exists."""
        if not self._vfs.exists(self.path):
            self._vfs.makedirs(self.path, exist_ok=True)
    
    def _get_tag_file(self, tag_name: str) -> Path:
        """Get the path to the tag file for the given tag name."""
        # Ensure the tag name is a valid filename
        safe_tag = "".join(c if c.isalnum() or c in '._-' else '_' for c in tag_name)
        return self.path / safe_tag
    
    def _read_tag_file(self, tag_file: Path) -> Set[str]:
        """Read all item keys from a tag file."""
        if not self._vfs.exists(tag_file):
            return set()
            
        with self._vfs.open(tag_file, 'r') as f:
            return {line.strip() for line in f if line.strip()}
    
    def _write_tag_file(self, tag_file: Path, item_keys: Set[str]) -> None:
        """Write item keys to a tag file."""
        with self._vfs.open(tag_file, 'w') as f:
            for item_key in sorted(item_keys):
                f.write(f"{item_key}\n")
    
    def add_tag(self, item: DocumentCaseItem, tag: str) -> None:
        """Add a tag to a document item.
        
        Args:
            item: The document item to tag.
            tag: The tag to add.
            
        Raises:
            ValueError: If the tag is not in the available tags list.
        """
        # Check if tag is in available tags
        available_tags = self.get_tags(item.prefix)
        if tag not in available_tags:
            raise ValueError(f"Tag '{tag}' is not in the available tags list")
            
        tag_file = self._get_tag_file(tag)
        item_keys = self._read_tag_file(tag_file)
        item_keys.add(item.key)
        self._write_tag_file(tag_file, item_keys)
    
    def remove_tag(self, item: DocumentCaseItem, tag: str) -> None:
        """Remove a tag from a document item.
        
        Args:
            item: The document item to untag.
            tag: The tag to remove.
        """
        tag_file = self._get_tag_file(tag)
        item_keys = self._read_tag_file(tag_file)
        
        if item.key in item_keys:
            item_keys.remove(item.key)
            if item_keys:
                self._write_tag_file(tag_file, item_keys)
            else:
                # Remove the tag file if it's empty
                self._vfs.remove(tag_file)
    
    def get_item_tags(self, item: DocumentCaseItem) -> List[str]:
        """Get all tags for a specific item.
        
        Only checks tag files that are in the available tags list.
        """
        if not self._vfs.exists(self.path):
            return []
            
        # Get all available tags for this item's prefix
        available_tags = self.get_tags(item.prefix)
        if not available_tags:
            return []
            
        # Only check tag files that are in the available tags
        tags = []
        for tag in available_tags:
            tag_file = self._get_tag_file(tag)
            if self._vfs.isfile(tag_file):
                item_keys = self._read_tag_file(tag_file)
                if item.key in item_keys:
                    tags.append(tag)
                    
        return sorted(tags)  

    def invalidate_cache(self) -> None:
        """Invalidate any cached tag data."""
        # No caching implemented in this version
        pass
    
    def _load_tags(self, path: Path, vfs: VFS) -> Set[str]:
        """Load all available tag names from the config file."""
        _config_file = path / '.textcase.yml'
        
        if not vfs.exists(_config_file):
            return set()
            
        with vfs.open(_config_file, 'r') as f:
            config = yaml.safe_load(f) or {}
            
        return set(config.get('tags', {}).keys())
    
    def _get_all_tags(self, vfs: VFS) -> Dict[str, Set[str]]:
        """Get all tags from this module and its parents recursively."""
        if self._cache is not None:
            return self._cache
            
        tags = self._load_tags(self.path, vfs)
        
        # Include parent tags if available
        if self.parent_tags is not None:
            parent_tags = self.parent_tags._get_all_tags(vfs)
            for tag, items in parent_tags.items():
                if tag in tags:
                    tags[tag].update(items)
                else:
                    tags[tag] = set(items)
        
        return tags
    
    def get_tags(self) -> Dict[str, Set[str]]:
        """Get all tags from this module and its parents recursively."""
        self._cache = self._get_all_tags(self._vfs)
        return self._cache
    
    def invalidate_cache(self) -> None:
        """Invalidate the tag cache."""
        self._cache = None
