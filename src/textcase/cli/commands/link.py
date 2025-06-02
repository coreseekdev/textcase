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
from typing import Optional
import click

from ...core.case_item import create_case_item
from ...cli.utils import debug_echo, get_document_path, get_document_item
from ...protocol.module import Module


@click.command()
@click.argument('source')
@click.argument('target')
@click.option('-l', '--label', default='', help='Optional label for the link')
@click.option('-v', '--verbose', is_flag=True, help='Enable verbose output')
@click.pass_context
def link(ctx: click.Context, source: str, target: str, label: str, verbose: bool):
    """Link two documents.
    
    Creates a link from the SOURCE document to the TARGET document.
    
    SOURCE format: PREFIX[ID][:region]
    TARGET format: PREFIX[ID]
    
    The optional region specifier determines where the link is created:
      - meta, frontmatter: Link in the document's frontmatter (default)
      - body, content: Link in the document's content
    
    Examples:
      textcase link TST1 REQ1                # Link TST001 to REQ001 with no label (in frontmatter)
      textcase link TST1:meta REQ1           # Explicitly link in frontmatter
      textcase link TST1:content REQ1        # Link in document content
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
    
    """
    # Get the source document path, module, and region
    source_path, source_module, source_formatted_id, source_region = get_document_path(source, project, ctx)
    if not source_path or not source_module:
        click.echo(f"Error: Could not find source document '{source}'.", err=True)
        ctx.exit(1)
    
    # Check if the source document exists
    if not source_path.exists():
        click.echo(f"Error: Source document '{source_formatted_id}' does not exist.", err=True)
        ctx.exit(1)
    
    # Get the target document path and module
    target_path, target_module, target_formatted_id, _ = get_document_path(target, project, ctx)
    if not target_path or not target_module:
        click.echo(f"Error: Could not find target document '{target}'.", err=True)
        ctx.exit(1)
    
    # Check if the target document exists
    if not target_path.exists():
        click.echo(f"Error: Target document '{target_formatted_id}' does not exist.", err=True)
        ctx.exit(1)
    """
    # Get case items from the modules
    source_item, source_region = get_document_item(source, project, ctx)
    target_item, _ = get_document_item(target, project, ctx)
    
    if not source_item or not target_item:
        click.echo(f"Error: Could not get document items.", err=True)
        ctx.exit(1)
    
    # Create the link
    try:
        source_item.make_link(target_item, label, source_region)
        link_info = f"{source_item.key} -> {target_item.key}"
        if label:
            link_info += f' ("{label}")'
        if source_region:
            link_info += f" [region: {source_region}]"
        click.echo(f"Linked: {link_info} ({source_item.path} -> {target_item.path.parent})")

    except NotImplementedError as e:
        click.echo(f"Error creating link: {e}", err=True)
        ctx.exit(1)
