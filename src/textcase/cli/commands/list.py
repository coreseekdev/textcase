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
"""List command implementation."""

import click
from typing import Optional, TypeVar

from textcase.proto.resource_collection_protocol import ResourceCollection
from textcase.cli.utils import debug_echo

T = TypeVar('T')

@click.command()
@click.argument('collection_name', required=False)
@click.pass_context
def list_cmd(ctx: click.Context, collection_name: Optional[str] = None):
    """
    List items in a collection.
    
    COLLECTION_NAME is the name or prefix of the collection to list items from.
    If not provided, all available collections will be listed.
    
    Examples:
      textcase list           # List all available collections
      textcase list req       # List all items in the REQ collection
    """
    # Get TextCase instance from context
    textcase = ctx.obj.get('textcase')
    if not textcase:
        click.echo("Error: No valid TextCase instance found.", err=True)
        ctx.exit(1)
    
    # Get resource manager
    resource_manager = textcase.resource_manager
    
    # If no collection name is provided, list all collections
    if not collection_name:
        collections = resource_manager.list_collections()
        if collections:
            for coll_name in collections:
                collection = resource_manager.get_collection(coll_name)
                if collection and collection.config and collection.config.prefix:
                    click.echo(f"{coll_name} (prefix: {collection.config.prefix})")
                else:
                    click.echo(f"{coll_name}")
        else:
            click.echo("No collections found.")
        return
    
    # Try to find the collection using parse_resource_reference
    collection = None
    item = None
    
    try:
        collection, item = resource_manager.parse_resource_reference(collection_name, partial=False)
    except Exception as e:
        debug_echo(ctx, f"Error parsing resource reference: {e}")
    
    if not collection:
        click.echo(f"Error: Collection '{collection_name}' not found.", err=True)
        ctx.exit(1)
    
    # If an item was found, it means the user provided an item reference instead of just a collection
    if item:
        click.echo(f"Warning: '{collection_name}' appears to be an item reference, not just a collection name.")
        click.echo(f"Listing all items in collection '{collection.name}':")
    
    # List all items in the collection
    items = collection.list_items()
    if items:
        # Sort items for consistent output
        sorted_items = sorted(items)
        
        # click.echo(f"Items in collection '{collection.name}':")
        for item_name in sorted_items:
            item_key = collection.get_item_key(item_name)
            click.echo(f"{item_key}")
    else:
        click.echo(f"No items found in collection '{collection.name}'.")
