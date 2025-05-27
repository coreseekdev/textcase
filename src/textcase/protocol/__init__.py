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
"""Protocol definitions for TextCase."""

from pathlib import Path
from typing import Any, Dict, List, Optional, Type, TypeVar, Union

# VFS protocol
from .vfs import VFS, FileHandle, FileStat, FileSeek, TempDir

# Module protocol
from .module import (
    Module,
    ModuleConfig,
    ModuleOrder
)

# For backward compatibility
from .vfs import VFS as VFSProtocol

__all__ = [
    # VFS related
    'VFS',
    'VFSProtocol',
    'FileHandle',
    'FileStat',
    'FileSeek',
    'TempDir',
    
    # Module related
    'Module',
    'ModuleConfig',
    'ModuleOrder',
    'ModuleTags',
]
