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
"""Module listing functions for the list command."""

import click
from pathlib import Path
from typing import Optional, List, Dict, Any, Set

from textcase.protocol.module import Module
from textcase.cli.utils import debug_echo, list_available_templates


def list_module_items(module: Module, ctx: click.Context) -> None:
    """
    List all items in a module.
    
    Args:
        module: The module to list items from
        ctx: Click context for debug output
    """
    if not module:
        click.echo("Error: Module not found", err=True)
        return
        
    # Get the module's prefix
    prefix = module.prefix
    if not prefix:
        click.echo(f"Error: Module has no prefix", err=True)
        return
        
    # Get all items in the module
    items = []
    if hasattr(module, 'path') and module.path.exists():
        for item in module.path.iterdir():
            if item.is_file() and item.suffix.lower() in ['.md', '.markdown']:
                # Check if the file matches the module's prefix pattern
                if item.stem.upper().startswith(prefix):
                    items.append(item)
                    
    if not items:
        click.echo(f"No items found in module '{prefix}'")
        return
        
    # Sort items by name
    items.sort(key=lambda x: x.stem)
    
    # Display the items
    click.echo(f"Items in module '{prefix}':")
    for item in items:
        # Extract the item ID from the filename, removing any extension
        item_id = item.stem
        
        # If the item_id contains a secondary extension (like .msg in CHAT001.msg), remove it
        if '.' in item_id:
            item_id = item_id.split('.')[0]
        
        # Try to get the title from the file
        title = ""
        try:
            with open(item, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line.startswith('# '):
                        title = line[2:].strip()
                        break
        except Exception:
            pass
            
        # Display the item
        if title:
            click.echo(f"  - {item_id}: {title}")
        else:
            click.echo(f"  - {item_id}")


def list_module_submodules(module: Module, ctx: click.Context) -> None:
    """
    List all submodules of a module.
    
    Args:
        module: The module to list submodules from
        ctx: Click context for debug output
    """
    if not module:
        click.echo("Error: Module not found", err=True)
        return
        
    # Get the module's prefix
    prefix = module.prefix
    if not prefix:
        click.echo(f"Error: Module has no prefix", err=True)
        return
        
    # Get all submodules
    submodules = module.get_submodules() if hasattr(module, 'get_submodules') else []
    
    if not submodules:
        click.echo(f"No submodules found for module '{prefix}'")
        return
        
    # Sort submodules by prefix and remove duplicates
    unique_prefixes = set()
    unique_submodules = []
    
    for submodule in submodules:
        if hasattr(submodule, 'prefix') and submodule.prefix:
            if submodule.prefix not in unique_prefixes:
                unique_prefixes.add(submodule.prefix)
                unique_submodules.append(submodule)
    
    # Sort by prefix
    unique_submodules.sort(key=lambda x: x.prefix)
    
    # Display the submodules
    click.echo(f"Submodules of '{prefix}':")
    for submodule in unique_submodules:
        submodule_prefix = submodule.prefix
        click.echo(f"  - {submodule_prefix}")


def list_module_tags(module: Module, ctx: click.Context) -> None:
    """
    List all tags in a module.
    
    Args:
        module: The module to list tags from
        ctx: Click context for debug output
    """
    if not module:
        click.echo("Error: Module not found", err=True)
        return
        
    # Get the module's prefix
    prefix = module.prefix
    if not prefix:
        click.echo(f"Error: Module has no prefix", err=True)
        return
        
    # Get all tags
    tags = {}
    
    # 检查标签是否以对象形式存在
    if hasattr(module, 'tags') and hasattr(module.tags, 'get_all_tags'):
        tags = module.tags.get_all_tags()
    # 检查标签是否以列表形式存在
    elif hasattr(module, 'config'):
        try:
            # 尝试使用 getattr 获取 tags 属性
            tag_list = getattr(module.config, 'tags', None)
            if tag_list:
                if isinstance(tag_list, list):
                    tags = {tag: "" for tag in tag_list}
                elif isinstance(tag_list, dict):
                    tags = tag_list
        except Exception as e:
            if ctx:
                debug_echo(ctx, f"Error getting tags from config: {e}")
            pass
    
    if ctx:
        debug_echo(ctx, f"Found tags: {tags}")
        
    if not tags:
        click.echo(f"No tags found in module '{prefix}'")
        return
        
    # Display the tags
    click.echo(f"Tags in module '{prefix}':")
    for tag_name, tag_desc in sorted(tags.items()):
        if tag_desc:
            click.echo(f"  - {tag_name}: {tag_desc}")
        else:
            click.echo(f"  - {tag_name}")


def list_templates(module: Module, ctx: click.Context) -> None:
    """
    List all templates in a module.
    
    Args:
        module: The module to list templates from
        ctx: Click context for debug output
    """
    templates = list_available_templates(module)
    
    if not templates:
        click.echo("No templates found")
        return
        
    click.echo("Available templates:")
    for template in sorted(templates):
        click.echo(f"  - {template}")


def list_root_modules(project: Module, ctx: click.Context) -> None:
    """
    List all root-level modules and available templates.
    
    Args:
        project: The project to list modules from
        ctx: Click context for debug output
    """
    # List root-level modules
    modules = project.get_submodules() if hasattr(project, 'get_submodules') else []
    
    # Use a set to track unique module prefixes
    unique_prefixes = set()
    
    if modules:
        click.echo("Available modules:")
        # Sort modules by prefix
        for module in sorted(modules, key=lambda x: x.prefix if hasattr(x, 'prefix') and x.prefix else ""):
            if hasattr(module, 'prefix') and module.prefix:
                # Only add each prefix once
                if module.prefix not in unique_prefixes:
                    unique_prefixes.add(module.prefix)
                    click.echo(f"  - {module.prefix}")
    else:
        click.echo("No modules found")
        
    # List available templates
    templates = list_available_templates(project)
    if templates:
        click.echo("\nAvailable templates:")
        for template in sorted(templates):
            click.echo(f"  - {template}")
    else:
        click.echo("\nNo templates found")
