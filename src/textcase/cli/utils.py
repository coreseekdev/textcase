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
"""Utility functions for CLI commands."""

import os
import re
import shutil
import click
from pathlib import Path
from typing import List, Optional, Tuple, Dict, Any, Union

from textcase.protocol.module import Module, DocumentCaseItem

def debug_echo(ctx: click.Context, message: str) -> None:
    """Echo a debug message only if verbose mode is enabled.
    
    Args:
        ctx: The Click context object.
        message: The message to echo.
    """
    if ctx.obj.get('verbose', False):
        click.echo(f"Debug: {message}")


def parse_document_id(doc_id: str, project, ctx = None) -> Tuple[Optional[str], Optional[str], Optional[str], Optional[str]]:
    """
    Parse a document ID into its components.
    
    This function handles document IDs in various formats:
    - PREFIX[ID] (e.g., REQ001, TST42)
    - PREFIX[ID]/REGION (e.g., REQ001/meta, TST42/content)
    - PREFIX/RESOURCE (e.g., REQ/items, REQ/modules, REQ/tags)
    
    It uses a right-to-left matching approach to find the longest prefix
    that matches an existing module.
    
    Args:
        doc_id: The document ID to parse
        project: The project to search for modules
        ctx: Optional Click context for debug output
        
    Returns:
        Tuple of (module_prefix, item_id, formatted_id, region) or (None, None, None, None) if not found
        - module_prefix: The prefix of the module (e.g., 'REQ')
        - item_id: The ID part without formatting (e.g., '1'), or resource type for module resources
        - formatted_id: The full formatted ID (e.g., 'REQ001'), or module prefix for module resources
        - region: The region specifier if present (e.g., 'meta', 'content'), or None
    """
    if ctx:
        debug_echo(ctx, f"Parsing document ID: {doc_id}")
    
    # Initialize return values
    module_prefix = None
    item_id = None
    formatted_id = None
    region = None
    
    # Store original doc_id for reference
    original_doc_id = doc_id
    
    # Get all available modules
    modules = [project] + project.get_submodules()
    modules = [m for m in modules if hasattr(m, 'prefix') and m.prefix]
    
    # Sort modules by prefix length (longest first) to ensure we match the longest prefix
    modules.sort(key=lambda m: len(m.prefix), reverse=True)
    
    if ctx:
        debug_echo(ctx, f"Available modules: {[m.prefix for m in modules]}")
    
    # First try exact match with any module
    for module in modules:
        if doc_id.upper() == module.prefix:
            # This is just the module prefix with no ID
            if ctx:
                debug_echo(ctx, f"Matched exact module prefix: {module.prefix}")
            return module.prefix, "", module.prefix, region
    
    # Try to find the longest prefix that matches
    for module in modules:
        prefix = module.prefix
        if doc_id.upper().startswith(prefix):
            # Extract the ID part (everything after the prefix)
            remaining = doc_id[len(prefix):]
            
            # Check if there's a separator
            settings = module.config.settings
            separator = settings.get('sep', '')
            
            # If there's a separator, make sure it's present
            if separator and remaining.startswith(separator):
                remaining = remaining[len(separator):]
            
            # Now check if there's a region specifier in the remaining part
            raw_id = remaining
            
            # 支持两种分隔符：'/' 和 ':'
            # 优先使用 '/' 作为分隔符，如果没有则尝试 ':'
            if '/' in remaining:
                parts = remaining.split('/', 1)
                raw_id = parts[0]
                region = parts[1] # 不能改大小写，因为 region 实际是定位到 document 的 path.
                
                if ctx:
                    debug_echo(ctx, f"Found potential region specifier: {region} in remaining part: {remaining}")
            elif ':' in remaining:
                # 向后兼容，支持旧的 ':' 分隔符
                parts = remaining.split(':', 1)
                raw_id = parts[0]
                region = parts[1] # 不能改大小写，因为 region 实际是定位到 document 的 path.
                
                if ctx:
                    debug_echo(ctx, f"Found potential region specifier (legacy format): {region} in remaining part: {remaining}")
                    
            # 检查是否是模块资源路径（如 REQ/item, REQ/module 等）
            resource_types = {
                'item': ['item', 'items'],
                'module': ['module', 'modules'],
                'tag': ['tag', 'tags'],
                'template': ['template', 'templates'],
            }
            
            # 检查是否是支持的资源类型
            for resource_type, aliases in resource_types.items():
                if not raw_id and region in aliases:
                    if ctx:
                        debug_echo(ctx, f"Detected module resource path: {prefix}/{region}")
                    # 返回标准化的资源类型（单数形式）
                    return prefix, resource_type, prefix, None
            
            # Format the ID according to module settings
            digits = settings.get('digits', 3)  # Default to 3 digits
            
            # Format numeric IDs with leading zeros based on digits setting
            if raw_id.isdigit():
                formatted_num = f"{int(raw_id):0{digits}d}"
                formatted_id = f"{prefix}{separator}{formatted_num}"
            else:
                formatted_id = f"{prefix}{separator}{raw_id}"
            
            if ctx:
                debug_echo(ctx, f"Matched module: {prefix}, raw_id: {raw_id}, formatted_id: {formatted_id}, region: {region}")
            
            # Process the region if it was found
            # 不检查 region 的实际取值            
            return prefix, raw_id, formatted_id, region
    
    # If we get here, no match was found
    if ctx:
        debug_echo(ctx, f"Could not match document ID to any module: {doc_id}")
    
    return module_prefix, item_id, formatted_id, region


