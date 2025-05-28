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
"""Tag command implementation."""

import click
from typing import Optional

from ...cli.utils import debug_echo
from ...protocol.module import Module
from ...core.case_item import create_case_item
from ..commands.link import get_document_path


@click.group()
@click.pass_context
def tag(ctx: click.Context):
    """
    Manage tags for case items.
    
    This command allows you to add, remove, or list tags for case items.
    """
    pass


@tag.command('add')
@click.argument('doc_id')
@click.argument('tags', nargs=-1, required=True)
@click.option('-v', '--verbose', is_flag=True, help='Enable verbose output')
@click.option('-f', '--force', is_flag=True, help='Force adding tags even if they are not defined')
@click.option('-g', '--global', 'is_global', is_flag=True, help='Add tags to the project globally instead of the module')
@click.pass_context
def add_tag(ctx: click.Context, doc_id: str, tags: tuple, verbose: bool, force: bool = False, is_global: bool = False):
    """
    Add tags to a case item.
    
    DOC_ID is the document ID in the format PREFIX[ID] (e.g., REQ001).
    TAGS are one or more tags to add to the case item.
    
    By default, tags must be defined in the project or module configuration.
    Use --force to automatically create undefined tags at the module level.
    Use --global to add or create tags at the project level instead of the module level.
    
    Examples:
      textcase tag add REQ001 important                      # Add a defined tag to module
      textcase tag add REQ001 important documentation        # Add multiple tags to module
      textcase tag add --force REQ001 new-tag                # Auto-create tag in module
      textcase tag add --global REQ001 important             # Add tag at project level
      textcase tag add --force --global REQ001 new-tag       # Auto-create tag at project level
    """
    # Get project from context
    project = ctx.obj.get('project')
    if not project:
        click.echo("Error: No valid project found.", err=True)
        ctx.exit(1)
    
    # Get document path and module
    doc_path, module, formatted_id = get_document_path(doc_id, project, ctx)
    if not doc_path or not module:
        click.echo(f"Error: Document '{doc_id}' not found.", err=True)
        ctx.exit(1)
    
    if verbose:
        click.echo(f"Adding tags to {formatted_id}: {', '.join(tags)}")
    
    # Get the case item
    case_item = module.get_document_item(formatted_id)
    
    # Add each tag
    success = True
    for tag in tags:
        try:
            # Determine where to check for and add tags
            tag_container = project if is_global else module
            tag_level = "project" if is_global else "module"
            
            # Check if the tag exists in the configuration
            if hasattr(tag_container, 'config') and hasattr(tag_container.config, 'tags'):
                all_tags = tag_container.config.tags
            else:
                all_tags = {}
                
            # Check if tag exists
            if tag not in all_tags:
                if force:
                    # Auto-create the tag if force is enabled
                    if is_global:
                        project.config.tags[tag] = f"Auto-created tag: {tag}"
                    else:
                        # Ensure module has tags configuration
                        if not hasattr(module, 'config') or not hasattr(module.config, 'tags'):
                            module.config.tags = {}
                        module.config.tags[tag] = f"Auto-created tag: {tag}"
                        
                    if verbose:
                        click.echo(f"Created new tag '{tag}' at {tag_level} level")
                else:
                    # Error if tag doesn't exist and force is not enabled
                    raise ValueError(f"Tag '{tag}' is not defined at {tag_level} level. Use --force to auto-create it.")
            
            # Add the tag to the case item
            module.tags.add_tag(case_item, tag)
            if verbose:
                click.echo(f"Added tag '{tag}' to {formatted_id}")
                
            # Save the configuration if we created a new tag
            if force and tag not in all_tags:
                tag_container.save()
        except Exception as e:
            click.echo(f"Error adding tag '{tag}': {e}", err=True)
            success = False
    
    # Save changes
    if success:
        module.save()
        click.echo(f"Successfully added tags to {formatted_id}")
    else:
        click.echo("Some tags could not be added", err=True)
        ctx.exit(1)


@tag.command('remove')
@click.argument('doc_id')
@click.argument('tags', nargs=-1, required=True)
@click.option('-v', '--verbose', is_flag=True, help='Enable verbose output')
@click.pass_context
def remove_tag(ctx: click.Context, doc_id: str, tags: tuple, verbose: bool):
    """
    Remove tags from a case item.
    
    DOC_ID is the document ID in the format PREFIX[ID] (e.g., REQ001).
    TAGS are one or more tags to remove from the case item.
    
    Examples:
      textcase tag remove REQ001 important
      textcase tag remove REQ001 important documentation
    """
    # Get project from context
    project = ctx.obj.get('project')
    if not project:
        click.echo("Error: No valid project found.", err=True)
        ctx.exit(1)
    
    # Get document path and module
    doc_path, module, formatted_id = get_document_path(doc_id, project, ctx)
    if not doc_path or not module:
        click.echo(f"Error: Document '{doc_id}' not found.", err=True)
        ctx.exit(1)
    
    if verbose:
        click.echo(f"Removing tags from {formatted_id}: {', '.join(tags)}")
    
    # Get the case item
    case_item = module.get_document_item(formatted_id)
    
    # Remove each tag
    success = True
    for tag in tags:
        try:
            # Check if the tag is assigned to the case item
            item_tags = module.tags.get_item_tags(case_item)
            if tag not in item_tags:
                click.echo(f"Tag '{tag}' is not assigned to {formatted_id}, skipping", err=True)
                continue
                
            # Remove the tag from the case item
            module.tags.remove_tag(case_item, tag)
            if verbose:
                click.echo(f"Removed tag '{tag}' from {formatted_id}")
        except Exception as e:
            click.echo(f"Error removing tag '{tag}': {e}", err=True)
            success = False
    
    # Save changes
    if success:
        module.save()
        click.echo(f"Successfully removed tags from {formatted_id}")
    else:
        click.echo("Some tags could not be removed", err=True)
        ctx.exit(1)


@tag.command('list')
@click.argument('doc_id', required=False)
@click.option('-v', '--verbose', is_flag=True, help='Enable verbose output')
@click.pass_context
def list_tags(ctx: click.Context, doc_id: Optional[str], verbose: bool):
    """
    List tags for a case item or all available tags.
    
    If DOC_ID is provided, lists tags for that specific case item.
    If no DOC_ID is provided, lists all available tags in the project.
    
    Examples:
      textcase tag list           # List all available tags
      textcase tag list REQ001    # List tags for REQ001
    """
    # Get project from context
    project = ctx.obj.get('project')
    if not project:
        click.echo("Error: No valid project found.", err=True)
        ctx.exit(1)
    
    if doc_id:
        # List tags for a specific document
        doc_path, module, formatted_id = get_document_path(doc_id, project, ctx)
        if not doc_path or not module:
            click.echo(f"Error: Document '{doc_id}' not found.", err=True)
            ctx.exit(1)
        
        # Get the case item
        case_item = module.get_document_item(formatted_id)
        
        # Get and display tags
        tags = module.tags.get_item_tags(case_item)
        if tags:
            click.echo(f"Tags for {formatted_id}:")
            for tag in sorted(tags):
                click.echo(f"  - {tag}")
        else:
            click.echo(f"No tags found for {formatted_id}")
    else:
        # List all available tags
        all_tags = project.tags.get_tags()
        if all_tags:
            click.echo("Available tags:")
            for tag in sorted(all_tags):
                description = project.config.tags.get(tag, "")
                if description:
                    click.echo(f"  - {tag}: {description}")
                else:
                    click.echo(f"  - {tag}")
        else:
            click.echo("No tags defined in the project")
