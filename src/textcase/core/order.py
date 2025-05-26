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

import yaml
from pathlib import Path
from typing import List, Optional

from ..protocol.vfs import VFS

class YamlOrder:
    """Order implementation using YAML files."""
    
    def __init__(self, path: Path, vfs: VFS):
        """Initialize with module path and VFS."""
        self.path = path
        self.vfs = vfs
        self._order_file = path / '.textcase' / 'order.yml'
        self._items: Optional[List[Path]] = None
    
    def _load_items(self) -> List[Path]:
        """Load items from the order file."""
        if self._items is not None:
            return self._items
            
        if not self.vfs.exists(self._order_file):
            self._items = []
            return self._items
            
        with self.vfs.open(self._order_file, 'r') as f:
            items = yaml.safe_load(f) or []
            
        self._items = [Path(item) for item in items]
        return self._items
    
    def _save_items(self) -> None:
        """Save items to the order file."""
        if self._items is None:
            return
            
        order_dir = self._order_file.parent
        if not self.vfs.exists(order_dir):
            self.vfs.makedirs(order_dir, exist_ok=True)
            
        with self.vfs.open(self._order_file, 'w') as f:
            yaml.safe_dump([str(item) for item in self._items], f, default_flow_style=False)
    
    def get_ordered_items(self) -> List[Path]:
        """Get items in their defined order."""
        return self._load_items().copy()
    
    def add_item(self, item: Path) -> None:
        """Add an item to the ordering."""
        items = self._load_items()
        if item not in items:
            items.append(item)
            self._save_items()
    
    def remove_item(self, item: Path) -> None:
        """Remove an item from the ordering."""
        items = self._load_items()
        if item in items:
            items.remove(item)
            self._save_items()
