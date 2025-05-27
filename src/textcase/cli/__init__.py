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
"""CLI interface for TextCase."""

import click
from pathlib import Path
from typing import Optional

from pathlib import Path
from typing import Optional

import click

from ..core import create_project, get_default_vfs

# Import all command modules
from .commands.create import create
from .commands.edit import edit
from .commands.link import link
from .commands.unlink import unlink
from .commands.clear import clear
from .commands.archive import archive

@click.group(invoke_without_command=True)
@click.option('--project-path', '-p', type=click.Path(exists=True, file_okay=False, path_type=Path), 
              help='Path to an existing project directory')
@click.option('--verbose', '-v', is_flag=True, help='Enable verbose output')
@click.pass_context
def cli(ctx: click.Context, project_path: Optional[Path] = None, verbose: bool = False):
    """TextCase - A full-stack text-based CASE tool.
    
    This tool requires an existing project with a .textcase.yml file.
    Use the 'create' command to initialize a new project.
    """
    # Ensure that ctx.obj exists and is a dict
    ctx.ensure_object(dict)
    
    # Store verbose flag in context
    ctx.obj['verbose'] = verbose
    
    # Get project path (default to current directory if not specified)
    project_path = (project_path or Path.cwd()).absolute()
    config_file = project_path / '.textcase.yml'
    
    # Always ensure VFS is available for all commands
    vfs = get_default_vfs()
    ctx.obj['vfs'] = vfs
    
    # Special handling for create command - it can work without a valid project
    if ctx.invoked_subcommand == 'create':
        # For create command, only try to load project if it exists
        if config_file.exists():
            try:
                project = create_project(project_path)
                ctx.obj['project'] = project
            except Exception as e:
                # Just log the error but continue - create command will handle this
                click.echo(f"Warning: Could not load existing project: {e}", err=True)
        
        # Always continue to the create command
        return
    
    # For all other commands, require a valid project
    if not config_file.exists():
        click.echo(f"Error: No .textcase.yml found in {project_path}", err=True)
        click.echo("\nTo create a new project, run:")
        click.echo(f"  tse create {project_path}")
        ctx.exit(1)
    
    try:
        # Load existing project
        project = create_project(project_path)
        
        # Verify the project has a valid config
        if not hasattr(project, 'config') or not project.config:
            click.echo(f"Error: Invalid project configuration in {project_path}", err=True)
            ctx.exit(1)
            
        ctx.obj['project'] = project
        
    except Exception as e:
        click.echo(f"Error loading project: {e}", err=True)
        ctx.exit(1)
    
    # If no command is provided, show help
    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help())
        
cli.add_command(create)
cli.add_command(edit)
cli.add_command(link)
cli.add_command(unlink)
cli.add_command(clear)
cli.add_command(archive)

def main():
    """Entry point for the CLI."""
    cli(obj={})
