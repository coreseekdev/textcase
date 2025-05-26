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
"""Core functionality for TextCase."""

from pathlib import Path
from typing import Any, Dict, List, Optional, Type, TypeVar, Union

from ..protocol import (
    VFS,
    FileHandle,
    FileStat,
    Module,
    ModuleConfig,
    ModuleOrder,
    ModuleTags,
)

from .localfs import LocalVFS, LocalFileHandle
from .order import YamlOrder
from .tags import FileBasedTags
from .module import BaseModule, ProjectModule

__all__ = [
    # Core implementations
    'LocalVFS',
    'LocalFileHandle',
    'YamlOrder',
    'FileBasedTags',
    'BaseModule',
    'ProjectModule',
    
    # Re-exported from protocol for convenience
    'VFS',
    'FileHandle',
    'FileStat',
    'Module',
    'ModuleConfig',
    'ModuleOrder',
    'ModuleTags',
]
