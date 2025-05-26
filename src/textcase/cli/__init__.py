"""CLI interface for TextCase."""

import click
from pathlib import Path
from typing import Optional

from ..core import LocalVFS, ProjectModule

# Import all command modules
from .commands.create import create
from .commands.edit import edit
from .commands.link import link
from .commands.unlink import unlink
from .commands.clear import clear
from .commands.archive import archive

@click.group(invoke_without_command=True)
@click.option('--project-path', '-p', type=click.Path(exists=True, file_okay=False, path_type=Path))
@click.pass_context
def cli(ctx: click.Context, project_path: Optional[Path] = None):
    """TextCase - A full-stack text-based CASE tool."""
    # Ensure that ctx.obj exists and is a dict
    ctx.ensure_object(dict)
    
    # Initialize VFS and project
    vfs = LocalVFS()
    project_path = project_path or Path.cwd()
    
    try:
        # Try to load existing project
        project = ProjectModule.load(project_path, vfs)
    except FileNotFoundError:
        # Or create a new one if it doesn't exist
        project = ProjectModule.create(
            path=project_path,
            vfs=vfs,
            settings={
                'digits': 3,
                'prefix': 'REQ',
                'sep': '',
                'default_tag': []
            }
        )
    
    ctx.obj['project'] = project
    ctx.obj['vfs'] = vfs
    
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
