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
"""Item listing functions for the list command."""

import click
from pathlib import Path
from typing import Optional, List, Dict, Any

from textcase.protocol.module import DocumentCaseItem
from textcase.cli.utils import debug_echo


def list_item_details(item: DocumentCaseItem, ctx: click.Context) -> None:
    """
    List details of a specific item.
    
    Args:
        item: The item to show details for
        ctx: Click context for debug output
    """
    if not item:
        click.echo("Error: Item not found", err=True)
        return
        
    # Get the item's key
    key = item.key() if hasattr(item, 'key') else "Unknown"
    
    # Display the item details
    click.echo(f"Item: {key}")
    
    # Display the item's path if available
    if hasattr(item, 'path') and item.path:
        click.echo(f"Path: {item.path}")
        
    # Display the item's links if available
    if hasattr(item, 'get_links'):
        links = item.get_links()
        if links:
            click.echo("Links:")
            for target, labels in links.items():
                for label in labels:
                    click.echo(f"  - {target}: {label}")
        else:
            click.echo("No links found")
            
    # Display the item's tags if available
    if hasattr(item, 'get_tags'):
        tags = item.get_tags()
        if tags:
            click.echo("Tags:")
            for tag in sorted(tags):
                click.echo(f"  - {tag}")
        else:
            click.echo("No tags found")
            
    # Try to get the title and content summary from the file
    if hasattr(item, 'path') and item.path and item.path.exists():
        try:
            click.echo("\nContent Summary:")
            with open(item.path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                
                # Find the title (first heading)
                title = None
                for line in lines:
                    line = line.strip()
                    if line.startswith('# '):
                        title = line[2:].strip()
                        click.echo(f"Title: {title}")
                        break
                
                # Show a brief content summary (first few non-empty lines)
                content_lines = [line.strip() for line in lines if line.strip() and not line.startswith('#')]
                if content_lines:
                    summary = content_lines[0]
                    if len(summary) > 80:
                        summary = summary[:77] + "..."
                    click.echo(f"Summary: {summary}")
                    
                    # Show total line count
                    click.echo(f"Total Lines: {len(lines)}")
        except Exception as e:
            if ctx.obj.get('verbose', False):
                debug_echo(ctx, f"Error reading item content: {e}")
            pass
