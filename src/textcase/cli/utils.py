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
"""Utility functions for CLI commands."""

import os
import shutil
import click
from pathlib import Path
from typing import List, Optional

from textcase.protocol.module import Module

def debug_echo(ctx: click.Context, message: str) -> None:
    """Echo a debug message only if verbose mode is enabled.
    
    Args:
        ctx: The Click context object.
        message: The message to echo.
    """
    if ctx.obj.get('verbose', False):
        click.echo(f"Debug: {message}")


def get_template_source_dir() -> Path:
    """
    Get the directory containing the default templates.
    
    Returns:
        Path to the templates directory
    """
    # Get the package directory
    current_file = Path(__file__)
    print(f"Current file: {current_file}")
    print(f"Current file absolute: {current_file.absolute()}")
    print(f"Current file dir: {current_file.parent}")
    print(f"Current file dir absolute: {current_file.parent.absolute()}")
    
    package_dir = current_file.parent.parent.parent
    print(f"Package dir: {package_dir}")
    print(f"Package dir absolute: {package_dir.absolute()}")
    
    # Templates are stored in the data/templates directory
    templates_dir = package_dir / "data" / "templates"
    print(f"Templates dir: {templates_dir}")
    print(f"Templates dir absolute: {templates_dir.absolute()}")
    print(f"Templates dir exists: {templates_dir.exists()}")
    
    return templates_dir


def copy_templates_to_project(module: Module, ctx=None) -> bool:
    """
    Copy the default templates to the project's .config/template directory.
    
    Args:
        module: The project module
        ctx: Optional Click context for debug output
        
    Returns:
        True if successful, False otherwise
    """
    # Get the source templates directory
    source_dir = get_template_source_dir()
    if not source_dir.exists() or not source_dir.is_dir():
        if ctx:
            debug_echo(ctx, f"Templates directory not found: {source_dir}")
        return False
        
    # Create the target directory
    target_dir = module.path / ".config" / "template"
    target_dir.mkdir(parents=True, exist_ok=True)
    
    # Copy all template files
    copied = 0
    for template_file in source_dir.iterdir():
        if template_file.is_file():
            target_file = target_dir / template_file.name
            if not target_file.exists():
                shutil.copy2(template_file, target_file)
                copied += 1
                if ctx:
                    debug_echo(ctx, f"Copied template: {template_file.name}")
    
    if ctx:
        debug_echo(ctx, f"Copied {copied} templates to {target_dir}")
    
    return True


def list_available_templates(module: Module) -> List[str]:
    """
    List the available templates in the project's .config/template directory.
    
    Args:
        module: The project module
        
    Returns:
        List of template names (without extensions)
    """
    template_dir = module.path / ".config" / "template"
    if not template_dir.exists() or not template_dir.is_dir():
        return []
        
    templates = []
    for template_file in template_dir.iterdir():
        if template_file.is_file():
            templates.append(template_file.stem)
            
    return templates
