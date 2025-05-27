"""Migration utilities for Markdown documents in textcase."""

import argparse
from pathlib import Path
import re
import frontmatter
from typing import List, Dict, Any, Optional, Tuple


def migrate_markdown_file(file_path: Path) -> bool:
    """Migrate a markdown file to use YAML frontmatter for links.
    
    Args:
        file_path: Path to the markdown file to migrate
        
    Returns:
        True if the file was migrated, False otherwise
    """
    if not file_path.exists() or not file_path.is_file():
        print(f"Error: File {file_path} does not exist or is not a file")
        return False
        
    # Read the file content
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
        
    # Check if the file already has frontmatter
    has_frontmatter = content.startswith('---')
    
    # Extract links from the content
    links = []
    link_pattern = re.compile(r'^LINK:\s*(.+)$', re.MULTILINE)
    for match in link_pattern.finditer(content):
        target_key = match.group(1).strip()
        links.append({'target': target_key, 'label': target_key})
        
    if not links:
        # No links to migrate
        return False
        
    # Remove the link lines from the content
    cleaned_content = re.sub(r'^LINK:.*$\n?', '', content, flags=re.MULTILINE)
    cleaned_content = cleaned_content.rstrip() + '\n'
    
    if has_frontmatter:
        # Parse the existing frontmatter
        post = frontmatter.loads(content)
        
        # Add the links to the frontmatter
        if 'links' not in post.metadata:
            post.metadata['links'] = []
            
        # Add new links that don't already exist
        for link in links:
            if link not in post.metadata['links']:
                post.metadata['links'].append(link)
                
        # Set the content to the cleaned content
        post.content = cleaned_content
    else:
        # Create new frontmatter
        post = frontmatter.Post(
            cleaned_content,
            links=links
        )
        
    # Write the updated content back to the file
    frontmatter.dump(post, file_path)
    
    print(f"Migrated {file_path} - Added {len(links)} links to frontmatter")
    return True


def migrate_directory(directory_path: Path, recursive: bool = True) -> Tuple[int, int]:
    """Migrate all markdown files in a directory.
    
    Args:
        directory_path: Path to the directory to migrate
        recursive: Whether to recursively migrate subdirectories
        
    Returns:
        Tuple of (number of files processed, number of files migrated)
    """
    if not directory_path.exists() or not directory_path.is_dir():
        print(f"Error: Directory {directory_path} does not exist or is not a directory")
        return (0, 0)
        
    processed = 0
    migrated = 0
    
    # Process all markdown files in the directory
    for file_path in directory_path.glob('*.md'):
        processed += 1
        if migrate_markdown_file(file_path):
            migrated += 1
            
    # Recursively process subdirectories if requested
    if recursive:
        for subdir in directory_path.iterdir():
            if subdir.is_dir():
                sub_processed, sub_migrated = migrate_directory(subdir, recursive)
                processed += sub_processed
                migrated += sub_migrated
                
    return (processed, migrated)


def main():
    """Main entry point for the migration script."""
    parser = argparse.ArgumentParser(description='Migrate Markdown files to use YAML frontmatter for links')
    parser.add_argument('path', type=str, help='Path to a file or directory to migrate')
    parser.add_argument('--recursive', '-r', action='store_true', help='Recursively migrate subdirectories')
    
    args = parser.parse_args()
    path = Path(args.path)
    
    if path.is_file():
        if migrate_markdown_file(path):
            print(f"Successfully migrated file: {path}")
        else:
            print(f"No migration needed for file: {path}")
    elif path.is_dir():
        processed, migrated = migrate_directory(path, args.recursive)
        print(f"Migration complete: {migrated} of {processed} files migrated")
    else:
        print(f"Error: {path} is not a valid file or directory")
        return 1
        
    return 0


if __name__ == '__main__':
    exit(main())
