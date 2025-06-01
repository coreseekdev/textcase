#!/usr/bin/env python3
"""
Analyze markdown structure using the project's existing dependencies.
"""

import sys
from textcase.parse.parser import Parser
from textcase.parse.document_type import DocumentType

def print_heading_structure(parsed_doc):
    """Print the heading structure of a parsed markdown document."""
    # Simple query to get all nodes
    query = """
    (document) @document
    (atx_heading) @heading
    (paragraph) @paragraph
    """
    
    # Get the language from the document
    language = parsed_doc.language
    if not language:
        print("Error: Could not get language from document")
        return
    
    # Parse the query
    try:
        query = language.query(query)
    except Exception as e:
        print(f"Error parsing query: {e}")
        return
    
    # Execute the query
    captures = query.captures(parsed_doc.tree.root_node)
    
    print("\n=== Debug: All Captures ===\n")
    
    # In this project, captures is already a dictionary where:
    # - keys are capture names (strings)
    # - values are lists of nodes
    captures_dict = captures
    
    # Print all captures
    for name, nodes in captures_dict.items():
        for node in nodes:
            node_type = node.type
            node_text = node.text.decode('utf8', errors='replace')
            if len(node_text) > 40:
                node_text = node_text[:37] + '...'
            print(f"{name}: {node_type} - '{node_text}' at {node.start_point}->{node.end_point}")
    
    # Print captures by group
    print("\n=== Captures By Group ===\n")
    for capture_name, nodes in captures_dict.items():
        print(f"Capture name: {capture_name}")
        for node in nodes:
            node_text = node.text.decode('utf8', errors='replace')
            if len(node_text) > 40:
                node_text = node_text[:37] + '...'
            print(f"  - Node text: '{node_text}'")
            print(f"    Type: {node.type}")
            print(f"    Start: {node.start_point}, End: {node.end_point}")
    
    # Print the full AST for debugging 
    print("\n=== Debug: Full AST ===\n")
    
    def print_ast(node, indent=0, max_depth=10):
        if indent > max_depth:
            print(f"{'  ' * indent}... (max depth reached)")
            return
            
        node_type = node.type
        node_text = node.text.decode('utf8', errors='replace')
        if len(node_text) > 40:
            node_text = node_text[:37] + '...'
        
        print(f"{'  ' * indent}{node_type} - '{node_text}' at {node.start_point}->{node.end_point}")
        
        # Print all children recursively
        if hasattr(node, 'children') and node.children:
            for child in node.children:
                print_ast(child, indent + 2, max_depth)
    
    print_ast(parsed_doc.tree.root_node)
    
    # Now try to extract heading structure
    print("\n=== Markdown Heading Structure ===\n")
    
    def extract_headings(node, level=0):
        if node.type == 'atx_heading':
            # Get heading level
            heading_level = 1
            heading_text = ""
            for child in node.children:
                if child.type.startswith('atx_h') and child.type.endswith('_marker'):
                    heading_level = int(child.type[5])
                elif child.type == 'inline':
                    heading_text = child.text.decode('utf8').strip()
            
            indent = '  ' * (level + heading_level - 1)
            line = node.start_point[0] + 1
            print(f"{indent}H{heading_level}: {heading_text} (line {line})")
            return heading_level
        
        if hasattr(node, 'children'):
            for child in node.children:
                extract_headings(child, level)
    
    extract_headings(parsed_doc.tree.root_node)

def main():
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} <markdown_file>")
        sys.exit(1)
    
    markdown_file = sys.argv[1]
    
    try:
        # Read the file content
        with open(markdown_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Parse the markdown
        parser = Parser(document_type=DocumentType.MARKDOWN)
        parsed_doc = parser.parse(content)
        
        # Print the heading structure
        print_heading_structure(parsed_doc)
        
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
