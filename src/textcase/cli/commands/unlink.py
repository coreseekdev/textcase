"""Unlink command implementation."""

import click

@click.command()
@click.argument('source')
@click.argument('target')
@click.pass_context
def unlink(ctx: click.Context, source: str, target: str):
    """Unlink two documents."""
    core = ctx.obj['core']
    # Implementation for unlinking documents
    click.echo(f"Unlinking {source} -/- {target}")
    # TODO: Implement actual unlinking logic
