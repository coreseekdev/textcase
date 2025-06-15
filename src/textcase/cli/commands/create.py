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

from textcase.textcase import TextCaseFactory, TextCase
from textcase.cli.utils import debug_echo

@click.command()
@click.argument('collection_prefix', type=str)
@click.argument('collection_path', type=click.Path(path_type=Path))
@click.option('--parent', help='Parent collection name (required for subcollections)')
@click.option('--tag', 'tags', multiple=True, help='Collection tag in format tag_name=description or just tag_name (can be used multiple times)')
@click.pass_context
def create(ctx: click.Context, collection_prefix: str, collection_path: Path, 
         parent: Optional[str] = None, tags: List[str] = None):
    """
    Create a new collection or subcollection.
    
    COLLECTION_PREFIX is the prefix for collection items (e.g., DOC, CODE).
    COLLECTION_PATH is the path where the collection will be created.
    
    Example usage:
      textcase create DOC ./docs/
      textcase create CODE ./src/ --parent docs --tag priority=high --tag status=active
    """
    # Get TextCase factory from context
    textcase_factory: TextCaseFactory = ctx.obj.get('textcase_factory')
    
    if parent is None:
        # parent 不存在的情况，创建新的 TextCase 项目
        try:
            # 创建新的 TextCase 实例
            textcase = textcase_factory.create(
                file_path=collection_path,
                collection_name=collection_prefix
            )
            ctx.obj['textcase'] = textcase
            click.echo(f"Created new TextCase project at {collection_path} with root collection '{collection_prefix}'")
            return
        except Exception as e:
            click.echo(f"Error: Failed to create TextCase instance: {e}", err=True)
            # import traceback
            # print(traceback.format_exc())
            ctx.exit(1)
    else:
        # parent 存在的情况， 要求上下文中已经存在
        try:
            textcase: Optional[TextCase] = ctx.obj.get('textcase')
            if textcase is None:
                click.echo(f"Error: TextCase instance not found in context", err=True)
                ctx.exit(1)
        except Exception as e:
            click.echo(f"Error: Failed to get TextCase instance: {e}", err=True)
            ctx.exit(1)

        # Get resource manager
        resource_manager = textcase.resource_manager
        
        # Check if collection already exists
        try:
            existing_collection = resource_manager.get_collection(collection_prefix)
            if existing_collection:
                click.echo(f"Error: Collection '{collection_prefix}' already exists at {existing_collection.path}", err=True)
                ctx.exit(1)
        except Exception:
            # Collection doesn't exist, which is what we want
            pass

        # Check parent
        try:
            parent_collection = resource_manager.get_collection(parent)
            if not parent_collection:
                click.echo(f"Error: Parent collection '{parent}' not found", err=True)
                ctx.exit(1)
        except Exception as e:
            click.echo(f"Error: Parent collection '{parent}' not found: {e}", err=True)
            ctx.exit(1)
        
        # Parse tags
        parsed_tags = {}
        if tags:
            for tag_str in tags:
                if '=' in tag_str:
                    tag_name, tag_description = tag_str.split('=', 1)
                else:
                    tag_name, tag_description = tag_str, ''
                parsed_tags[tag_name] = tag_description
        
        # Create the collection
        collection = resource_manager.create_collection(
            name=collection_prefix,
            path=str(collection_path),
            parent=parent
        )
        
        # Add tags to the collection if provided
        if tags:
            # TODO: Implement adding tags to collection
            for tag_str in tags:
                tag_name, tag_description = tag_str.split('=', 1) if '=' in tag_str else (tag_str, '')
                collection. add_tag(tag_name, tag_description)
        
        # TODO: 添加 collection 到 resource_manager