def get_document_item(doc_id: str, project, ctx = None) -> Tuple[Optional[DocumentCaseItem], Optional[str]]:
    """
    Get a document item from a document ID.
    
    Args:
        doc_id: The document ID to parse
        project: The project to search for modules
        ctx: Optional Click context for debug output
        
    Returns:
        Tuple of (case_item, region) or (None, None) if not found
        - case_item: The document case item
        - region: The region specifier if present (e.g., 'meta', 'content'), or None
    """
    # Parse the document ID
    module_prefix, item_id, formatted_id, region = parse_document_id(doc_id, project, ctx)
    
    if not module_prefix or not formatted_id:
        if ctx:
            debug_echo(ctx, f"Could not parse document ID: {doc_id}")
        return None, region
    
    # Find the module
    target_module = None
    if project.prefix == module_prefix:
        target_module = project
    else:
        for submodule in project.get_submodules():
            if hasattr(submodule, 'prefix') and submodule.prefix == module_prefix:
                target_module = submodule
                break
    
    if not target_module:
        if ctx:
            debug_echo(ctx, f"Could not find module for prefix: {module_prefix}")
        return None, region
    
    # Get the document item
    try:
        # Use the raw ID without formatting to get the item
        case_item = target_module.get_document_item(item_id)
        
        # Set the path if needed
        if hasattr(case_item, 'path') and case_item.path is None:
            doc_path = target_module.path / f"{formatted_id}.md"
            case_item.path = doc_path
        
        if ctx:
            debug_echo(ctx, f"Found document item: {case_item.key}")
        
        return case_item, region
    except Exception as e:
        if ctx:
            debug_echo(ctx, f"Error getting document item: {e}")
        return None, region


def get_document_path(doc_id: str, project, ctx = None) -> Tuple[Optional[Path], Optional[Module], Optional[str], Optional[str]]:
    """
    Get the document path from a document ID.
    
    Args:
        doc_id: The document ID in the format PREFIX[ID][:region]
        project: The project to search in
        ctx: Click context for debug output
        
    Returns:
        A tuple of (document_path, module, formatted_id, region) or (None, None, None, None) if not found
    """
    # Parse the document ID
    module_prefix, item_id, formatted_id, region = parse_document_id(doc_id, project, ctx)
    
    if not module_prefix or not formatted_id:
        if ctx:
            debug_echo(ctx, f"Could not parse document ID: {doc_id}")
        return None, None, None, region
    
    # Find the module
    target_module = None
    if project.prefix == module_prefix:
        target_module = project
    else:
        for submodule in project.get_submodules():
            if hasattr(submodule, 'prefix') and submodule.prefix == module_prefix:
                target_module = submodule
                break
    
    if not target_module:
        if ctx:
            debug_echo(ctx, f"Could not find module for prefix: {module_prefix}")
        return None, None, None, region
    
    # Create the file path
    file_path = target_module.path / f"{formatted_id}.md"
    
    if ctx:
        debug_echo(ctx, f"Resolved file path: {file_path}")
    
    return file_path, target_module, formatted_id, region


def get_template_source_dir() -> Path:
    """
    Get the directory containing the default templates.
    
    Returns:
        Path to the templates directory
    """
    # Get the package directory
    current_file = Path(__file__)
    print(f"Current file: {current_file}")
    print(f"Current file absolute: {current_file.absolute()}")
    print(f"Current file dir: {current_file.parent}")
    print(f"Current file dir absolute: {current_file.parent.absolute()}")
    
    package_dir = current_file.parent.parent.parent
    print(f"Package dir: {package_dir}")
    print(f"Package dir absolute: {package_dir.absolute()}")
    
    # Templates are stored in the data/templates directory
    templates_dir = package_dir / "data" / "templates"
    print(f"Templates dir: {templates_dir}")
    print(f"Templates dir absolute: {templates_dir.absolute()}")
    print(f"Templates dir exists: {templates_dir.exists()}")
    
    return templates_dir


def copy_templates_to_project(module: Module, ctx=None) -> bool:
    """
    Copy the default templates to the project's .config/template directory.
    
    Args:
        module: The project module
        ctx: Optional Click context for debug output
        
    Returns:
        True if successful, False otherwise
    """
    # Get the source templates directory
    source_dir = get_template_source_dir()
    if not source_dir.exists() or not source_dir.is_dir():
        if ctx:
            debug_echo(ctx, f"Templates directory not found: {source_dir}")
        return False
        
    # Create the target directory
    target_dir = module.path / ".config" / "template"
    target_dir.mkdir(parents=True, exist_ok=True)
    
    # Copy all template files
    copied = 0
    for template_file in source_dir.iterdir():
        if template_file.is_file():
            target_file = target_dir / template_file.name
            if not target_file.exists():
                shutil.copy2(template_file, target_file)
                copied += 1
                if ctx:
                    debug_echo(ctx, f"Copied template: {template_file.name}")
    
    if ctx:
        debug_echo(ctx, f"Copied {copied} templates to {target_dir}")
    
    return True


def list_available_templates(module: Module) -> List[str]:
    """
    List the available templates in the project's .config/template directory.
    
    Args:
        module: The project module
        
    Returns:
        List of template names (without extensions)
    """
    template_dir = module.path / ".config" / "template"
    if not template_dir.exists() or not template_dir.is_dir():
        return []
        
    templates = []
    for template_file in template_dir.iterdir():
        if template_file.is_file():
            templates.append(template_file.stem)
            
    return templates
