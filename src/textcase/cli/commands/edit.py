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
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Optional, Tuple

import click


def get_editor() -> str:
    """Get the editor from environment variables or use a default."""
    return os.environ.get('EDITOR', 'vi')  # Default to vi if no editor is set


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


def get_document_path(doc_id: str, base_dir: Path) -> Path:
    """Convert doc_id to a file path."""
    # TODO: Implement proper doc_id to path conversion based on your project's structure
    # This is a simple implementation that treats doc_id as a filename
    return base_dir / f"{doc_id}.md"


@click.command()
@click.argument('doc_id')
@click.pass_context
def edit(ctx: click.Context, doc_id: str):
    """
    Edit a document using the system editor.
    
    The document will be created if it doesn't exist, but only if changes are made.
    """
    # Get the base directory from context or use current directory
    base_dir = Path.cwd()
    if ctx.obj and 'project' in ctx.obj:
        base_dir = ctx.obj['project'].path
    
    doc_path = get_document_path(doc_id, base_dir)
    temp_dir = Path(tempfile.mkdtemp(prefix='textcase_edit_'))
    
    try:
        # Create a temporary file for editing
        temp_file = temp_dir / 'temp_doc.md'
        
        # If document exists, read its content, otherwise start with empty content
        initial_content = doc_path.read_bytes() if doc_path.exists() else b''
        
        # Edit the temporary file
        was_modified, content = edit_with_editor(temp_file, initial_content)
        
        if was_modified:
            # Only update the original file if changes were made
            doc_path.parent.mkdir(parents=True, exist_ok=True)
            doc_path.write_bytes(content)
            click.echo(f"Updated: {doc_path}")
            
            # If this was a new file, print a message
            if not doc_path.exists():
                click.echo(f"Created new document: {doc_path}")
        else:
            if doc_path.exists():
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
