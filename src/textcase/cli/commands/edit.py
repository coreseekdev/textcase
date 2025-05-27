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

from textcase.protocol.module import Module
from textcase.core.module_item import CaseItemBase
from textcase.cli.utils import debug_echo

# Global setting to control whether to use temporary files or edit directly
USE_DIRECT_EDIT = True


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


def parse_document_id(doc_id: str, project, ctx) -> Tuple[Optional[Module], Optional[str], Optional[str]]:
    """Parse a document ID into module and item ID components.
    
    Args:
        doc_id: The document ID to parse (e.g., 'REQ1', 'REQ001', 'TST002', 'REQtest')
        project: The project to search for modules
        
    Returns:
        Tuple of (module, prefix, item_id) or (None, None, None) if not found
    """
    if not doc_id:
        return None, None, None
        
    debug_echo(ctx, f"Parsing document ID: {doc_id}")
    
    # First, try to find an exact file match with any module prefix
    modules = [project] + project.get_submodules()
    
    for module in modules:
        if not hasattr(module, 'prefix') or not module.prefix:
            continue
            
        debug_echo(ctx, f"Checking module with prefix: {module.prefix}")
        
        # Check if the document ID starts with this module's prefix
        if doc_id.upper().startswith(module.prefix):
            prefix = module.prefix
            # Extract the ID part (everything after the prefix)
            raw_id = doc_id[len(prefix):]
            
            # Check if the file exists
            file_path = module.path / f"{doc_id}.md"
            debug_echo(ctx, f"Checking if file exists: {file_path}")
            
            if module._vfs.exists(file_path):
                debug_echo(ctx, f"Found existing file: {file_path}")
                return module, prefix, raw_id
            
            # If file doesn't exist, this might be a new document
            # Check if the prefix is valid for this module
            if module.prefix == prefix:
                debug_echo(ctx, f"Valid prefix for module: {module.prefix}, raw_id: {raw_id}")
                return module, prefix, raw_id
    
    # If we get here, try to parse as a standard format (prefix + number)
    debug_echo(ctx, "No direct match found, trying standard format")
    match = re.match(r'^([A-Za-z]+)([0-9]+|[A-Za-z0-9_-]*)$', doc_id)
    if match:
        prefix = match.group(1).upper()
        raw_id = match.group(2) or ''
        
        debug_echo(ctx, f"Matched standard format - prefix: {prefix}, raw_id: {raw_id}")
        
        # Find the module with this prefix
        target_module = None
        
        if project.prefix == prefix:
            target_module = project
        else:
            for submodule in project.get_submodules():
                if hasattr(submodule, 'prefix') and submodule.prefix == prefix:
                    target_module = submodule
                    break
        
        if target_module:
            debug_echo(ctx, f"Found module for prefix {prefix}")
            return target_module, prefix, raw_id
    
    debug_echo(ctx, f"Could not parse document ID: {doc_id}")
    return None, None, None


def format_item_id(module: Module, raw_id: str) -> str:
    """Format an item ID according to module settings.
    
    Args:
        module: The module containing the settings
        raw_id: The raw ID to format
        
    Returns:
        The formatted ID
    """
    # Get module settings
    settings = module.config.settings
    digits = settings.get('digits', 3)  # Default to 3 digits
    sep = settings.get('sep', '')  # Default to no separator
    
    # Format numeric IDs with leading zeros based on digits setting
    if raw_id.isdigit():
        formatted_id = f"{int(raw_id):0{digits}d}"
    else:
        formatted_id = raw_id
        
    # Return the full ID with prefix and separator
    return f"{module.prefix}{sep}{formatted_id}"


def get_document_path(doc_id: str, project, ctx) -> Tuple[Optional[Path], Optional[Module], Optional[str]]:
    """Convert doc_id to a file path.
    
    Args:
        doc_id: The document ID to parse (e.g., 'REQ1', 'REQ001')
        project: The project to search for modules
        
    Returns:
        Tuple of (file_path, module, formatted_id) or (None, None, None) if not found
    """
    debug_echo(ctx, f"Getting document path for: {doc_id}")
    
    # First try to parse as a document ID
    module, prefix, raw_id = parse_document_id(doc_id, project, ctx)
    
    if not module or not prefix:
        debug_echo(ctx, f"Could not determine module for document ID: {doc_id}")
        return None, None, None
    
    debug_echo(ctx, f"Found module: {module.prefix}, raw_id: {raw_id}")
    
    # If raw_id is empty, use the doc_id as is (for cases like REQtest)
    if not raw_id and doc_id.startswith(prefix):
        formatted_id = doc_id
    else:
        # Format the ID according to module settings
        formatted_id = format_item_id(module, raw_id)
    
    # Create the file path
    file_path = module.path / f"{formatted_id}.md"
    debug_echo(ctx, f"Resolved file path: {file_path}")
    
    return file_path, module, formatted_id


