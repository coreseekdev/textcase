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
from typing import List, Optional, Tuple, Set

from textcase.cli.utils import debug_echo


@click.command()
@click.argument('resource_name')
@click.argument('tags', nargs=-1, required=False)
@click.option('-r', '--remove', is_flag=True, help='Remove tags instead of adding them')
@click.pass_context
def tag(ctx: click.Context, resource_name: str, tags: tuple, remove: bool):
    """
    Add, remove, or list tags for a resource item.
    
    RESOURCE_NAME is the reference to the resource item (e.g. 'req1').
    TAGS are one or more tags to add or remove from the resource item.
    
    If no TAGS are provided, lists all tags for the resource item.
    
    Examples:
      textcase tag req1                               # List tags for req1
      textcase tag req1 important documentation        # Add multiple tags
      textcase tag -r req1 important                   # Remove a tag
    """
    # Get TextCase instance from context
    textcase = ctx.obj.get('textcase')
    verbose = ctx.obj.get('verbose')
    
    if not textcase:
        click.echo("Error: No valid TextCase instance found.", err=True)
        ctx.exit(1)
    
    # Get resource manager
    resource_manager = textcase.resource_manager
    
    # 使用 parse_resource_reference 解析资源引用
    collection = None
    item = None
    
    try:
        collection, item = resource_manager.parse_resource_reference(resource_name, partial=False)
    except Exception as e:
        debug_echo(ctx, f"Error parsing resource reference: {e}")
    
    if not collection:
        click.echo(f"Error: Resource '{resource_name}' not found.", err=True)
        ctx.exit(1)
    
    # 获取集合中定义的有效标签
    valid_tags: Set[str] = set()
    if collection.config and hasattr(collection.config, 'tags'):
        valid_tags = set(collection.config.tags)
    
    # 如果只找到集合但没有找到项目，则列出集合可用的标签
    if not item:
        if valid_tags:
            # click.echo(f"Available tags for collection '{collection.name}':")
            for tag in sorted(valid_tags):
                click.echo(f"{tag}")
        else:
            click.echo(f"No tags defined for collection '{collection.name}'")
        return
    
    # 获取项目的完整引用，用于显示
    item_key = collection.get_item_key(item.name)
    
    # 如果没有提供标签，则列出项目的所有标签
    if not tags:
        item_tags = item.tags
        if item_tags:
            # click.echo(f"Tags for {item_key}:")
            for tag in sorted(item_tags):
                click.echo(f"{tag}")
        else:
            click.echo(f"No tags found for {item_key}")
        return
    
    if verbose:
        action = "Removing" if remove else "Adding"
        click.echo(f"{action} tags to {item_key}: {', '.join(tags)}")
    
    # 获取集合中定义的有效标签
    valid_tags: Set[str] = set()
    if collection.config and hasattr(collection.config, 'tags'):
        valid_tags = set(collection.config.tags)
    
    # 处理每个标签
    success = True
    for tag_name in tags:
        try:
            # 不区分大小写匹配标签
            matching_tag = None
            for valid_tag in valid_tags:
                if valid_tag.upper() == tag_name.upper():
                    matching_tag = valid_tag
                    break
            
            # 如果找到匹配的标签，使用集合中定义的大小写形式
            actual_tag = matching_tag if matching_tag else tag_name
            
            # 检查标签是否在集合的有效标签列表中
            if not matching_tag and not remove:
                click.echo(f"Warning: Tag '{tag_name}' is not defined in collection '{collection.name}'")
            
            if remove:
                # 移除标签 (不区分大小写)
                tag_removed = False
                for existing_tag in list(item.tags):  # 创建副本以便在迭代时修改
                    if existing_tag.upper() == tag_name.upper():
                        item.unassign_tag(existing_tag)
                        click.echo(f"Removed tag '{existing_tag}' from {item_key}")
                        tag_removed = True
                
                if not tag_removed and verbose:
                    # 如果项目本来就没有这个标签，也正常返回，不报错
                    click.echo(f"Item {item_key} does not have tag '{tag_name}'")
            else:
                # 添加标签 (使用匹配的大小写形式)
                has_tag = False
                for existing_tag in item.tags:
                    if existing_tag.upper() == actual_tag.upper():
                        has_tag = True
                        break
                
                if has_tag:
                    if verbose:
                        click.echo(f"Item {item_key} already has tag '{actual_tag}'")
                else:
                    item.assign_tag(actual_tag)
                    click.echo(f"Added tag '{actual_tag}' to {item_key}")
        except Exception as e:
            action = "removing" if remove else "adding"
            click.echo(f"Error {action} tag '{tag_name}': {e}", err=True)
            success = False
    
    if success:
        action = "removed from" if remove else "added to"
        if len(tags) > 0:
            click.echo(f"Successfully {action} {item_key}")
    else:
        action = "remove" if remove else "add"
        click.echo(f"Some tags could not be {action}d", err=True)
        ctx.exit(1)




