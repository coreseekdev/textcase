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

from textcase.cli.utils import debug_echo
from textcase.cli.commands.edit import edit_with_editor, get_editor


def monitor_file_changes(file_path: Path, module, item_id: str, timeout: int = 60) -> None:
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
                        # Create a resource item and add it to the collection
                        # TODO: Implement resource item creation
                        return
                    except Exception as e:
                        # If we can't add to collection, just return
                        print(f"Error adding to collection: {e}")
                        return
        except Exception:
            # Any error, just continue monitoring
            pass

        # Sleep to avoid high CPU usage
        time.sleep(1)

@click.command()
@click.option('-n', '--name', help='Specify a custom name or number for the resource item')
@click.option('-q', '--quiet', is_flag=True, help='Skip opening the editor and save directly')
@click.option('-m', '--message', help='Specify content message for the resource item (supports multi-line)')
@click.argument('collection_name', type=str)
@click.pass_context
def add(ctx: click.Context, collection_name: str, name: Optional[str] = None, quiet: bool = False, message: Optional[str] = None):
    """
    Add a new resource item to a collection.
    
    COLLECTION_NAME is the name of the collection to add the resource item to.
    
    Example usage:
      textcase add docs                           # Add a new resource item with auto-generated ID
      textcase add -n custom_name docs            # Add a new resource item with custom string name
      textcase add -n 3 docs                      # Add a new resource item with custom numeric ID
      textcase add -m "My content" docs           # Add a resource item with specified content
      textcase add -m "Multi-line\ncontent" docs  # Add with multi-line content
    """
    # Get TextCase instance from context
    textcase = ctx.obj.get('textcase')
    if not textcase:
        click.echo("Error: No valid TextCase instance found.", err=True)
        ctx.exit(1)
    
    # Get resource manager
    resource_manager = textcase.resource_manager
    
    # Find the collection with the given name
    collection = None
    try:
        collection = resource_manager.get_collection(collection_name)
    except Exception as e:
        debug_echo(ctx, f"Error finding collection: {e}")
    
    if not collection:
        click.echo(f"Error: Collection '{collection_name}' not found.", err=True)
        ctx.exit(1)
    
    debug_echo(ctx, f"Found collection: {collection_name} at {collection.path}")

    # Get next available ID from collection using the new interface
    # Use the collection's get_next_item_name method
    item_id = collection.get_next_item_name()
    debug_echo(ctx, f"Generated next item ID: {item_id}")
    
    # Get collection configuration
    config = collection.config
    
    # Create the full ID with prefix and separator from config
    if config.prefix:
        full_id = f"{config.prefix}{config.sep}{item_id}"
    else:
        full_id = item_id
    
    # Use suffix from config or default to .md
    extension = config.suffix if config.suffix else ".md"
    file_path = Path(collection.path) / f"{full_id}{extension}"
    
    debug_echo(ctx, f"Creating resource item at {file_path}")
    
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
                
                # In quiet mode, directly add to collection
                try:
                    # TODO: Implement resource item creation and addition to collection
                    click.echo(f"Added resource item: {full_id}")
                except Exception as e:
                    click.echo(f"Error adding item to collection: {e}", err=True)
                    if file_path.exists():
                        try:
                            os.remove(file_path)
                        except Exception:
                            pass
                    ctx.exit(1)
                    
            except Exception as e:
                click.echo(f"Error creating resource item: {e}", err=True)
                ctx.exit(1)
        else:
            # Interactive mode: open the editor
            try:
                # Start a monitoring thread to watch for file changes
                monitor_thread = threading.Thread(
                    target=monitor_file_changes,
                    args=(file_path, collection, full_id),
                    daemon=True
                )
                monitor_thread.start()
                
                # Open the editor
                was_modified, content = edit_with_editor(file_path, initial_content.encode('utf-8'))
                
                if was_modified and file_path.exists():
                    # File was modified and saved, add to collection
                    try:
                        # TODO: Implement resource item creation and addition to collection
                        click.echo(f"Added resource item: {full_id}")
                    except Exception as e:
                        click.echo(f"Error adding item to collection: {e}", err=True)
                else:
                    # User canceled or didn't save, delete the file if it exists
                    if file_path.exists():
                        try:
                            os.remove(file_path)
                            click.echo(f"Canceled: Item {full_id} not created.")
                        except Exception as e:
                            click.echo(f"Error removing temporary file: {e}", err=True)
                    else:
                        click.echo(f"Canceled: Item {full_id} not created.")
                        
            except Exception as e:
                click.echo(f"Error in editor: {e}", err=True)
                if file_path.exists():
                    try:
                        os.remove(file_path)
                    except Exception:
                        pass
                ctx.exit(1)
    except Exception as e:
        click.echo(f"Error creating resource item: {e}", err=True)
        # Clean up if file exists
        if file_path.exists():
            try:
                os.remove(file_path)
            except Exception:
                pass
        ctx.exit(1)