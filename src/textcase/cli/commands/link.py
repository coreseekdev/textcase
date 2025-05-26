"""Link command implementation."""

import click

@click.command()
@click.argument('source')
@click.argument('target')
@click.pass_context
def link(ctx: click.Context, source: str, target: str):
    """Link two documents."""
    core = ctx.obj['core']
    # Implementation for linking documents
    click.echo(f"Linking {source} -> {target}")
    # TODO: Implement actual linking logic
