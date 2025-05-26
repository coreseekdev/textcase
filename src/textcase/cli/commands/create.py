"""Create command implementation."""

import datetime
import click
from pathlib import Path
from typing import Optional, Dict, Any
import yaml

@click.command()
@click.argument('doc_type', type=click.Choice(['requirement', 'test', 'model'], case_sensitive=False))
@click.argument('name')
@click.option('--title', help='Document title (defaults to name if not provided)')
@click.pass_context
def create(ctx: click.Context, doc_type: str, name: str, title: Optional[str] = None):
    """Create a new document.
    
    Creates a new document of the specified type with the given name.
    """
    project = ctx.obj['project']
    vfs = ctx.obj['vfs']
    doc_title = title or name.replace('_', ' ').title()
    
    # Create a submodule for the document type if it doesn't exist
    try:
        doc_module = project.create_submodule(doc_type + 's')
    except Exception:
        doc_module = next((m for m in project.get_submodules() 
                         if m.path.name == doc_type + 's'), None)
    
    if not doc_module:
        click.echo(f"Error: Could not create or find module for {doc_type}s")
        return
    
    # Create document file
    doc_filename = f"{doc_module.config.settings.get('prefix', '')}{name}.md"
    doc_path = doc_module.path / doc_filename
    
    # Create document content
    doc_content = f"# {doc_title}\n\n"
    
    # Save document to disk
    with vfs.open(doc_path, 'w') as f:
        f.write(doc_content)
    
    # Add to module order and save
    doc_module.order.add_item(doc_path.relative_to(doc_module.path))
    project.save()
    
    click.echo(f"Created {doc_type} document: {doc_title}")
    click.echo(f"  Path: {doc_path}")
