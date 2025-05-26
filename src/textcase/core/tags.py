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
"""Default implementation of ModuleTags."""

import os
from pathlib import Path
from typing import Dict, List, Optional, Set

from ..protocol.vfs import VFS

class FileBasedTags:
    """Tag implementation using individual tag files (similar to .gitignore)."""
    
    def __init__(self, path: Path, vfs: VFS):
        """Initialize with module path and VFS."""
        self.path = path
        self.vfs = vfs
        self._tags_dir = path / '.textcase' / 'tags'
        self._cache: Optional[Dict[str, Set[Path]]] = None
    
    def _ensure_tags_dir(self) -> None:
        """Ensure the tags directory exists."""
        if not self.vfs.exists(self._tags_dir):
            self.vfs.makedirs(self._tags_dir, exist_ok=True)
    
    def _load_tag_file(self, tag: str) -> Set[Path]:
        """Load a single tag file."""
        tag_file = self._tags_dir / f"{tag}.tag"
        if not self.vfs.exists(tag_file):
            return set()
            
        items = set()
        with self.vfs.open(tag_file, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    items.add(Path(line))
        return items
    
    def _load_all_tags(self) -> Dict[str, Set[Path]]:
        """Load all tags from the filesystem."""
        if self._cache is not None:
            return self._cache
            
        if not self.vfs.exists(self._tags_dir):
            self._cache = {}
            return self._cache
            
        tags = {}
        for entry in self.vfs.listdir(self._tags_dir):
            if entry.name.endswith('.tag'):
                tag_name = entry.name[:-4]  # Remove .tag extension
                tags[tag_name] = self._load_tag_file(tag_name)
                
        self._cache = tags
        return tags
    
    def _save_tag(self, tag: str, items: Set[Path]) -> None:
        """Save a tag to its file."""
        self._ensure_tags_dir()
        tag_file = self._tags_dir / f"{tag}.tag"
        
        if not items:
            if self.vfs.exists(tag_file):
                self.vfs.remove(tag_file)
            return
            
        with self.vfs.open(tag_file, 'w') as f:
            for item in sorted(str(i) for i in items):
                f.write(f"{item}\n")
    
    def get_tags(self) -> Dict[str, List[Path]]:
        """Get all tags and their associated items."""
        return {tag: sorted(items) for tag, items in self._load_all_tags().items()}
    
    def get_items_with_tag(self, tag: str) -> List[Path]:
        """Get all items with the given tag."""
        return sorted(self._load_all_tags().get(tag, set()))
    
    def add_tag(self, item: Path, tag: str) -> None:
        """Add a tag to an item."""
        tags = self._load_all_tags()
        if tag not in tags:
            tags[tag] = set()
            
        if item not in tags[tag]:
            tags[tag].add(item)
            self._save_tag(tag, tags[tag])
    
    def remove_tag(self, item: Path, tag: str) -> None:
        """Remove a tag from an item."""
        tags = self._load_all_tags()
        if tag in tags and item in tags[tag]:
            tags[tag].remove(item)
            self._save_tag(tag, tags[tag])
    
    def invalidate_cache(self) -> None:
        """Invalidate the tag cache."""
        self._cache = None
