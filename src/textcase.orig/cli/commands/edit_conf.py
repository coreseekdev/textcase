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
"""Edit configuration command implementation."""

import os
import click
from pathlib import Path
from typing import Optional, Tuple, Dict, Any

from textcase.protocol.module import Module
from textcase.cli.utils import debug_echo
from textcase.cli.commands.edit import edit_with_editor, get_editor
from textcase.cli.commands.add_conf import parse_config_id


def find_config_file(project: Module, template_name: str, config_name: str) -> Optional[Path]:
    """
    Find a configuration file.
    
    Args:
        project: The project module
        template_name: The name of the template
        config_name: The name of the configuration
        
    Returns:
        Path to the configuration file or None if not found
    """
    # Check if the configuration directory exists
    config_dir = project.path / ".config" / template_name
    if not config_dir.exists():
        return None
        
    # Look for a configuration file with the given name (with any extension)
    for file_path in config_dir.iterdir():
        if file_path.is_file() and file_path.stem == config_name:
            return file_path
            
    return None


def edit_configuration(ctx: click.Context, project: Module, template_name: str, config_name: str) -> bool:
    """
    Edit an existing configuration.
    
    Args:
        ctx: Click context
        project: The project module
        template_name: The name of the template
        config_name: The name of the configuration
        
    Returns:
        True if successful, False otherwise
    """
    debug_echo(ctx, f"Editing configuration: {template_name}:{config_name}")
    
    # Find the configuration file
    config_path = find_config_file(project, template_name, config_name)
    if not config_path:
        click.echo(f"Error: Configuration '{template_name}:{config_name}' not found.", err=True)
        return False
        
    debug_echo(ctx, f"Found configuration: {config_path}")
    
    # Open the file in the editor
    editor = get_editor()
    modified, _ = edit_with_editor(config_path)
    
    if not modified:
        click.echo("No changes made.")
        return True
        
    click.echo(f"Updated configuration: {template_name}:{config_name}")
    return True


def edit_conf_command(ctx: click.Context, config_id: str) -> bool:
    """
    Handle the edit_conf command.
    
    Args:
        ctx: Click context
        config_id: The configuration ID in the format 'template_name:name'
        
    Returns:
        True if successful, False otherwise
    """
    # Get project from context
    project = ctx.obj.get('project')
    if not project:
        click.echo("Error: No valid project found.", err=True)
        return False
        
    # Parse the configuration ID
    template_name, config_name = parse_config_id(config_id)
    if not template_name:
        click.echo("Error: Invalid configuration ID. Format should be 'template_name:name'.", err=True)
        return False
        
    if not config_name:
        click.echo("Error: Configuration name not specified. Format should be 'template_name:name'.", err=True)
        return False
        
    # Edit the configuration
    return edit_configuration(ctx, project, template_name, config_name)
