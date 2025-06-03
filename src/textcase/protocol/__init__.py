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

# Message protocol
from .message import (
    MessageStore, Message, MessageOutput,
    FunctionCall
)

# LLM protocol
from .llm import (
    LLMResponseProtocol,
    LLMProviderProtocol
)

# Agent protocol
from .agent import (
    AgentProtocol,
    AgentFactoryProtocol
)

# VFS protocol
from .vfs import VFS, FileHandle, FileStat, FileSeek, TempDir

# Base protocols
from .base import (
    ItemBase,
    ItemCollection,
    ModuleBase,
    ModuleConfigBase
)

# Module protocols
from .module import (
    # Base protocols
    ItemBase,
    ItemCollection,
    ModuleBase,
    ModuleConfigBase,
    
    # Document protocols
    DocumentTag,
    DocumentItem,
    DocumentModuleConfig,
    DocumentModuleBase,
    DocumentModule,
    Project,
    ProjectConfig,
    ProjectOutline,
    
    # Source protocols
    FileItem,
    FileModule,
    SourceCodeItem,
    SourceModule,
    
    # Legacy names for backward compatibility
    Module,
    ModuleConfig,
    ModuleOrder,
    ModuleTagging,
    ProjectTags,
    CaseItem,
    DocumentCaseItem
)

# URI protocol
from .uri import (
    URI,
    URIResolver,
    ResourceType
)

# Resource protocol
from .resource import (
    Resource,
    ResourceMetadata,
    ResourceContent,
    ResourceReference,
    ResourceRegistry
)

# Task protocol
from .task import (
    Task,
    TaskList,
    TaskStatus,
    TestCase,
    TestStep,
    TestVerification,
    TestResult,
    TestRunner
)

# API protocol
from .api import (
    APIServer,
    APIRoute,
    APIHandler,
    APIRequest,
    APIResponse,
    APIConfig
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
    
    # Base protocols
    'ItemBase',
    'ItemCollection',
    'ModuleBase',
    'ModuleConfigBase',
    
    # Document protocols
    'DocumentTag',
    'DocumentItem',
    'DocumentModuleConfig',
    'DocumentModuleBase',
    'DocumentModule',
    'Project',
    'ProjectConfig',
    'ProjectOutline',
    
    # Source protocols
    'FileItem',
    'FileModule',
    'SourceCodeItem',
    'SourceModule',
    
    # Legacy module related
    'Module',
    'ModuleConfig',
    'ModuleOrder',
    'ModuleTagging',
    'ProjectTags',
    'CaseItem',
    'DocumentCaseItem',
    
    # URI related
    'URI',
    'URIResolver',
    'ResourceType',
    
    # Resource related
    'Resource',
    'ResourceMetadata',
    'ResourceContent',
    'ResourceReference',
    'ResourceRegistry',
    
    # Task related
    'Task',
    'TaskList',
    'TaskStatus',
    'TestCase',
    'TestStep',
    'TestVerification',
    'TestResult',
    'TestRunner',
    
    # API related
    'APIServer',
    'APIRoute',
    'APIHandler',
    'APIRequest',
    'APIResponse',
    'APIConfig',
    
    # LLM related
    'LLMResponseProtocol',
    'LLMProviderProtocol',
    
    # Agent related
    'AgentProtocol',
    'AgentFactoryProtocol',
]
