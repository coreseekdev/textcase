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
"""List configuration command implementation."""

import os
import click
from pathlib import Path
from typing import Optional, List, Dict

from textcase.protocol.module import Module
from textcase.cli.utils import debug_echo
from textcase.cli.utils.template_utils import list_available_templates


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
@click.option('-t', '--templates', is_flag=True, help='List available templates')
@click.option('-c', '--configs', is_flag=True, help='List available configurations')
@click.option('--template', help='Filter configurations by template name')
@click.pass_context
def list_conf(ctx: click.Context, templates: bool, configs: bool, template: Optional[str] = None):
    """
    List available templates and configurations.
    
    Examples:
      textcase list-conf -t            # List all available templates
      textcase list-conf -c            # List all configurations
      textcase list-conf --template prompt  # List configurations for the 'prompt' template
      textcase list-conf               # List both templates and configurations
    """
    # Get project from context
    project = ctx.obj.get('project')
    if not project:
        click.echo("Error: No valid project found.", err=True)
        ctx.exit(1)
        
    # If neither flag is specified, show both
    if not templates and not configs:
        templates = True
        configs = True
        
    # List templates if requested
    if templates:
        template_list = list_available_templates(project)
        if template_list:
            click.echo("Available templates:")
            for template_name in sorted(template_list):
                click.echo(f"  - {template_name}")
        else:
            click.echo("No templates found.")
            
        if configs:
            click.echo()  # Add a blank line between sections
            
    # List configurations if requested
    if configs:
        config_dict = list_configurations(project, template)
        if config_dict:
            if template:
                click.echo(f"Configurations for template '{template}':")
            else:
                click.echo("Available configurations:")
                
            for template_name, config_list in sorted(config_dict.items()):
                click.echo(f"  {template_name}:")
                for config_name in config_list:
                    click.echo(f"    - {config_name}")
        else:
            if template:
                click.echo(f"No configurations found for template '{template}'.")
            else:
                click.echo("No configurations found.")
