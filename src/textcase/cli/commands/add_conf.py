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
import tempfile
import click
import jinja2
import jinja2.meta
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


class PreserveUndefined(jinja2.Undefined):
    """A custom undefined handler that preserves the original variable syntax."""
    def __str__(self):
        # Return the original variable syntax when rendered as string
        return f"{{{{ {self._undefined_name} }}}}"
    
    def __getattr__(self, name):
        # Allow chaining of undefined attributes
        return self
    
    __getitem__ = __getattr__
    __call__ = __getattr__
    __add__ = __getattr__
    __radd__ = __getattr__


def render_template(ctx: click.Context, template_path: Path, context: Dict[str, Any]) -> str:
    """
    Render a Jinja2 template with the given context.
    
    This function will automatically populate template variables from environment variables
    if they are not provided in the context. Environment variables should be prefixed with
    'TEMPLATE_' followed by the variable name in uppercase.
    
    Args:
        template_path: Path to the template file
        context: Dictionary of variables to use in rendering
        
    Returns:
        Rendered template content with unresolved variables preserved as-is
    """
    debug_echo(ctx, "=== Starting template rendering ===")
    debug_echo(ctx, f"Template path: {template_path}")
    debug_echo(ctx, f"Template exists: {template_path.exists()}")
    
    # Read the template content first
    try:
        with open(template_path, 'r') as f:
            template_content = f.read()
        debug_echo(ctx, f"Template content (first 100 chars):\n{template_content[:100]}...")
    except Exception as e:
        debug_echo(ctx, f"Error reading template file: {e}", err=True)
        return ""
    
    # Create Jinja2 environment with our custom undefined handler
    env = jinja2.Environment(
        undefined=PreserveUndefined,  # Use our custom undefined handler
    )
    
    # Parse the template to find all variables
    try:
        ast = env.parse(template_content)
        template_vars = jinja2.meta.find_undeclared_variables(ast)
        debug_echo(ctx, f"Found template variables: {template_vars}")
    except Exception as e:
        debug_echo(ctx, f"Error parsing template: {e}", err=True)
        return template_content
    
    # Create a copy of the context to avoid modifying the original
    render_context = context.copy()
    debug_echo(ctx, f"Initial context: {render_context}")
    
    # Populate variables from environment variables
    for var in template_vars:
        env_var = f"TEMPLATE_{var.upper()}"
        if var not in render_context and env_var in os.environ:
            render_context[var] = os.environ[env_var]
            debug_echo(ctx, f"Set {var} from environment variable {env_var} = {os.environ[env_var]}")
    
    debug_echo(ctx, f"Final render context: {render_context}")
    
    # Render the template
    try:
        template = env.from_string(template_content)
        content = template.render(**render_context)
        debug_echo(ctx, f"Rendered content (first 200 chars):\n{content[:200]}...")
        debug_echo(ctx, "=== Template rendering completed successfully ===")
        return content
    except Exception as e:
        debug_echo(ctx, f"Error rendering template: {e}", err=True)
        debug_echo(ctx, "Returning original template content due to error")
        return template_content


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
    
    # Add environment variables to the context
    for key, value in os.environ.items():
        if key.startswith('TEMPLATE_'):
            var_name = key[9:].lower()  # Remove 'TEMPLATE_' prefix and convert to lowercase
            debug_echo(ctx, f"Adding environment variable to context: {var_name} = {value}")
            global_vars[var_name] = value
    
    # Add default values for required variables if not provided
    if 'name' not in global_vars:
        global_vars['name'] = config_name
    if 'description' not in global_vars:
        global_vars['description'] = f"Configuration for {config_name}"
    
    debug_echo(ctx, f"Rendering template with context: {global_vars}")
    
    # Render the template
    content = render_template(ctx, template_path, global_vars)
    
    if not content:
        click.echo("Error: Failed to render template.", err=True)
        return False
    
    # Create a temporary file with the rendered content
    with tempfile.NamedTemporaryFile(mode='w+', suffix=template_path.suffix, delete=False) as temp_file:
        temp_file.write(content)
        temp_path = temp_file.name
    
    try:
        # Convert temp_path to a Path object for edit_with_editor
        temp_path_obj = Path(temp_path)
        
        # Open the temporary file in the editor
        modified, _ = edit_with_editor(temp_path_obj)
        
        if not modified:
            debug_echo(ctx, "No changes made, configuration not created.")
            return False
            
        # Read the modified content
        with open(temp_path, 'r') as f:
            final_content = f.read()
            
        # Write the final content to the output file
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w') as f:
            f.write(final_content)
            
    finally:
        # Clean up the temporary file
        try:
            os.unlink(temp_path)
        except OSError:
            pass
        
    debug_echo(ctx, f"Created configuration: {template_name}:{config_name}")
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
