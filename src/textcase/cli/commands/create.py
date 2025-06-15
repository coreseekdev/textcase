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
"""Create command implementation."""

import os
import sys
import click
from pathlib import Path
from typing import Optional, Dict, Any, List

from textcase.textcase import TextCaseFactory
from textcase.cli.utils import debug_echo

@click.command()
@click.argument('collection_name', type=str)
@click.argument('collection_path', type=click.Path(path_type=Path))
@click.option('--parent', help='Parent collection name (required for subcollections)')
@click.option('--tags', help='Collection tags in format tag1=description1,tag2=description2')
@click.pass_context
def create(ctx: click.Context, collection_name: str, collection_path: Path, 
         parent: Optional[str] = None, tags: Optional[str] = None):
    """
    Create a new collection or subcollection.
    
    COLLECTION_NAME is the name of the collection (e.g., docs, code).
    COLLECTION_PATH is the path where the collection will be created.
    
    Example usage:
      textcase create docs ./docs/
      textcase create code ./src/ --parent docs
    """
    # Get TextCase instance from context
    textcase = ctx.obj.get('textcase')
    
    # For create command, we need to create a new TextCase instance if one doesn't exist
    if textcase is None:
        try:
            # Create a new TextCase instance using the collection_path
            textcase = TextCaseFactory.create(
                file_path=collection_path,
                collection_name=collection_name
            )
            ctx.obj['textcase'] = textcase
            click.echo(f"Created new TextCase project at {collection_path} with root collection '{collection_name}'")
            return
        except Exception as e:
            click.echo(f"Error: Failed to create TextCase instance: {e}", err=True)
            import traceback
            print(traceback.format_exc())
            ctx.exit(1)
    
    # If we have a parent, we're creating a subcollection in an existing project
    if parent is not None and textcase is None:
        click.echo("Error: No valid TextCase instance found.", err=True)
        ctx.exit(1)
    
    # Get VFS from TextCase
    vfs = textcase.vfs
    
    # Get resource manager
    resource_manager = textcase.resource_manager
    
    # Resolve collection path
    if not collection_path.is_absolute():
        # If path is relative, resolve it relative to the repository root
        collection_path = Path(textcase.repo_root_path) / collection_path
    
    # Check if collection already exists
    try:
        existing_collection = resource_manager.get_collection(collection_name)
        if existing_collection:
            click.echo(f"Error: Collection '{collection_name}' already exists at {existing_collection.path}", err=True)
            ctx.exit(1)
    except Exception:
        # Collection doesn't exist, which is what we want
        pass
    
    # Check if parent collection exists when specified
    parent_collection = None
    if parent:
        try:
            parent_collection = resource_manager.get_collection(parent)
            if not parent_collection:
                click.echo(f"Error: Parent collection '{parent}' not found", err=True)
                ctx.exit(1)
        except Exception as e:
            click.echo(f"Error: Parent collection '{parent}' not found: {e}", err=True)
            ctx.exit(1)
    
    # Create the collection directory if it doesn't exist
    try:
        os.makedirs(collection_path, exist_ok=True)
    except Exception as e:
        click.echo(f"Error creating collection directory: {e}", err=True)
        ctx.exit(1)
    
    # Create the collection
    try:
        debug_echo(ctx, f"Creating collection '{collection_name}' at {collection_path}")
        
        # Parse and apply tags if provided
        tag_dict = {}
        if tags:
            tag_pairs = tags.split(',')
            for pair in tag_pairs:
                if '=' in pair:
                    tag, description = pair.split('=', 1)
                    tag_dict[tag.strip()] = description.strip()
                else:
                    tag_dict[pair.strip()] = ""
        
        # Create the collection
        collection = resource_manager.create_collection(
            name=collection_name,
            path=str(collection_path),
            parent_name=parent
        )
        
        # Add tags to the collection if provided
        if tag_dict:
            # TODO: Implement adding tags to collection
            pass
        
        click.echo(f"Created collection '{collection_name}' at {collection_path}")
        
    except Exception as e:
        click.echo(f"Error creating collection: {e}", err=True)
        ctx.exit(1)