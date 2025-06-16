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
from pathlib import Path
from typing import Optional, Tuple, Dict, Any

import click

from textcase.cli.utils import debug_echo

# Global setting to control whether to use temporary files or edit directly
USE_DIRECT_EDIT = True


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
    
    # TODO: Implement item lookup by ID or path
    # For now, just use the item_id as a path relative to the repository root
    file_path = Path(textcase.repo_root_path) / item_id
    
    if not file_path.exists():
        click.echo(f"Error: Item '{item_id}' not found.", err=True)
        ctx.exit(1)
    
    debug_echo(ctx, f"Editing item: {item_id} at {file_path}")
    
    # Ensure the parent directory exists
    file_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Check if we should use direct editing (global setting or command-line flag)
    use_direct = USE_DIRECT_EDIT
    debug_echo(ctx, f"Using direct edit mode: {use_direct}")
    
    if use_direct:
        # Edit the file directly
        debug_echo(ctx, f"Editing file directly: {file_path}")
        
        # Get file modification time before editing
        mtime_before = file_path.stat().st_mtime if file_path.exists() else 0
        
        # Open the editor directly on the file
        editor = get_editor()
        try:
            subprocess.run([editor, str(file_path)], check=True)
        except subprocess.CalledProcessError as e:
            click.echo(f"Error opening editor: {e}", err=True)
            ctx.exit(1)
        
        # Check if file was modified
        if file_path.exists():
            mtime_after = file_path.stat().st_mtime
            was_modified = mtime_before != mtime_after
            
            if was_modified:
                click.echo(f"Updated: {file_path}")
            else:
                click.echo("No changes made.")
        else:
            click.echo("File was deleted during editing.")
    else:
        # Use temporary file for editing
        temp_dir = Path(tempfile.mkdtemp(prefix='textcase_edit_'))
        
        try:
            # Get the file extension
            extension = file_path.suffix
            
            # Create a temporary file for editing with the same extension
            temp_file = temp_dir / f'temp_doc{extension}'
            
            # If document exists, read its content, otherwise create with a title
            if file_path.exists():
                debug_echo(ctx, f"Document exists, loading content from {file_path}")
                initial_content = file_path.read_bytes()
            else:
                debug_echo(ctx, f"Document does not exist, creating new file with title")
                initial_content = f"# {item_id}\n\n".encode('utf-8')
            
            # Edit the temporary file
            was_modified, content = edit_with_editor(temp_file, initial_content)
            
            if was_modified:
                # Only update the original file if changes were made
                file_path.parent.mkdir(parents=True, exist_ok=True)
                file_path.write_bytes(content)
                click.echo(f"Updated: {file_path}")
            else:
                if file_path.exists():
                    click.echo("No changes made.")
                else:
                    click.echo("No changes made, document not created.")
        except Exception as e:
            click.echo(f"Error editing document: {e}", err=True)
            raise click.Abort()
        finally:
            # Clean up temporary directory
            if temp_dir.exists():
                shutil.rmtree(temp_dir)