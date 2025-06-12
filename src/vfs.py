#!/usr/bin/env python
"""
VFS CLI tool for interacting with repository file systems.

This tool provides command-line access to the VFS (Virtual File System) functionality,
specifically using the RepoVFS implementation which combines local file system access
with git repository functionality.

Usage:
    python vfs.py <repo_path> <command> [args...]

Commands:
    ls <path>            - List contents of a directory
    get <path>           - Get file contents
    put <path> <content> - Write content to a file
"""

import argparse
import sys
import os
from pathlib import Path, PurePosixPath
import json

from textcase.core.vfs.repo_vfs import RepoVFS
from textcase.proto.service_vfs_protocol import EntryType


def cmd_ls(vfs, args):
    """List contents of a directory.
    
    Args:
        vfs: VFS instance
        args: Command line arguments
    """
    path = PurePosixPath(args.path)
    options = {}
    
    try:
        # Call the list method with the provided path
        entries = vfs.list(path, options)
        
        # Print the directory contents
        print(f"Contents of {args.path}:")
        for entry_path, entry_type in entries:
            # Format the output based on entry type
            if entry_type == EntryType.DIR:
                print(f"[DIR]  {entry_path}")
            else:
                print(f"[FILE] {entry_path}")
    except Exception as e:
        print(f"Error listing directory: {e}")
        return 1
    
    return 0


def cmd_get(vfs, args):
    """Get file contents.
    
    Args:
        vfs: VFS instance
        args: Command line arguments
    """
    path = PurePosixPath(args.path)
    
    try:
        # Get file contents as text
        content = vfs.get_text(path)
        if content is not None:
            print(content)
        else:
            print(f"Error: Could not read file {args.path}")
            return 1
    except Exception as e:
        print(f"Error reading file: {e}")
        return 1
    
    return 0


def cmd_put(vfs, args):
    """Put file contents.
    
    Args:
        vfs: VFS instance
        args: Command line arguments
    """
    path = PurePosixPath(args.path)
    content = args.content.encode('utf-8')  # Convert string to bytes
    
    try:
        # Write content to the file
        success = vfs.put(path, content, create_if_missing=True)
        if success:
            print(f"Successfully wrote to {args.path}")
        else:
            print(f"Error: Could not write to {args.path}")
            return 1
    except Exception as e:
        print(f"Error writing file: {e}")
        return 1
    
    return 0


def main():
    """Main entry point for the VFS CLI tool."""
    # Create the top-level parser
    parser = argparse.ArgumentParser(description="VFS CLI tool for interacting with repository file systems")
    parser.add_argument('repo_path', help="Path to the git repository")
    
    # Create subparsers for commands
    subparsers = parser.add_subparsers(dest='command', help="Command to execute")
    
    # ls command
    ls_parser = subparsers.add_parser('ls', help="List contents of a directory")
    ls_parser.add_argument('path', help="Directory path to list")
    
    # get command
    get_parser = subparsers.add_parser('get', help="Get file contents")
    get_parser.add_argument('path', help="File path to read")
    
    # put command
    put_parser = subparsers.add_parser('put', help="Write content to a file")
    put_parser.add_argument('path', help="File path to write")
    put_parser.add_argument('content', help="Content to write")
    
    # Parse arguments
    args = parser.parse_args()
    
    # Check if a command was provided
    if not args.command:
        parser.print_help()
        return 1
    
    # Initialize VFS
    try:
        vfs = RepoVFS(args.repo_path)
    except Exception as e:
        print(f"Error initializing VFS: {e}")
        return 1
    
    # Execute the appropriate command
    if args.command == 'ls':
        return cmd_ls(vfs, args)
    elif args.command == 'get':
        return cmd_get(vfs, args)
    elif args.command == 'put':
        return cmd_put(vfs, args)
    else:
        print(f"Unknown command: {args.command}")
        return 1


if __name__ == "__main__":
    sys.exit(main())