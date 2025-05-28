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
"""Add command implementation."""

import os
import re
import time
import threading
import click
from pathlib import Path
from typing import Optional, Tuple, Dict, Any

from textcase.protocol.module import Module
from textcase.core.module import YamlModule
from textcase.cli.utils import debug_echo
from textcase.cli.commands.edit import edit_with_editor, get_editor


def monitor_file_changes(file_path: Path, module: Module, item_id: str, timeout: int = 60) -> None:
    """
    Monitor a file for changes and add it to the module order when changes are detected.
    
    Args:
        file_path: Path to the file to monitor
        module: The module to add the item to
        item_id: The ID of the item
        timeout: How long to monitor for changes in seconds
    """
    if not file_path.exists():
        return
        
    initial_mtime = file_path.stat().st_mtime
    start_time = time.time()
    
    while time.time() - start_time < timeout:
        try:
            # Check if file exists and has been modified
            if file_path.exists():
                current_mtime = file_path.stat().st_mtime
                if current_mtime > initial_mtime:
                    # File has been modified, add to order and exit
                    try:
                        # Create a CaseItem using the factory function and add it to the module order
                        from textcase.core.case_item import create_case_item
                        case_item = create_case_item(
                            prefix=module.prefix,
                            id=item_id,
                            settings=module.config.settings if hasattr(module, 'config') else {},
                            path=file_path
                        )
                        module.order.add_item(case_item)
                        return
                    except Exception as e:
                        # If we can't add to order, just return
                        print(f"Error adding to order: {e}")
                        return
        except Exception:
            # Any error, just continue monitoring
            pass
            
        # Sleep to avoid high CPU usage
        time.sleep(1)


def validate_item_id(ctx: click.Context, module: Module, name: str) -> Tuple[bool, str]:
    """
    Validate if the item ID is valid and doesn't already exist.
    
    Args:
        ctx: Click context
        module: The module to check against
        name: The name to validate
        
    Returns:
        Tuple of (is_valid, formatted_id)
    """
    # Get module settings
    settings = module.config.settings
    prefix = settings.get('prefix', '')
    sep = settings.get('sep', '')
    digits = settings.get('digits', 3)
    
    # If name is a number, format it according to module settings
    if name.isdigit():
        # Format with the specified number of digits
        formatted_id = f"{int(name):0{digits}d}"
    else:
        # Use name as is for string names
        formatted_id = name
    
    # Check if an item with this ID already exists
    full_id = f"{prefix}{sep}{formatted_id}"
    file_path = module.path / f"{full_id}.md"
    
    # Use _vfs attribute which is available in both YamlModule and _YamlProject
    if module._vfs.exists(file_path):
        click.echo(f"Error: Item with ID '{full_id}' already exists.", err=True)
        return False, ""
    
    return True, formatted_id


