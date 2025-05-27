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
"""Link command implementation."""

from pathlib import Path
import click

from ...core.case_item import create_case_item
from ...cli.utils import debug_echo
from ...protocol.module import Module


def get_document_path(doc_id: str, project, ctx) -> tuple[Path, Module, str]:
    """Get the document path from a document ID.
    
    Args:
        doc_id: The document ID in the format PREFIX[ID]
        project: The project to search in
        ctx: Click context for debug output
        
    Returns:
        A tuple of (document_path, module, formatted_id) or (None, None, None) if not found
    """
    # Try to parse the document ID to get prefix and ID parts
    prefix = None
    item_id = None
    
    # Extract prefix and ID (e.g., REQ001 -> prefix=REQ, id=001)
    import re
    match = re.match(r'^([A-Za-z]+)(\d+)$', doc_id)
    if match:
        prefix = match.group(1).upper()
        item_id = match.group(2)
    else:
        debug_echo(ctx, f"Could not parse document ID: {doc_id}")
        return None, None, None
    
    debug_echo(ctx, f"Parsed document ID: prefix={prefix}, id={item_id}")
    
    # Find the module with this prefix
    module = None
    
    # First try the project's own prefix
    if prefix == project.prefix:
        module = project
    else:
        # Check all submodules
        submodules = project.get_submodules()
        debug_echo(ctx, f"Available submodules: {[m.prefix for m in submodules]}")
        
        for submodule in submodules:
            if submodule.prefix == prefix:
                module = submodule
                break
    
    if not module:
        debug_echo(ctx, f"No module found for prefix: {prefix}")
        return None, None, None
    
    debug_echo(ctx, f"Found module: {module.prefix} at {module.path}")
    
    # Create a case item to get the formatted ID and path
    case_item = module.get_document_item(item_id)
    formatted_id = case_item.key
    
    # Get the document path
    doc_path = module.path / f"{formatted_id}.md"
    debug_echo(ctx, f"Document path: {doc_path}")
    
    return doc_path, module, formatted_id


@click.command()
@click.argument('source')
@click.argument('target')
@click.option('-l', '--label', default='', help='Optional label for the link')
@click.option('-v', '--verbose', is_flag=True, help='Enable verbose output')
@click.pass_context
def link(ctx: click.Context, source: str, target: str, label: str, verbose: bool):
    """Link two documents.
    
    Creates a link from the SOURCE document to the TARGET document.
    Both SOURCE and TARGET should be document IDs in the format PREFIX[ID].
    
    Examples:
      textcase link TST1 REQ1                # Link TST001 to REQ001 with no label
      textcase link TST1 REQ1 -l "related"   # Link with a specific label
      textcase link TST001 REQ001             # Link using full IDs
    """
    # Set verbose mode in context if not already set
    if verbose and 'verbose' not in ctx.obj:
        ctx.obj['verbose'] = verbose
    
    # Get the project from context (ensured by the CLI)
    project = ctx.obj['project']
    if not project:
        click.echo("Error: No valid project found.", err=True)
        ctx.exit(1)
    
    # Get the source document path and module
    source_path, source_module, source_formatted_id = get_document_path(source, project, ctx)
    if not source_path or not source_module:
        click.echo(f"Error: Could not find source document '{source}'.", err=True)
        ctx.exit(1)
    
    # Check if the source document exists
    if not source_path.exists():
        click.echo(f"Error: Source document '{source_formatted_id}' does not exist.", err=True)
        ctx.exit(1)
    
    # Get the target document path and module
    target_path, target_module, target_formatted_id = get_document_path(target, project, ctx)
    if not target_path or not target_module:
        click.echo(f"Error: Could not find target document '{target}'.", err=True)
        ctx.exit(1)
    
    # Check if the target document exists
    if not target_path.exists():
        click.echo(f"Error: Target document '{target_formatted_id}' does not exist.", err=True)
        ctx.exit(1)
    
    # Get case items from the modules
    source_id = source_formatted_id.split(source_module.prefix)[-1].lstrip('-')
    target_id = target_formatted_id.split(target_module.prefix)[-1].lstrip('-')
    
    source_item = source_module.get_document_item(source_id)
    target_item = target_module.get_document_item(target_id)
    
    # Set the paths explicitly if needed
    if hasattr(source_item, 'path') and source_item.path is None:
        source_item.path = source_path
    
    if hasattr(target_item, 'path') and target_item.path is None:
        target_item.path = target_path
    
    # Create the link
    try:
        source_item.make_link(target_item, label)
        link_info = f"{source_formatted_id} -> {target_formatted_id}"
        if label:
            link_info += f' ("{label}")'
        click.echo(f"Linked: {link_info} ({source_path.parent} -> {target_path.parent})")
    except Exception as e:
        click.echo(f"Error creating link: {e}", err=True)
        ctx.exit(1)
