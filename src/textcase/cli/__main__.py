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
"""TextCase CLI entry point."""

import os
import sys
import click
from pathlib import Path
from typing import Optional

from textcase.textcase import TextCaseFactory

# Import commands
from textcase.cli.commands.add import add
from textcase.cli.commands.edit import edit
from textcase.cli.commands.create import create
from textcase.cli.commands.tag import tag
from textcase.cli.commands.clear import clear
from textcase.cli.commands.list import list_cmd
from textcase.cli.commands.config import config_cmd

__all__ = ['main']


@click.group()
@click.option('-p', '--project', default='.', help='Path to the project directory (default: current directory)')
@click.option('-c', '--config', help='Path to the configuration file')
@click.option('-v', '--verbose', count=True, help='Enable verbose output (use multiple times for higher verbosity: -v, -vv, -vvv)')
@click.pass_context
def cli(ctx: click.Context, project: str, config: Optional[str], verbose: int):
    """TextCase CLI - Manage your TextCase projects."""
    # Initialize context object
    ctx.ensure_object(dict)
    ctx.obj['verbose'] = verbose
    
    # Resolve project path
    project_path = Path(project).resolve()
    ctx.obj['project_path'] = project_path
    
    # Create TextCase factory with optional config file
    textcase_factory: TextCaseFactory = TextCaseFactory(config_file=config)
    ctx.obj['textcase_factory'] = textcase_factory
    
    # Special handling for 'create' command - don't require valid project unless --parent is used
    if ctx.invoked_subcommand == 'create':
        # Check if --parent option is being used by examining sys.argv
        # If --parent is used, we need an existing TextCase instance
        if '--parent' in sys.argv:
            # For create with --parent, we need an existing TextCase instance
            try:
                textcase = textcase_factory.get(str(project_path))
                ctx.obj['textcase'] = textcase
                
                if verbose >= 1:
                    click.echo(f"Using project at: {textcase.repo_root_path}")
                    if config:
                        click.echo(f"Using config file: {config}")
            except Exception as e:
                if verbose >= 1:
                    click.echo(f"Error initializing TextCase: {e}", err=True)
                    if verbose >= 3:
                        import traceback
                        click.echo(traceback.format_exc(), err=True)
                else:
                    click.echo("Error: Could not find a valid TextCase project. When using --parent, you must run the command from within an existing TextCase project.", err=True)
                ctx.exit(1)
        # For create without --parent, we'll create the TextCase instance on demand
        return
    
    # For all other commands, ensure we have a valid TextCase instance
    try:
        # Create TextCase instance using the factory
        textcase = textcase_factory.get(str(project_path))
        ctx.obj['textcase'] = textcase
        
        if verbose >= 1:
            click.echo(f"Using project at: {textcase.repo_root_path}")
            if config:
                click.echo(f"Using config file: {config}")
            if verbose >= 2:
                click.echo(f"Verbose level: {verbose}")
    except Exception as e:
        if verbose >= 1:
            click.echo(f"Error initializing TextCase: {e}", err=True)
            if verbose >= 3:
                import traceback
                click.echo(traceback.format_exc(), err=True)
        else:
            click.echo("Error: Could not find a valid TextCase project.", err=True)
            click.echo("Run 'textcase create' to create a new project.")
        
        # Exit for all commands except 'create'
        if ctx.invoked_subcommand != 'create':
            sys.exit(1)


# Register commands
cli.add_command(add)
cli.add_command(edit)
cli.add_command(create)
cli.add_command(tag)
cli.add_command(clear)
cli.add_command(list_cmd, name='list')
cli.add_command(config_cmd, name='config')


def main():
    """Entry point for the TextCase CLI."""
    try:
        cli()
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)

if __name__ == "__main__":
    main()