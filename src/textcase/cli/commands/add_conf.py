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
"""Add configuration command implementation."""

import os
import re
import time
import click
import jinja2
from pathlib import Path
from typing import Optional, Dict, Any, Tuple, List

from textcase.protocol.module import Module
from textcase.core.module import YamlModule
from textcase.cli.utils import debug_echo
from textcase.cli.commands.edit import edit_with_editor, get_editor


def get_template_path(project: Module, template_name: str) -> Optional[Path]:
    """
    Get the path to a template file.
    
    Args:
        project: The project module
        template_name: The name of the template
        
    Returns:
        Path to the template file or None if not found
    """
    # Check if the template directory exists
    template_dir = project.path / ".config" / "template"
    if not template_dir.exists():
        return None
        
    # Look for a template file with the given name (ignoring extension)
    for file_path in template_dir.iterdir():
        if file_path.is_file() and file_path.stem == template_name:
            return file_path
            
    return None


def render_template(template_path: Path, context: Dict[str, Any]) -> str:
    """
    Render a Jinja2 template with the given context.
    
    Args:
        template_path: Path to the template file
        context: Dictionary of variables to use in rendering
        
    Returns:
        Rendered template content
    """
    # Create Jinja2 environment
    env = jinja2.Environment(
        loader=jinja2.FileSystemLoader(template_path.parent),
        undefined=jinja2.Undefined,  # Allow undefined variables
    )
    
    # Load the template
    template = env.get_template(template_path.name)
    
    # Render the template
    try:
        content = template.render(**context)
        return content
    except Exception as e:
        # If rendering fails, return the raw template content
        with open(template_path, 'r') as f:
            return f.read()


def parse_config_id(config_id: str) -> Tuple[str, str]:
    """
    Parse a configuration ID in the format 'template_name:name'.
    
    Args:
        config_id: The configuration ID to parse
        
    Returns:
        Tuple of (template_name, config_name)
    """
    if ':' not in config_id:
        return config_id, ""
        
    parts = config_id.split(':', 1)
    return parts[0].strip(), parts[1].strip()


def add_configuration(ctx: click.Context, project: Module, template_name: str, config_name: str) -> bool:
    """
    Add a new configuration based on a template.
    
    Args:
        ctx: Click context
        project: The project module
        template_name: The name of the template to use
        config_name: The name of the configuration to create
        
    Returns:
        True if successful, False otherwise
    """
    debug_echo(ctx, f"Adding configuration: {template_name}:{config_name}")
    
    # Get the template path
    template_path = get_template_path(project, template_name)
    if not template_path:
        click.echo(f"Error: Template '{template_name}' not found.", err=True)
        return False
        
    debug_echo(ctx, f"Found template: {template_path}")
    
    # Create the configuration directory if it doesn't exist
    config_dir = project.path / ".config" / template_name
    config_dir.mkdir(parents=True, exist_ok=True)
    
    # Determine the output file path
    output_path = config_dir / f"{config_name}{template_path.suffix}"
    if output_path.exists():
        click.echo(f"Error: Configuration '{config_name}' already exists.", err=True)
        return False
        
    # Get global variables from project settings
    global_vars = project.config.settings.get('variables', {})
    
    # Render the template
    content = render_template(template_path, global_vars)
    
    # Write the initial content to the output file
    with open(output_path, 'w') as f:
        f.write(content)
        
    # Open the file in the editor
    editor = get_editor()
    modified, _ = edit_with_editor(output_path)
    
    if not modified:
        # If the user didn't make any changes, delete the file
        output_path.unlink()
        click.echo("No changes made, configuration not created.")
        return False
        
    click.echo(f"Created configuration: {template_name}:{config_name}")
    return True


def add_conf_command(ctx: click.Context, config_id: str) -> bool:
    """
    Handle the add_conf command.
    
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
        
    # Add the configuration
    return add_configuration(ctx, project, template_name, config_name)
