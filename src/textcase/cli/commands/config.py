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
"""Configuration management commands."""

import os
import sys
from tabnanny import verbose
import click
import tempfile
import subprocess
from pathlib import Path
from typing import Optional, Tuple, List, Dict, Any

from ...textcase import TextCase

from ...collection.config_collection_manager import ConfigCollectionManagerImpl
from ...collection.config_collection import ConfigCollectionImpl, ConfigTemplateCollectionImpl
from ...proto.resource_collection_protocol import ResourceCollection, ResourceItem
from ...textcase import TextCase


def _get_editor() -> str:
    """Get the editor command to use for editing files."""
    editor = os.environ.get('EDITOR')
    if not editor:
        if sys.platform.startswith('win'):
            editor = 'notepad'
        else:
            editor = 'vim'
    return editor


def _edit_config_file(file_path: str) -> None:
    """Open a file in the user's preferred editor.
    
    Args:
        file_path: Path to the file to edit
    """
    editor = _get_editor()
    try:
        subprocess.run([editor, file_path], check=True)
    except subprocess.CalledProcessError:
        click.echo(f"Failed to open editor {editor} for file {file_path}")
    except FileNotFoundError:
        click.echo(f"Editor {editor} not found. Set the EDITOR environment variable to your preferred editor.")


def _parse_config_reference(textcase: TextCase, reference: str, partial: bool = False) -> Tuple[Optional[ResourceCollection], Optional[ResourceItem]]:
    """Parse a configuration reference.
    
    Args:
        tc: TextCase instance
        reference: Reference string (e.g., "config.agent.default")
        partial: Whether to allow partial matching
        
    Returns:
        Tuple of (collection, item) or (collection, None) if only collection found
        or (None, None) if reference is invalid
    """
    # 确保引用以 config. 开头
    if not reference.startswith("config."):
        click.echo(f"Invalid configuration reference: {reference}. Must start with 'config.'")
        return None, None
    
    # 使用资源管理器解析引用
    collection, item = textcase.resource_manager.parse_resource_reference(reference, partial)
    
    # 检查是否是模板集合引用
    if collection and collection.name.endswith(".template"):
        # 这是一个模板集合引用，需要特殊处理
        pass
    
    return collection, item


def _get_template_collection(collection: ResourceCollection) -> Optional[ConfigTemplateCollectionImpl]:
    """Get the template collection for a config collection.
    
    Args:
        collection: Configuration collection
        
    Returns:
        Template collection or None if not available
    """
    if not isinstance(collection, ConfigCollectionImpl):
        return None
    
    return collection.template_collection


@click.command()
@click.argument('reference', required=False)
@click.argument('item_name', required=False)
@click.argument('template_name', required=False)
@click.pass_context
def config_cmd(ctx: click.Context, reference: Optional[str] = None, item_name: Optional[str] = None, 
              template_name: Optional[str] = None) -> None:
    """Manage configuration collections and items.
    
    REFERENCE is a configuration reference (e.g., config.agent, config.agent.default).
    
    ITEM_NAME is the name of a configuration item to edit or create.
    
    TEMPLATE_NAME is the name of a template to use when creating a new item.
    
    Examples:
    
    \b
    # List all configuration collections
    textcase config
    
    \b
    # List all items in a configuration collection
    textcase config config.agent
    
    \b
    # List all templates in a configuration collection
    textcase config config.agent.template
    
    \b
    # Edit or create a configuration item
    textcase config config.agent my_agent
    
    \b
    # Create a configuration item from a specific template
    textcase config config.agent my_agent custom_template
    """
    # 获取 TextCase 实例
    textcase = ctx.obj.get('textcase')
    verbose = ctx.obj.get('verbose')
    if not textcase:
        click.echo("Error: No valid TextCase instance found.", err=True)
        ctx.exit(1)
    
    # 情况 1: 没有参数，列出所有预定义的配置集合
    if not reference:
        predefined = ConfigCollectionManagerImpl.PREDEFINED_COLLECTIONS
        # click.echo("Available configuration collections:")
        for collection_name in predefined:
            click.echo(f"{collection_name}")
        return
    
    # 解析引用
    parts = reference.split('.')

    # config.xxx.template 采用普通配置集合同样的方式处理

    # 情况 3: 引用是一个配置集合 (config.xxx)
    collection, _ = _parse_config_reference(textcase, reference, False)
    if not collection:
        click.echo(f"Configuration collection {reference} not found")
        return
    
    # 如果没有指定项目名称，列出集合中的所有项目
    if not item_name:
        items = collection.list_items()
        if not items:
            click.echo(f"No items found in {reference}")
            return
        
        # click.echo(f"Items in {reference}:")
        for item in items:
            click.echo(f"{item}")
        return
    
    # 情况 4 & 5: 编辑或创建配置项
    # 检查项目是否存在
    item = collection.get_item(item_name)
    
    if not item:
        # 项目不存在，需要创建
        if not isinstance(collection, ConfigCollectionImpl):
            click.echo(f"Cannot create items in {reference}")
            return
        
        # 获取模板集合
        template_collection = _get_template_collection(collection)
        if not template_collection:
            click.echo(f"Template collection for {reference} not available")
            return
        
        # 确定使用哪个模板
        template_to_use = template_name if template_name else collection.get_default_template_name()
        
        # 检查模板是否存在
        template_item = template_collection.get_item(template_to_use)
        if not template_item:
            if template_name:
                # 用户指定了模板但不存在
                click.echo(f"Template {template_to_use} not found in {reference}.template")
                return
            else:
                # 默认模板不存在
                click.echo(f"Default template not found in {reference}.template")
                return
        
        try:
            # 创建新的配置项
            item = collection.create_from_template(item_name, template_to_use)
            click.echo(f"Created new configuration item {item_name} from template {template_to_use}")
        except Exception as e:
            click.echo(f"Failed to create configuration item: {e}")
            return
    
    # 现在我们有了一个项目（新创建的或已存在的），编辑它
    if not isinstance(item, ResourceItem):
        click.echo(f"Cannot edit {item_name}")
        return
    
    # 获取项目的文件路径
    if isinstance(collection, ConfigCollectionImpl):
        file_path = collection.path / f"{item_name}.yml"
        # 编辑文件
        _edit_config_file(str(file_path))
        click.echo(f"Edited configuration item {item_name}")
    else:
        click.echo(f"Cannot edit items in {reference}")
