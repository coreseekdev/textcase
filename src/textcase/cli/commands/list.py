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

import os
import click
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union, Any

from textcase.protocol.module import Module, DocumentCaseItem
from textcase.cli.utils import debug_echo, get_document_item, list_available_templates, parse_document_id
from textcase.cli.commands.list_module import (
    list_module_items, list_module_submodules, list_module_tags,
    list_root_modules, list_templates
)
from textcase.cli.commands.list_item import list_item_details


def list_configurations(project: Module, template_name: Optional[str] = None) -> Dict[str, List[str]]:
    """
    List available configurations.
    
    Args:
        project: The project module
        template_name: Optional template name to filter by
        
    Returns:
        Dictionary mapping template names to lists of configuration names
    """
    config_dir = project.path / ".config"
    if not config_dir.exists() or not config_dir.is_dir():
        return {}
        
    result = {}
    
    # List all subdirectories in .config (except 'template')
    for item in config_dir.iterdir():
        if item.is_dir() and item.name != "template":
            # If a specific template was requested, skip others
            if template_name and item.name != template_name:
                continue
                
            # Get all configuration files in this directory
            configs = []
            for config_file in item.iterdir():
                if config_file.is_file():
                    configs.append(config_file.stem)
                    
            if configs:
                result[item.name] = sorted(configs)
                
    return result


@click.command()
@click.argument('resource', required=False)
@click.pass_context
def list_cmd(ctx: click.Context, resource: Optional[str] = None):
    """
    List various resources in the project.
    
    Examples:
      tse list                    # List root modules and templates
      tse list REQ                # List items in the REQ module
      tse list REQ/items          # List items in the REQ module
      tse list REQ/modules        # List submodules of the REQ module
      tse list REQ/tags           # List tags in the REQ module
      tse list REQ1               # Show details of the REQ1 item
      tse list template_name      # List configurations for the template
      tse list /template          # List all templates
      tse list /modules           # List all modules in the project
      tse list /tags              # List all tags in the project
      tse list /items             # List all items in the project
    """
    # Get project from context
    project = ctx.obj.get('project')
    if not project:
        click.echo("Error: No valid project found.", err=True)
        ctx.exit(1)
        
    # If no resource is specified, list project items (equivalent to 'tse list REQ/item')
    if not resource:
        # 获取项目前缀
        project_prefix = project.prefix if hasattr(project, 'prefix') and project.prefix else None
        
        if project_prefix:
            # 列出项目中的所有条目，相当于 'tse list REQ/item'
            list_module_items(project, ctx)
        else:
            # 如果项目没有前缀，则默认列出模块和模板
            list_root_modules(project, ctx)
        return
    
    # 统一处理资源路径，无论是根级别（/resource）还是模块级别（module/resource）
    target_module = project  # 默认为项目模块
    resource_path = resource
    
    if resource.startswith('/'):
        # 根级别资源（如 /template, /modules 等）
        resource_path = resource[1:]
    else:
        # 解析模块级别资源（如 REQ/items, REQ/template/provider 等）
        module_prefix, raw_id, formatted_id, region = parse_document_id(resource, project, ctx)
        
        # 特殊处理资源路径格式（如 REQ/template, REQ/tag 等）
        if '/' in resource:
            resource_tokens = resource.split('/')
            if len(resource_tokens) >= 2:
                # 处理模板资源
                if resource_tokens[1] == 'template':
                    if len(resource_tokens) == 2:
                        # REQ/template 格式
                        if ctx:
                            debug_echo(ctx, f"Special handling for template resource: {resource}")
                        region = 'template'
                    elif len(resource_tokens) >= 3:
                        # REQ/template/provider 格式
                        if ctx:
                            debug_echo(ctx, f"Special handling for template subresource: {resource}")
                        region = f"template/{resource_tokens[2]}"
                # 处理标签资源
                elif resource_tokens[1] == 'tag' or resource_tokens[1] == 'tags':
                    if ctx:
                        debug_echo(ctx, f"Special handling for tag resource: {resource}")
                    region = 'tag'
                # 处理模块资源
                elif resource_tokens[1] == 'module' or resource_tokens[1] == 'modules':
                    if ctx:
                        debug_echo(ctx, f"Special handling for module resource: {resource}")
                    region = 'module'
                # 处理条目资源
                elif resource_tokens[1] == 'item' or resource_tokens[1] == 'items':
                    if ctx:
                        debug_echo(ctx, f"Special handling for item resource: {resource}")
                    region = 'item'
        
        # 获取目标模块
        if project.prefix == module_prefix:
            target_module = project
        else:
            target_module = None
            for module in project.get_submodules():
                if hasattr(module, 'prefix') and module.prefix == module_prefix:
                    target_module = module
                    break
        
        if not target_module:
            click.echo(f"Error: Could not parse resource path: {resource}", err=True)
            return
            
        if formatted_id != module_prefix:  # 不仅仅是模块前缀
            item, _ = get_document_item(resource, project, ctx)
            if item:
                list_item_details(item, region, ctx)
                return

        # 如果没有指定资源类型，则检查是否是特定条目
        if not region:
            # 默认行为：列出模块中的条目
            list_module_items(target_module, ctx)
            return
            
        # 使用 region 作为资源路径
        resource_path = region
        
        # 注意：我们已经在特殊处理 REQ/template 格式时处理了 template 资源类型
        # 这里不需要重复处理
    
    # 处理资源路径
    # 检查是否是模板相关资源（template 或 template/name）
    if resource_path == 'template' or resource_path.startswith('template/'):
        # 只有项目模块才有模板资源
        if target_module is project or target_module.prefix == project.prefix:
            # 检查是否是模板子资源（如 template/provider）
            if '/' in resource_path:
                template_parts = resource_path.split('/', 1)
                template_name = template_parts[1]
                # 列出指定模板的所有配置文件
                configs = list_configurations(project, template_name)
                if configs:
                    click.echo(f"Configurations for template '{template_name}':")
                    for template_name, config_list in sorted(configs.items()):
                        click.echo(f"  {template_name}:")
                        for config_name in config_list:
                            click.echo(f"    - {config_name}")
                else:
                    click.echo(f"No configurations found for template '{template_name}'.")
            else:
                # 列出所有模板
                list_templates(target_module, ctx)
        else:
            click.echo(f"Error: Module '{target_module.prefix}' does not have template resources", err=True)
        return  # 在处理完模板资源后立即返回，避免继续执行未知资源类型的处理逻辑
    
    # 处理其他基本资源类型
    if resource_path == 'item' or resource_path == 'items':
        list_module_items(target_module, ctx)
        return
        
    if resource_path == 'module' or resource_path == 'modules':
        list_module_submodules(target_module, ctx)
        return
        
    if resource_path == 'tag' or resource_path == 'tags':
        list_module_tags(target_module, ctx)
        return
        
    # 未知资源类型
    click.echo(f"Error: Unknown resource type: {resource_path}", err=True)