@click.command()
@click.option('-n', '--name', help='Specify a custom name or number for the case item')
@click.option('-q', '--quiet', is_flag=True, help='Skip opening the editor and save directly')
@click.option('-m', '--message', help='Specify content message for the case item (supports multi-line)')
@click.argument('module_prefix', type=str)
@click.pass_context
def add(ctx: click.Context, module_prefix: str, name: Optional[str] = None, quiet: bool = False, message: Optional[str] = None):
    """
    Add a new case item to a module or a new configuration.
    
    MODULE_PREFIX is the prefix of the module to add the case item to (e.g., REQ).
    
    For configurations, use the format 'template_name:name' where template_name is a
    template in the .config/template directory and name is the configuration name.
    
    Example usage:
      textcase add REQ                           # Add a new case item with auto-generated ID
      textcase add -n FOOBAR REQ                 # Add a new case item with custom string name
      textcase add -n 3 REQ                      # Add a new case item with custom numeric ID
      textcase add -m "My content" REQ           # Add a case item with specified content
      textcase add -m "Multi-line\ncontent" REQ  # Add with multi-line content
      textcase add prompt:my_prompt              # Add a new configuration using the 'prompt' template
    """
    # Get project from context
    project = ctx.obj.get('project')
    if not project:
        click.echo("Error: No valid project found.", err=True)
        ctx.exit(1)
        
    # Check if this is a configuration command (contains ':' or starts with lowercase)
    if ':' in module_prefix or (module_prefix and module_prefix[0].islower()):
        # Import the add_conf module here to avoid circular imports
        from textcase.cli.commands.add_conf import add_conf_command
        
        # Handle as a configuration command
        success = add_conf_command(ctx, module_prefix, quiet=quiet)
        ctx.exit(0 if success else 1)
    
    # Find the module with the given prefix
    module = None
    try:
        # First check if it's the root module
        if project.prefix == module_prefix:
            module = project
        else:
            # Then check submodules
            for submodule in project.get_submodules():
                if hasattr(submodule, 'prefix') and submodule.prefix == module_prefix:
                    module = submodule
                    break
    except Exception as e:
        debug_echo(ctx, f"Error finding module: {e}")
    
    if not module:
        click.echo(f"Error: Module with prefix '{module_prefix}' not found.", err=True)
        ctx.exit(1)
    
    debug_echo(ctx, f"Found module: {module.prefix} at {module.path}")
    
    # Get module settings
    settings = module.config.settings
    prefix = settings.get('prefix', '')
    sep = settings.get('sep', '')
    
    # Determine the item ID
    item_id = None
    if name:
        # Validate user-provided name
        is_valid, formatted_id = validate_item_id(ctx, module, name)
        if not is_valid:
            ctx.exit(1)
        item_id = formatted_id
    else:
        # Get next available ID from module order
        try:
            item_id = module.order.get_next_item_id(prefix)
            debug_echo(ctx, f"Generated next item ID: {item_id}")
        except Exception as e:
            click.echo(f"Error generating item ID: {e}", err=True)
            ctx.exit(1)
    
    # Create the full ID with prefix and separator
    full_id = f"{prefix}{sep}{item_id}"
    file_path = module.path / f"{full_id}.md"
    
    debug_echo(ctx, f"Creating case item at {file_path}")
    
    # Create initial content with a title and optional message
    if message:
        # Add the title with a separator and the message
        initial_content = f"# {full_id}: {message}\n\n"
        quiet = True
    else:
        # Just add the title
        initial_content = f"# {full_id}\n\n"
    
    try:
        if quiet:
            # In quiet mode, create the file directly
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(initial_content)
                was_modified = True
                
                # In quiet mode, directly add to module order
                try:
                    from textcase.core.case_item import create_case_item
                    case_item = create_case_item(
                        prefix=prefix,
                        id=item_id,
                        settings=module.config.settings if hasattr(module, 'config') else {},
                        path=file_path
                    )
                    module.order.add_item(case_item)
                    module.order._save_items()  # Force save the order
                    click.echo(f"Added case item: {full_id}")
                except Exception as e:
                    click.echo(f"Error adding item to module order: {e}", err=True)
                    if file_path.exists():
                        try:
                            module._vfs.remove(file_path)
                        except Exception:
                            pass
                    ctx.exit(1)
                    
            except Exception as e:
                click.echo(f"Error creating case item: {e}", err=True)
                ctx.exit(1)
        else:
            # Interactive mode: open the editor
            try:
                # Start a monitoring thread to watch for file changes
                monitor_thread = threading.Thread(
                    target=monitor_file_changes,
                    args=(file_path, module, full_id),
                    daemon=True
                )
                monitor_thread.start()
                
                # Open the editor
                was_modified, content = edit_with_editor(file_path, initial_content.encode('utf-8'))
                
                if was_modified and file_path.exists():
                    # File was modified and saved, add to module order
                    try:
                        from textcase.core.case_item import create_case_item
                        case_item = create_case_item(
                            prefix=prefix,
                            id=item_id,
                            settings=module.config.settings if hasattr(module, 'config') else {},
                            path=file_path
                        )
                        module.order.add_item(case_item)
                        module.order._save_items()  # Force save the order
                        click.echo(f"Added case item: {full_id}")
                    except Exception as e:
                        click.echo(f"Error adding item to module order: {e}", err=True)
                else:
                    # User canceled or didn't save, delete the file if it exists
                    if file_path.exists():
                        try:
                            module._vfs.remove(file_path)
                            click.echo(f"Canceled: Item {full_id} not created.")
                        except Exception as e:
                            click.echo(f"Error removing temporary file: {e}", err=True)
                    else:
                        click.echo(f"Canceled: Item {full_id} not created.")
                        
            except Exception as e:
                click.echo(f"Error in editor: {e}", err=True)
                if file_path.exists():
                    try:
                        module._vfs.remove(file_path)
                    except Exception:
                        pass
                ctx.exit(1)
    except Exception as e:
        click.echo(f"Error creating case item: {e}", err=True)
        # Clean up if file exists
        if file_path.exists():
            try:
                module._vfs.remove(file_path)
            except Exception:
                pass
        ctx.exit(1)
