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
"""Create command implementation."""

import os
import sys
import click
from pathlib import Path
from typing import Optional, Dict, Any, List

from textcase.core.module import YamlModule
from textcase.protocol.module import Module
from textcase.cli.utils import debug_echo, copy_templates_to_project

@click.command()
@click.argument('prefix', type=str)
@click.argument('module_path', type=click.Path(path_type=Path))
@click.option('--parent', help='Parent module prefix (required for submodules)')
@click.option('-s', '--sep', help='Separator between prefix and ID (e.g., "-" for REQ-001)')
@click.option('--digits', type=int, help='Number of digits for IDs (e.g., 3 for REQ001, 4 for REQ0001)')
@click.option('--settings', help='Additional module settings in format key1=value1,key2=value2')
@click.option('--tags', help='Module tags in format tag1=description1,tag2=description2')
@click.pass_context
def create(ctx: click.Context, prefix: str, module_path: Path, parent: Optional[str] = None, 
         sep: Optional[str] = None, digits: Optional[int] = None,
         settings: Optional[str] = None, tags: Optional[str] = None):
    """Create a new module or submodule.
    
    PREFIX is the module prefix (e.g., REQ, TST).
    MODULE_PATH is the path where the module will be created.
    
    Example usage:
      textcase create REQ ./reqs/
      textcase create TST ./reqs/tests --parent REQ
    """
    # Get VFS from context (always available)
    vfs = ctx.obj['vfs']
    
    # Check if we have a valid project
    project = ctx.obj.get('project')
    project_path = None
    
    # If parent is specified, we MUST have a valid project
    if parent and not project:
        click.echo(f"Error: Parent module '{parent}' specified but no valid project found.", err=True)
        click.echo("A valid project with a .textcase.yml file is required when creating submodules.")
        ctx.exit(1)
    
    # Debug project information
    if project:
        debug_echo(ctx, f"Project path: {project.path}")
        debug_echo(ctx, f"Project prefix: {project.prefix}")
        # Safely get submodules
        try:
            submodules = project.get_submodules()
            submodule_prefixes = []
            for m in submodules:
                try:
                    if hasattr(m, 'prefix'):
                        submodule_prefixes.append(m.prefix)
                except Exception:
                    pass
            debug_echo(ctx, f"Available submodules: {submodule_prefixes}")
        except Exception as e:
            debug_echo(ctx, f"Error getting submodules: {e}")
    
    # Resolve module path
    if project and not module_path.is_absolute():
        # If we have a project, resolve relative to project path
        # Convert to absolute path first to handle any '..' or '.' in the path
        abs_module_path = (Path.cwd() / module_path).resolve()
        # If the resolved path is within the project directory, use the relative path from project root
        try:
            rel_path = abs_module_path.relative_to(project.path)
            module_path = project.path / rel_path
        except ValueError:
            # If not relative to project path, use as is
            module_path = abs_module_path
        project_path = project.path
    else:
        # Otherwise, resolve relative to current directory
        if not module_path.is_absolute():
            module_path = (Path.cwd() / module_path).resolve()
        project_path = Path.cwd()
    
    # Check if parent module exists when specified
    parent_prefix = None
    if parent:
        debug_echo(ctx, f"Looking for parent module with prefix '{parent}'")
        # 父模块是否是 Project 自身
        if parent == project.prefix:
            debug_echo(ctx, f"Parent module is the project itself")
            parent_prefix = project.prefix
        else:
            # Check if the project has the parent module in its configuration
            parent_info = project.config.get_submodule(parent)
            debug_echo(ctx, f"Parent info from config: {parent_info}")
            if not parent_info:
                click.echo(f"Error: Parent module with prefix '{parent}' not found in project configuration", err=True)
                ctx.exit(1)
            else:
                # Parent exists in config, use its prefix
                parent_prefix = parent
                debug_echo(ctx, f"Using parent prefix: {parent_prefix}")
    
    # Check if .textcase.yml already exists in the target directory
    config_file = module_path / '.textcase.yml'
    if vfs.exists(config_file):
        click.echo(f"Error: Cannot create module at '{module_path}' - .textcase.yml already exists", err=True)
        ctx.exit(1)
        
    # Create the module directory if it doesn't exist
    try:
        vfs.makedirs(module_path, exist_ok=True)
    except Exception as e:
        click.echo(f"Error creating module directory: {e}", err=True)
        ctx.exit(1)
    
    # Create the module instance
    try:
        debug_echo(ctx, f"Creating module at {module_path}")
        module = YamlModule(module_path, vfs)
        
        # Configure module settings
        default_settings = {
            'prefix': prefix,
            'digits': 3,
            'sep': '',
            'default_tag': []
        }
        
        # Apply command-line options if provided
        if sep is not None:
            default_settings['sep'] = sep
            
        if digits is not None:
            default_settings['digits'] = digits
        
        # Parse and apply additional custom settings if provided
        if settings:
            custom_settings = parse_key_value_string(settings)
            default_settings.update(custom_settings)
        
        module.config.settings.update(default_settings)
        
        # Parse and apply tags if provided
        if tags:
            tag_dict = parse_key_value_string(tags)
            module.config.tags.update(tag_dict)
        
        # Save the module configuration
        module.save()
        
        # Add the module to the project if we have one
        if project:
            debug_echo(ctx, f"Adding module to project")
            try:
                # If this is a submodule, add it to the parent
                if parent_prefix:
                    debug_echo(ctx, f"Using parent prefix: '{parent_prefix}'")
                    # Register the module in the project configuration
                    project.config.add_submodule(prefix, module_path.relative_to(project.path), parent_prefix)
                    # Save the configuration
                    project.config.save(vfs)
                    click.echo(f"Created submodule '{prefix}' at {module_path} with parent '{parent}'")
                else:
                    # Add as a root module
                    # Register the module in the project configuration as a root module
                    project.config.add_submodule(prefix, module_path.relative_to(project.path))
                    # Save the configuration
                    project.config.save(vfs)
                    click.echo(f"Created module '{prefix}' at {module_path}")
            except Exception as e:
                click.echo(f"Error adding module to project: {e}", err=True)
                ctx.exit(1)
            
            # Save the project to update configuration
            project.save()
            
            # If this is a root module (project), copy templates to .config/template
            if not parent_prefix:
                debug_echo(ctx, f"Copying templates to project")
                copy_templates_to_project(module, ctx)
        else:
            # Just create the module without adding to a project - this is a root module
            click.echo(f"Created module '{prefix}' at {module_path}")
            # Save just the module configuration
            module.save()
            
            # Copy templates to .config/template
            debug_echo(ctx, f"Copying templates to module")
            copy_templates_to_project(module, ctx)
        
    except Exception as e:
        click.echo(f"Error creating module: {e}", err=True)
        ctx.exit(1)


def parse_key_value_string(kv_string: str) -> Dict[str, Any]:
    """Parse a key-value string in the format key1=value1,key2=value2.
    
    Args:
        kv_string: String in format key1=value1,key2=value2
        
    Returns:
        Dictionary of parsed key-value pairs
    """
    result = {}
    if not kv_string:
        return result
        
    pairs = kv_string.split(',')
    for pair in pairs:
        if '=' in pair:
            key, value = pair.split('=', 1)
            key = key.strip()
            value = value.strip()
            
            # Try to convert value to appropriate type
            if value.lower() == 'true':
                value = True
            elif value.lower() == 'false':
                value = False
            elif value.isdigit():
                value = int(value)
            elif value.startswith('[') and value.endswith(']'):
                # Parse as list
                items = value[1:-1].split(';')
                value = [item.strip() for item in items if item.strip()]
                
            result[key] = value
    
    return result
