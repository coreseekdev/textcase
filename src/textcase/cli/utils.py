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
"""Utility functions for TextCase CLI."""

import os
import re
import click
from pathlib import Path
from typing import Optional, Tuple, Dict, Any, List


def debug_echo(ctx: click.Context, message: str) -> None:
    """Print a debug message if verbose mode is enabled.
    
    Args:
        ctx: Click context
        message: Message to print
    """
    if ctx.obj.get('verbose', False):
        click.echo(f"DEBUG: {message}")


def parse_key_value_string(kv_string: str) -> Dict[str, str]:
    """Parse a key-value string in the format key1=value1,key2=value2.
    
    Args:
        kv_string: String in the format key1=value1,key2=value2
        
    Returns:
        Dictionary of key-value pairs
    """
    result = {}
    if not kv_string:
        return result
        
    pairs = kv_string.split(',')
    for pair in pairs:
        if '=' in pair:
            key, value = pair.split('=', 1)
            result[key.strip()] = value.strip()
        else:
            # If no value is provided, use an empty string
            result[pair.strip()] = ""
            
    return result


def find_collection_for_path(resource_manager, file_path: Path) -> Tuple[Any, str]:
    """Find the collection that contains the given file path.
    
    Args:
        resource_manager: Resource collection manager
        file_path: Path to the file
        
    Returns:
        Tuple of (collection, relative_path)
    """
    # TODO: Implement finding the collection for a path
    # For now, return None
    return None, str(file_path)


def get_item_from_path(collection, item_path: str) -> Any:
    """Get a resource item from a path.
    
    Args:
        collection: Resource collection
        item_path: Path to the item, relative to the collection
        
    Returns:
        Resource item
    """
    # TODO: Implement getting an item from a path
    # For now, return None
    return None