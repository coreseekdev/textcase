"""Archive command implementation."""

import click
from pathlib import Path

@click.command()
@click.argument('doc_id')
@click.option('--archive-dir', type=click.Path(file_okay=False, dir_okay=True, path_type=Path), 
              default=Path('archived'), help='Archive directory')
@click.pass_context
def archive(ctx: click.Context, doc_id: str, archive_dir: Path):
    """Archive a document."""
    core = ctx.obj['core']
    # Implementation for archiving documents
    click.echo(f"Archiving {doc_id} to {archive_dir}")
    # TODO: Implement actual archiving logic