@click.command()
@click.argument('doc_id')
# @click.option('--direct', '-d', is_flag=True, help='Edit the file directly without using a temporary file')
@click.pass_context
def edit(ctx: click.Context, doc_id: str):
    """
    Edit a document or configuration using the system editor.
    
    For documents, the document will be created if it doesn't exist, but only if changes are made.
    
    For configurations, use the format 'template_name:name' where template_name is a
    template in the .config/template directory and name is the configuration name.
    
    Requires an existing project. The project must be initialized with a .textcase.yml file.
    
    Examples:
      textcase edit REQ1                # Edit REQ001.md (with leading zeros based on module settings)
      textcase edit REQ001              # Edit REQ001.md directly
      textcase edit TST42               # Edit TST042.md in the TST module
      textcase edit prompt:my_prompt    # Edit the 'my_prompt' configuration using the 'prompt' template
    """
    # Get the project from context (ensured by the CLI)
    project = ctx.obj['project']
    if not project:
        click.echo("Error: No valid project found.", err=True)
        ctx.exit(1)
        
    # Check if this is a configuration command (contains ':' or starts with lowercase)
    if ':' in doc_id or (doc_id and doc_id[0].islower()):
        # Import the edit_conf module here to avoid circular imports
        from textcase.cli.commands.edit_conf import edit_conf_command
        
        # Handle as a configuration command
        success = edit_conf_command(ctx, doc_id)
        ctx.exit(0 if success else 1)
    
    # Parse the document ID and get the file path
    doc_path, module, formatted_id = get_document_path(doc_id, project, ctx)
    if not doc_path or not module:
        click.echo(f"Error: Could not parse document ID '{doc_id}'. Format should be PREFIX followed by ID (e.g., REQ1, TST002).", err=True)
        ctx.exit(1)
    
    debug_echo(ctx, f"Editing document: {formatted_id} in module {module.prefix} at {doc_path}")
    
    # Ensure the parent directory exists
    doc_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Check if we should use direct editing (global setting or command-line flag)
    use_direct = USE_DIRECT_EDIT
    debug_echo(ctx, f"Using direct edit mode: {use_direct}")
    
    if use_direct:
        # Edit the file directly
        debug_echo(ctx, f"Editing file directly: {doc_path}")
        
        # If the file doesn't exist, show an error
        if not doc_path.exists():
            click.echo(f"Error: Document '{formatted_id}' does not exist in module {module.prefix}", err=True)
            ctx.exit(1)
        
        # Get file modification time before editing
        mtime_before = doc_path.stat().st_mtime if doc_path.exists() else 0
        
        # Open the editor directly on the file
        editor = get_editor()
        try:
            subprocess.run([editor, str(doc_path)], check=True)
        except subprocess.CalledProcessError as e:
            click.echo(f"Error opening editor: {e}", err=True)
            ctx.exit(1)
        
        # Check if file was modified
        if doc_path.exists():
            mtime_after = doc_path.stat().st_mtime
            was_modified = mtime_before != mtime_after
            
            if was_modified:
                click.echo(f"Updated: {doc_path}")
                
                # If this was a new file, add it to the module order
                if mtime_before == 0:
                    click.echo(f"Created new document: {doc_path}")
                    try_add_to_module_order(ctx, module, formatted_id, doc_path)
            else:
                click.echo("No changes made.")
        else:
            click.echo("File was deleted during editing.")
    else:
        # Use temporary file for editing
        temp_dir = Path(tempfile.mkdtemp(prefix='textcase_edit_'))
        
        try:
            # Create a temporary file for editing
            temp_file = temp_dir / 'temp_doc.md'
            
            # If document exists, read its content, otherwise create with a title
            if doc_path.exists():
                debug_echo(ctx, f"Document exists, loading content from {doc_path}")
                initial_content = doc_path.read_bytes()
            else:
                debug_echo(ctx, f"Document does not exist, creating new file with title")
                initial_content = f"# {formatted_id}\n\n".encode('utf-8')
            
            # Edit the temporary file
            was_modified, content = edit_with_editor(temp_file, initial_content)
            
            if was_modified:
                # Only update the original file if changes were made
                doc_path.parent.mkdir(parents=True, exist_ok=True)
                doc_path.write_bytes(content)
                click.echo(f"Updated: {doc_path}")
                
                # If this was a new file, add it to the module order
                if not doc_path.exists() or doc_path.stat().st_size == 0:
                    click.echo(f"Created new document: {doc_path}")
                    try_add_to_module_order(ctx, module, formatted_id, doc_path)
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


def try_add_to_module_order(ctx, module, formatted_id, doc_path):
    """Try to add a document to the module's order.
    
    Args:
        ctx: Click context
        module: Module to add the document to
        formatted_id: Formatted ID of the document
        doc_path: Path to the document
    """
    try:
        if hasattr(module, 'order') and hasattr(module.order, 'add_item'):
            # Extract the raw ID from the formatted ID
            item_id = formatted_id.split(module.prefix)[-1]
            if item_id.startswith(module.config.settings.get('sep', '')):
                item_id = item_id[len(module.config.settings.get('sep', '')):]  
                
            # Create a CaseItem using the factory function and add it to the order
            from textcase.core.case_item import create_case_item
            case_item = create_case_item(
                prefix=module.prefix,
                id=item_id,
                settings=module.config.settings if hasattr(module, 'config') else {},
                path=doc_path
            )
            module.order.add_item(case_item)
            debug_echo(ctx, f"Added {formatted_id} to module order")
    except Exception as e:
        click.echo(f"Warning: Could not add document to module order: {e}", err=True)
