#!/usr/bin/env python3
"""
Inspect markdown heading structure using tree-sitter.

This script loads a markdown file and prints its AST structure,
with a focus on heading nodes and their relationships.
"""

import sys
from tree_sitter import Language, Parser
from tree_sitter_languages import get_language

def print_node(node, indent=0, max_depth=5, current_depth=0):
    """Recursively print a node and its children with indentation."""
    if current_depth > max_depth:
        print("  " * indent + "...")
        return
        
    node_type = node.type
    node_text = node.text.decode('utf8', errors='replace')
    
    # Truncate long text for display
    if len(node_text) > 50:
        node_text = node_text[:47] + '...'
    
    # Print node info
    print(f"{'  ' * indent}{node_type} ({node.start_point[0]+1}:{node.start_point[1]}-{node.end_point[0]+1}:{node.end_point[1]})")
    print(f"{'  ' * (indent+1)}Text: {node_text!r}")
    
    # Print heading level if this is a heading
    if node_type == 'atx_heading':
        for child in node.children:
            if child.type == 'atx_heading_marker':
                heading_level = len(child.text.decode('utf8').strip())
                print(f"{'  ' * (indent+1)}Heading Level: {heading_level}")
    
    # Recursively print children
    if node.children:
        print(f"{'  ' * (indent+1)}Children:")
        for child in node.children:
            print_node(child, indent + 2, max_depth, current_depth + 1)

def main():
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} <markdown_file>")
        sys.exit(1)
    
    markdown_file = sys.argv[1]
    
    try:
        with open(markdown_file, 'rb') as f:
            content = f.read()
    except Exception as e:
        print(f"Error reading file: {e}")
        sys.exit(1)
    
    # Initialize parser with markdown language
    try:
        language = get_language('markdown')
    except Exception as e:
        print(f"Error loading markdown language: {e}")
        print("Make sure tree-sitter-markdown is installed.")
        sys.exit(1)
    
    parser = Parser()
    parser.set_language(language)
    
    # Parse the content
    tree = parser.parse(content)
    
    print(f"\n=== AST for {markdown_file} ===\n")
    print_node(tree.root_node)
    
    # Also print just the heading structure
    print("\n=== Heading Structure ===\n")
    
    # Query for all headings
    query = language.query("""
    (atx_heading
      (atx_heading_marker) @marker
      (heading_content) @heading) @heading_node
    """)
    
    captures = query.captures(tree.root_node)
    
    for node, name in captures:
        if name == 'heading_node':
            # Get heading level
            for child in node.children:
                if child.type == 'atx_heading_marker':
                    level = len(child.text.decode('utf8').strip())
                    break
            
            # Get heading text
            for child in node.children:
                if child.type == 'heading_content':
                    text = child.text.decode('utf8').strip()
                    break
            
            line = node.start_point[0] + 1
            print(f"{'  ' * (level-1)}L{level}: {text} (line {line})")

if __name__ == "__main__":
    main()
