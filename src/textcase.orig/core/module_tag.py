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
from typing import Dict, List, Optional, Set, cast
import yaml

from ..protocol.module import CaseItem, DocumentCaseItem, ModuleTagging, Project
from ..protocol.vfs import VFS


class FileBasedModuleTags(ModuleTagging):
    """File-based implementation for module-level tag storage.
    
    Each tag is stored as a file in the module directory, where the filename is the tag name.
    Each line in the file represents an item key that has that tag.
    """
    
    def __init__(self, project: Project, path: Path, vfs: VFS):
        self._cache: Optional[Dict[str, Set[str]]] = None
        """Initialize with module path, VFS, and optional parent tags.
        
        Args:
            project: The project to which this module belongs.
            path: The path to the module directory.
            vfs: The virtual filesystem to use for I/O operations.
        """
        # 隐含，必须绑定 project 才能访问 tag 机制
        self._project = project
        self.path = path
        self._vfs = vfs
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
            
        try:
            with self._vfs.open(tag_file, 'r') as f:
                content = f.read()
                # Ensure we decode bytes to string if needed
                if isinstance(content, bytes):
                    content = content.decode('utf-8')
                return {line.strip() for line in content.splitlines() if line.strip()}
        except Exception as e:
            print(f"Error reading tag file {tag_file}: {e}")
            return set()
    
    def _write_tag_file(self, tag_file: Path, item_keys: Set[str]) -> None:
        """Write item keys to a tag file."""
        try:
            content = '\n'.join(sorted(item_keys)) + '\n' if item_keys else ''
            # Ensure we write strings, not bytes
            if isinstance(content, str):
                content = content.encode('utf-8')
            with self._vfs.open(tag_file, 'wb') as f:  # Use binary mode for consistency
                f.write(content)
        except Exception as e:
            print(f"Error writing to tag file {tag_file}: {e}")
    
    def add_tag(self, item: CaseItem, tag: str) -> None:
        if not isinstance(item, DocumentCaseItem):
            raise ValueError("Only DocumentCaseItem is supported")
        
        doc_item = cast(DocumentCaseItem, item)
        """Add a tag to a document item.
        
        Args:
            item: The document item to tag.
            tag: The tag to add.
            
        Raises:
            ValueError: If the tag is not in the available tags list.
        """
        # Check if tag is in available tags
        # 注意，此处的实现并没有限制 item 是 当前模块的。
        # 如果调用时不注意，是可能存在 某个模块的 item 的 tag 关系记录到其他模块了
        available_tags = self.get_tags(doc_item.prefix)
        if tag not in available_tags:
            raise ValueError(f"Tag '{tag}' is not in the available tags list")
            
        tag_file = self._get_tag_file(tag)
        item_keys = self._read_tag_file(tag_file)
        item_keys.add(doc_item.key)
        self._write_tag_file(tag_file, item_keys)
        self.invalidate_cache()
    
    def remove_tag(self, item: CaseItem, tag: str) -> None:
        if not isinstance(item, DocumentCaseItem):
            raise ValueError("Only DocumentCaseItem is supported")
            
        doc_item = cast(DocumentCaseItem, item)
        """Remove a tag from a document item.
        
        Args:
            item: The document item to untag.
            tag: The tag to remove.
        """
        tag_file = self._get_tag_file(tag)
        item_keys = self._read_tag_file(tag_file)
        
        if doc_item.key in item_keys:
            item_keys.remove(doc_item.key)
            if item_keys:
                self._write_tag_file(tag_file, item_keys)
            else:
                # Remove the tag file if it's empty
                self._vfs.remove(tag_file)
            self.invalidate_cache()
    
    def get_item_tags(self, item: CaseItem) -> List[str]:
        if not isinstance(item, DocumentCaseItem):
            raise ValueError("Only DocumentCaseItem is supported")
            
        doc_item = cast(DocumentCaseItem, item)
        """Get all tags for a specific item.
        
        Only checks tag files that are in the available tags list.
        """
        if not self._vfs.exists(self.path):
            return []
            
        # Get all available tags for this item's prefix
        available_tags = self.get_tags(doc_item.prefix)
        if not available_tags:
            return []
        
        # print("available_tags: %s" % available_tags)
        # Only check tag files that are in the available tags
        tags = []
        for tag in available_tags:
            tag_file = self._get_tag_file(tag)
            if self._vfs.isfile(tag_file):
                # print("read tag_file: %s" % doc_item.key)
                # print("tag_file items: %s" % self._read_tag_file(tag_file))
                # Check if the document ID is in the tag file
                if doc_item.key in self._read_tag_file(tag_file):
                    tags.append(tag)
                    
        return sorted(tags)  
    
    def _load_tags(self, path: Path, vfs: VFS) -> Set[str]:
        """Load all available tag names from the config file."""
        _config_file = path / '.textcase.yml'
        
        if not vfs.exists(_config_file):
            return set()
            
        with vfs.open(_config_file, 'r') as f:
            config = yaml.safe_load(f) or {}
            
        return set(config.get('tags', {}).keys())

    def get_tags(self, prefix: Optional[str] = None) -> List[str]:
        """Get all available tags, optionally filtered by prefix.
        
        Args:
            prefix: Optional prefix to filter tags by.
            
        Returns:
            A list of available tag names.
        """
        if prefix and self._project:
            return self._project.get_tags(prefix)
        
        
        if self._cache is None:
            self._cache = sorted(self._load_tags(self.path, self._vfs))
        
        return self._cache
    
    def invalidate_cache(self) -> None:
        """Invalidate the tag cache."""
        self._cache = None
