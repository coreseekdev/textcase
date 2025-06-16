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

import subprocess
import click
from pathlib import Path, PurePosixPath
from typing import Optional, Tuple, Dict, Any

from textcase.proto.resource_collection_protocol import ResourceCollection, ResourceItem
from textcase.cli.utils import debug_echo
from textcase.cli.commands.edit import edit_with_editor, get_editor


def get_vfs_local_path(collection: 'ResourceCollection[T]', vfs_path: PurePosixPath) -> Path:
    """Convert a VFS path to a local file system path.
    
    Args:
        collection: The resource collection
        vfs_path: VFS path to convert
        
    Returns:
        Local file system path
        
    Raises:
        RuntimeError: If the path cannot be converted
    """
    try:
        # Use the new to_local_path method from VFS client
        local_path = collection._vfs.to_local_path(vfs_path)
        if local_path:
            return local_path
        else:
            # Fallback: construct path manually if VFS doesn't support conversion
            # This is a simple fallback that may not work in all cases
            raise RuntimeError(f"Cannot convert VFS path {vfs_path} to local path")
    except Exception as e:
        raise RuntimeError(f"Failed to convert VFS path {vfs_path} to local path: {e}")

@click.command()
@click.option('-n', '--name', help='Specify a custom name or number for the resource item')
@click.option('-q', '--quiet', is_flag=True, help='Skip opening the editor and save directly')
@click.option('-m', '--message', multiple=True, help='Specify content message for the resource item (can be used multiple times)')
@click.argument('collection_name', type=str)
@click.pass_context
def add(ctx: click.Context, collection_name: str, name: Optional[str] = None, quiet: bool = False, message: tuple = ()):
    """
    Add a new resource item to a collection.
    
    COLLECTION_NAME is the name of the collection to add the resource item to.
    
    Example usage:
      textcase add docs                           # Add a new resource item with auto-generated ID
      textcase add -n custom_name docs            # Add a new resource item with custom string name
      textcase add -n 3 docs                      # Add a new resource item with custom numeric ID
      textcase add -m "My content" docs           # Add a resource item with specified content
      textcase add -m "Line 1" -m "Line 2" docs   # Add with multiple messages joined by newlines
      textcase add -m "Multi-line\ncontent" docs  # Add with multi-line content
    """
    # Get TextCase instance from context
    textcase = ctx.obj.get('textcase')
    if not textcase:
        click.echo("Error: No valid TextCase instance found.", err=True)
        ctx.exit(1)
    
    # Get resource manager
    resource_manager = textcase.resource_manager
    
    # 使用 parse_resource_reference 查找集合
    collection = None
    item = None
    
    # 尝试解析引用，可能是集合名称或前缀
    try:
        collection, item = resource_manager.parse_resource_reference(collection_name, partial=False)
    except Exception as e:
        debug_echo(ctx, f"Error parsing resource reference: {e}")
    
    if not collection:
        click.echo(f"Error: Collection '{collection_name}' not found.", err=True)
        ctx.exit(1)
        
    # 如果找到了项目，这意味着用户可能误用了完整的项目引用而不是集合名称
    if item:
        click.echo(f"Warning: '{collection_name}' appears to be an item reference, not a collection name.")
        click.echo(f"Using collection '{collection.name}' instead.")
        # 继续使用找到的集合，但不使用找到的项目
    
    debug_echo(ctx, f"Found collection: {collection_name} at {collection.path}")

    # Get next available ID from collection using the new interface
    # Use the collection's get_next_item_name method
    if name:
        item_id = name
        # check exist
        if collection.has_item(item_id):
            click.echo(f"Error: Item '{item_id}' already exists.", err=True)
            ctx.exit(1)
    else:
        item_id = collection.get_next_item_name()
    debug_echo(ctx, f"Generated next item ID: {item_id}")
    
    item_key = collection.get_item_key(item_id)

    # Create initial content with a title and optional message
    if message:
        # Join multiple messages with newlines
        combined_message = '\n'.join(message)
        # Add the title with a separator and the message
        initial_content = f"# {item_key}: {combined_message}\n\n"
        quiet = True
    else:
        # Just add the title
        initial_content = f"# {item_key}\n\n"
        
    try:
        if quiet:
            # In quiet mode, create the item directly using collection.add_item
            try:
                item = collection.add_item(item_id)
                item.write_content(initial_content)
                click.echo(f"Added resource item: {item_id}")
            except Exception as e:
                click.echo(f"Error creating resource item: {e}", err=True)
                ctx.exit(1)
        else:
            # Interactive mode: create item, write initial content, open editor, check for modifications
            try:
                # 1. Create item using collection.add_item
                item: 'ResourceItem[T]' = collection.add_item(item_id, initial_content)
                # item.write_content(initial_content)
                
                # 2. Get file modification time via VFS info
                file_path_vfs = item.get_file_path()
                file_info_before = collection._vfs.info(file_path_vfs)
                mtime_before = file_info_before.get('modified') if file_info_before else 0

                # 3. Convert VFS path to local path for editor
                local_file_path = get_vfs_local_path(collection, file_path_vfs)
                
                debug_echo(ctx, f"Opening editor for: {local_file_path}")
                
                # 4. Open file with git's editor
                editor = get_editor()
                subprocess.run([editor, str(local_file_path)], check=True)
                
                # 5. Check if file was modified
                file_info_after = collection._vfs.info(file_path_vfs)
                mtime_after = file_info_after.get('modified') if file_info_after else 0
                
                if mtime_after > mtime_before:
                    # File was modified, keep the item
                    click.echo(f"Added resource item: {item_key}")
                else:
                    # File was not modified, remove the item
                    collection.remove_item(item_id)
                    click.echo(f"Canceled: Item {item_key} not created (no changes made).")
                        
            except Exception as e:
                click.echo(f"Error in editor: {e}", err=True)
                # Try to clean up the item if it was created
                try:
                    collection.remove_item(item_id)
                except Exception:
                    pass
                ctx.exit(1)
    except Exception as e:
        click.echo(f"Error creating resource item: {e}", err=True)
        ctx.exit(1)