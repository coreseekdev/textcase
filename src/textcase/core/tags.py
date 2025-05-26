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
import yaml
from pathlib import Path
from typing import Dict, List, Optional, Set

from ..protocol.vfs import VFS

class FileBasedTags:
    """Tag implementation using .textcase.yml for storing tags."""
    
    def __init__(self, path: Path, vfs: VFS):
        """Initialize with module path and VFS."""
        self.path = path
        self.vfs = vfs
        self._config_file = path / '.textcase.yml'
        self._cache: Optional[Dict[str, Set[Path]]] = None
    
    def _load_tags(self) -> Dict[str, Set[Path]]:
        """Load all tags from the config file."""
        if not self.vfs.exists(self._config_file):
            return {}
            
        with self.vfs.open(self._config_file, 'r') as f:
            config = yaml.safe_load(f) or {}
            
        tags = config.get('tags', {})
        return {
            tag: {Path(item) for item in items}
            for tag, items in tags.items()
            if isinstance(items, list)
        }
    
    def _load_all_tags(self) -> Dict[str, Set[Path]]:
        """Load all tags from the config file."""
        if self._cache is not None:
            return self._cache
            
        self._cache = self._load_tags()
        return self._cache
    
    def _save_tags(self, tags: Dict[str, Set[Path]]) -> None:
        """Save all tags to the config file."""
        # Load existing config or create new one
        config = {}
        if self.vfs.exists(self._config_file):
            with self.vfs.open(self._config_file, 'r') as f:
                config = yaml.safe_load(f) or {}
        
        # Update the tags in the config
        config['tags'] = {
            tag: sorted(str(item) for item in items)
            for tag, items in tags.items()
            if items  # Only include non-empty tag sets
        }
        
        # Save the updated config
        with self.vfs.open(self._config_file, 'w') as f:
            yaml.safe_dump(config, f, default_flow_style=False)
            
        # Update the cache
        self._cache = {k: v.copy() for k, v in tags.items()}
    
    def get_tags(self) -> Dict[str, List[Path]]:
        """Get all tags and their associated items.
        
        Returns:
            A dictionary mapping tag names to lists of paths, with each list sorted.
        """
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
            self._save_tags(tags)
    
    def remove_tag(self, item: Path, tag: str) -> None:
        """Remove a tag from an item."""
        tags = self._load_all_tags()
        if tag in tags and item in tags[tag]:
            tags[tag].remove(item)
            # If the tag is now empty, remove it completely
            if not tags[tag]:
                del tags[tag]
            self._save_tags(tags)
    
    def invalidate_cache(self) -> None:
        """Invalidate the tag cache."""
        self._cache = None
