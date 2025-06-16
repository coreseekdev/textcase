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
"""Edit command implementation."""

import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path, PurePosixPath
from typing import Optional, Tuple, Dict, Any, TypeVar

import click

from textcase.proto.resource_collection_protocol import ResourceCollection, ResourceItem
from textcase.cli.utils import debug_echo

T = TypeVar('T')

# Global setting to control whether to use temporary files or edit directly
USE_DIRECT_EDIT = True


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
        # Use the to_local_path method from VFS client
        local_path = collection._vfs.to_local_path(vfs_path)
        if local_path:
            return local_path
        else:
            # Fallback: construct path manually if VFS doesn't support conversion
            raise RuntimeError(f"Cannot convert VFS path {vfs_path} to local path")
    except Exception as e:
        raise RuntimeError(f"Failed to convert VFS path {vfs_path} to local path: {e}")


def get_editor() -> str:
    """Get the editor from environment variables or use a default.
    
    Priority order:
    1. EDITOR environment variable
    2. Git's core.editor configuration
    3. Default to notepad on Windows
    """
    # First check EDITOR environment variable
    editor = os.environ.get('EDITOR')
    if editor:
        return editor
    
    # Try to get git's default editor
    try:
        import subprocess
        result = subprocess.run(['git', 'config', '--global', 'core.editor'], 
                              capture_output=True, text=True, timeout=5)
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
    except (subprocess.TimeoutExpired, subprocess.CalledProcessError, FileNotFoundError):
        pass
    
    # Default to notepad on Windows
    return 'notepad'


def edit_with_editor(file_path: Path, initial_content: bytes = b'') -> Tuple[bool, bytes]:
    """
    Edit a file using the system editor.
    
    Args:
        file_path: Path to the file to edit
        initial_content: Initial content for the file if it doesn't exist
        
    Returns:
        Tuple[bool, bytes]: (was_modified, content) - whether the file was modified and its content
    """
    editor = get_editor()
    file_path = file_path.absolute()
    
    # Create parent directories if they don't exist
    file_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Write initial content if file doesn't exist
    if not file_path.exists() and initial_content:
        file_path.write_bytes(initial_content)
    
    # Get file modification time before editing
    mtime_before = file_path.stat().st_mtime if file_path.exists() else 0
    
    # Open the editor
    try:
        subprocess.run([editor, str(file_path)], check=True)
    except subprocess.CalledProcessError as e:
        click.echo(f"Error opening editor: {e}", err=True)
        return False, b''
    
    # Check if file still exists
    if not file_path.exists():
        return False, b''
        
    # Read the modified content
    mtime_after = file_path.stat().st_mtime
    content = file_path.read_bytes()
    
    # Check if file was modified
    was_modified = mtime_before != mtime_after
    
    return was_modified, content


@click.command()
@click.argument('item_id')
@click.pass_context
def edit(ctx: click.Context, item_id: str):
    """
    Edit a resource item using the system editor.
    
    ITEM_ID is the ID of the resource item to edit.
    
    Examples:
      textcase edit docs/file1.md       # Edit a specific file in the docs collection
      textcase edit ITEM-001            # Edit an item by its ID
    """
    # Get TextCase instance from context
    textcase = ctx.obj.get('textcase')
    if not textcase:
        click.echo("Error: No valid TextCase instance found.", err=True)
        ctx.exit(1)
    
    # Get resource manager
    resource_manager = textcase.resource_manager
    
    # Try to find the item by ID or path
    file_path = None
    collection = None
    item = None
    
    # 首先尝试使用 parse_resource_reference 函数解析引用
    # 在编辑模式下，我们不希望进行部分匹配，因此设置 partial=False
    collection, item = resource_manager.parse_resource_reference(item_id, partial=False)

    if collection and item:
        # 成功找到集合和项目
        vfs_path = item.get_file_path()
        try:
            # 将 VFS 路径转换为本地文件路径
            file_path = get_vfs_local_path(collection, vfs_path)
            debug_echo(ctx, f"Found item {item.name} in collection {collection.name} at {file_path}")
        except RuntimeError as e:
            click.echo(f"Error: {e}", err=True)
            ctx.exit(1)
    elif collection and not item:
        # 只找到集合但没有找到项目，视为匹配失败
        click.echo(f"Error: No specific item found for reference '{item_id}'. Please provide a complete item reference.", err=True)
        ctx.exit(1)
    else:
        # 没有找到集合和项目，视为匹配失败
        click.echo(f"Error: No collection/item match found for reference '{item_id}'. Please provide a complete item reference.", err=True)
        ctx.exit(1)
    
    debug_echo(ctx, f"Editing item: {item_id} at {file_path}")
    
    # Check if we should use direct editing (global setting or command-line flag)
    use_direct = USE_DIRECT_EDIT
    debug_echo(ctx, f"Using direct edit mode: {use_direct}")
    
    if use_direct:
        # Edit the file directly
        debug_echo(ctx, f"Editing file directly: {file_path}")
        
        if collection and item:
            # 使用 VFS 访问文件
            vfs_path = item.get_file_path()
            
            # 获取文件修改时间
            file_info_before = collection._vfs.info(vfs_path)
            mtime_before = file_info_before.get('modified') if file_info_before else 0
            
            # 打开编辑器
            editor = get_editor()
            try:
                subprocess.run([editor, str(file_path)], check=True)
            except subprocess.CalledProcessError as e:
                click.echo(f"Error opening editor: {e}", err=True)
                ctx.exit(1)
            
            # 检查文件是否被修改
            file_info_after = collection._vfs.info(vfs_path)
            if not file_info_after:
                click.echo("File was deleted during editing.")
            else:
                mtime_after = file_info_after.get('modified')
                was_modified = mtime_before != mtime_after
                
                if was_modified:
                    click.echo(f"Updated: {file_path}")
                else:
                    click.echo("No changes made.")
    else:
        # Use temporary file for editing
        raise NotImplementedError