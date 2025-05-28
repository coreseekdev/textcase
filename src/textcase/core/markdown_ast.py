"""Markdown AST (Abstract Syntax Tree) implementation for textcase.

This module provides functionality to parse Markdown content into a tree-based
structure that better represents the hierarchical nature of Markdown documents.
"""

from typing import Dict, Any, List, Optional, Union
from markdown_it import MarkdownIt


class MarkdownNode:
    """Base class for all nodes in the Markdown AST."""
    
    def __init__(self, node_type: str, line: int = -1):
        self.type = node_type
        self.line = line
        self.children = []
        
    def add_child(self, child: 'MarkdownNode'):
        """Add a child node to this node."""
        self.children.append(child)
        return child
        
    def to_dict(self) -> Dict[str, Any]:
        """Convert the node to a dictionary representation."""
        result = {
            'type': self.type,
            'line': self.line,
        }
        if self.children:
            result['children'] = [child.to_dict() for child in self.children]
        return result


class RootNode(MarkdownNode):
    """Root node of the Markdown AST."""
    
    def __init__(self):
        super().__init__('root', 0)
        # Additional metadata about the document
        self.metadata = {}


class HeadingNode(MarkdownNode):
    """Node representing a heading in Markdown."""
    
    def __init__(self, level: int, text: str, line: int, token_index: int = -1):
        super().__init__('heading', line)
        self.level = level
        self.text = text
        self.token_index = token_index
        
    def to_dict(self) -> Dict[str, Any]:
        """Convert the node to a dictionary representation."""
        result = super().to_dict()
        result.update({
            'level': self.level,
            'text': self.text,
            'token_index': self.token_index
        })
        return result


class SectionNode(MarkdownNode):
    """Node representing a section in Markdown (a heading and its content)."""
    
    def __init__(self, heading: HeadingNode, start_line: int, end_line: int):
        super().__init__('section', heading.line)
        self.heading = heading
        self.start_line = start_line
        self.end_line = end_line
        self.add_child(heading)
        
    def to_dict(self) -> Dict[str, Any]:
        """Convert the node to a dictionary representation."""
        result = super().to_dict()
        result.update({
            'heading': self.heading.to_dict(),
            'start_line': self.start_line,
            'end_line': self.end_line
        })
        return result


class ListNode(MarkdownNode):
    """Node representing a list in Markdown."""
    
    def __init__(self, list_type: str, start_line: int, end_line: int = -1):
        super().__init__('list', start_line)
        self.list_type = list_type  # 'bullet', 'ordered', 'task'
        self.start_line = start_line
        self.end_line = end_line
        
    def to_dict(self) -> Dict[str, Any]:
        """Convert the node to a dictionary representation."""
        result = super().to_dict()
        result.update({
            'list_type': self.list_type,
            'start_line': self.start_line,
            'end_line': self.end_line
        })
        return result


class ListItemNode(MarkdownNode):
    """Node representing a list item in Markdown."""
    
    def __init__(self, text: str, line: int, is_task: bool = False, is_checked: bool = False):
        super().__init__('list_item', line)
        self.text = text
        self.is_task = is_task
        self.is_checked = is_checked if is_task else False
        self.has_link = False
        self.link_url = ""
        self.link_text = ""
        
    def to_dict(self) -> Dict[str, Any]:
        """Convert the node to a dictionary representation."""
        result = super().to_dict()
        result.update({
            'text': self.text,
            'is_task': self.is_task,
            'is_checked': self.is_checked
        })
        if self.has_link:
            result.update({
                'has_link': self.has_link,
                'link_url': self.link_url,
                'link_text': self.link_text
            })
        return result


class LinkNode(MarkdownNode):
    """Node representing a link in Markdown."""
    
    def __init__(self, url: str, text: str, line: int):
        super().__init__('link', line)
        self.url = url
        self.text = text
        
    def to_dict(self) -> Dict[str, Any]:
        """Convert the node to a dictionary representation."""
        result = super().to_dict()
        result.update({
            'url': self.url,
            'text': self.text
        })
        return result


class ImageNode(MarkdownNode):
    """Node representing an image in Markdown."""
    
    def __init__(self, url: str, alt: str, line: int):
        super().__init__('image', line)
        self.url = url
        self.alt = alt
        
    def to_dict(self) -> Dict[str, Any]:
        """Convert the node to a dictionary representation."""
        result = super().to_dict()
        result.update({
            'url': self.url,
            'alt': self.alt
        })
        return result


class CodeBlockNode(MarkdownNode):
    """Node representing a code block in Markdown."""
    
    def __init__(self, content: str, language: str, line: int):
        super().__init__('code_block', line)
        self.content = content
        self.language = language
        
    def to_dict(self) -> Dict[str, Any]:
        """Convert the node to a dictionary representation."""
        result = super().to_dict()
        result.update({
            'content': self.content,
            'language': self.language
        })
        return result


def parse_markdown(content: str, debug: bool = False) -> RootNode:
    """Parse markdown content into an AST.
    
    Args:
        content: Markdown content to parse
        debug: Whether to print debug information
        
    Returns:
        A RootNode containing the parsed Markdown AST
    """
    md = MarkdownIt()
    tokens = md.parse(content)
    lines = content.splitlines()
    
    if debug:
        print("DEBUG: All tokens:")
        for idx, token in enumerate(tokens):
            print(f"DEBUG: Token {idx}: {token.type} - {token.tag if hasattr(token, 'tag') else 'no tag'} - {token.content if hasattr(token, 'content') and token.content else 'no content'}")
    
    # Create the root node
    root = RootNode()
    
    # First pass: collect all headings
    headings = []
    for i, token in enumerate(tokens):
        if token.type == 'heading_open':
            level = int(token.tag[1])  # h1 -> 1, h2 -> 2, etc.
            
            if i + 1 < len(tokens):
                text_token = tokens[i + 1]
                if text_token.type == 'inline' and text_token.content:
                    # Get the line number in the file
                    line_num = token.map[0] if hasattr(token, 'map') and token.map else -1
                    
                    # If no line number info, try to find the heading in the file
                    if line_num == -1:
                        for j, line in enumerate(lines):
                            if line.strip() == f"{'#' * level} {text_token.content}":
                                line_num = j
                                break
                    
                    heading = HeadingNode(level, text_token.content, line_num, i)
                    headings.append(heading)
                    if debug:
                        print(f"DEBUG: Found heading: level={level}, text={text_token.content}, line={line_num}")
    
    # Second pass: build sections
    sections = []
    for i, heading in enumerate(headings):
        # Determine the content range of the current heading
        start_line = heading.line
        end_line = len(lines)
        
        for next_heading in headings[i+1:]:  # Find the next heading
            if next_heading.level <= heading.level:
                end_line = next_heading.line
                break
        
        # Create a section node
        section = SectionNode(heading, start_line, end_line)
        sections.append(section)
        root.add_child(section)
        if debug:
            print(f"DEBUG: Section '{heading.text}' from line {start_line} to {end_line}")
    
    # Third pass: process lists and other elements
    current_list = None
    current_section = None
    in_task_list = False
    
    for i, token in enumerate(tokens):
        # Update current section based on headings
        if token.type == 'heading_open':
            for section in sections:
                if section.heading.token_index == i:
                    current_section = section
                    break
        
        # Process links
        elif token.type == 'link_open':
            href = token.attrs.get('href', '')
            
            if token.nesting == 1 and i + 1 < len(tokens):
                text_token = tokens[i + 1]
                if text_token.type == 'text' and text_token.content:
                    line_num = token.map[0] if hasattr(token, 'map') and token.map else -1
                    link = LinkNode(href, text_token.content, line_num)
                    
                    # Add to the current section if available
                    if current_section:
                        current_section.add_child(link)
                    else:
                        root.add_child(link)
        
        # Process code blocks
        elif token.type == 'code_block' or token.type == 'fence':
            line_num = token.map[0] if hasattr(token, 'map') and token.map else -1
            language = token.info if hasattr(token, 'info') else ''
            code_block = CodeBlockNode(token.content, language, line_num)
            
            # Add to the current section if available
            if current_section:
                current_section.add_child(code_block)
            else:
                root.add_child(code_block)
        
        # Process lists
        elif token.type == 'bullet_list_open' or token.type == 'ordered_list_open':
            list_type = 'bullet' if token.type == 'bullet_list_open' else 'ordered'
            line_num = token.map[0] if hasattr(token, 'map') and token.map else -1
            end_line = token.map[1] if hasattr(token, 'map') and token.map and len(token.map) > 1 else -1
            current_list = ListNode(list_type, line_num, end_line)
            
            # Add to the current section if available
            if current_section:
                current_section.add_child(current_list)
            else:
                root.add_child(current_list)
        
        # Process list items
        elif token.type == 'list_item_open' and current_list:
            item_start = token.map[0] if hasattr(token, 'map') and token.map else -1
            
            # Look for inline content
            for j in range(i + 1, min(i + 5, len(tokens))):
                if tokens[j].type == 'inline':
                    content = tokens[j].content.strip()
                    
                    # Check if it's a task list item
                    is_task = content.startswith('[ ] ') or content.startswith('[x] ')
                    is_checked = content.startswith('[x] ')
                    
                    if is_task:
                        # Mark the list as a task list
                        current_list.list_type = 'task'
                        in_task_list = True
                        
                        # Extract task text (remove task marker)
                        task_text = content[4:].strip()
                        
                        # Create list item node
                        list_item = ListItemNode(task_text, item_start, True, is_checked)
                        
                        # Check for links in the task item
                        if hasattr(tokens[j], 'children') and tokens[j].children:
                            has_link = False
                            link_url = ""
                            link_text = ""
                            
                            for child in tokens[j].children:
                                if child.type == 'link_open':
                                    has_link = True
                                    if 'href' in child.attrs:
                                        link_url = child.attrs['href']
                                elif child.type == 'text' and has_link:
                                    link_text = child.content
                            
                            if has_link:
                                list_item.has_link = True
                                list_item.link_url = link_url
                                list_item.link_text = link_text
                    else:
                        # Regular list item
                        list_item = ListItemNode(content, item_start)
                    
                    # Add to the current list
                    current_list.add_child(list_item)
                    break
        
        # Process list end
        elif (token.type == 'bullet_list_close' or token.type == 'ordered_list_close') and current_list:
            list_end = token.map[1] if hasattr(token, 'map') and token.map and len(token.map) > 1 else len(lines)
            current_list.end_line = list_end
            
            # If this is a task list, make sure it has a valid end_line
            if current_list.list_type == 'task' and current_list.end_line <= 0:
                # If we couldn't get the end line from the token map, calculate it based on the last item
                if current_list.children:
                    # Set end_line to the line after the last item
                    last_item_line = max(child.line for child in current_list.children if hasattr(child, 'line'))
                    current_list.end_line = last_item_line + 1
                else:
                    # Fallback to the current line if no children
                    current_list.end_line = token.map[0] + 1 if hasattr(token, 'map') and token.map else len(lines)
            
            # Reset current list
            current_list = None
            in_task_list = False
    
    return root


def ast_to_dict(ast: RootNode) -> Dict[str, Any]:
    """Convert an AST to a dictionary representation.
    
    This is useful for backward compatibility with code that expects
    the old dictionary-based representation.
    
    Args:
        ast: The AST to convert
        
    Returns:
        A dictionary representation of the AST
    """
    result = {
        'headings': [],
        'links': [],
        'images': [],
        'code_blocks': [],
        'sections': [],
        'list_blocks': [],
        'task_lists': []
    }
    
    # Helper function to recursively process nodes
    def process_node(node, parent_heading=None):
        if node.type == 'heading':
            result['headings'].append({
                'level': node.level,
                'text': node.text,
                'line': node.line,
                'token_index': node.token_index
            })
        elif node.type == 'section':
            result['sections'].append({
                'heading': {
                    'level': node.heading.level,
                    'text': node.heading.text,
                    'line': node.heading.line,
                    'token_index': node.heading.token_index
                },
                'start_line': node.start_line,
                'end_line': node.end_line,
                'content': []  # Would need actual content lines here
            })
            # Process children with this section's heading as parent
            for child in node.children:
                process_node(child, node.heading)
        elif node.type == 'link':
            result['links'].append({
                'url': node.url,
                'text': node.text,
                'line': node.line
            })
        elif node.type == 'image':
            result['images'].append({
                'url': node.url,
                'alt': node.alt,
                'line': node.line
            })
        elif node.type == 'code_block':
            result['code_blocks'].append({
                'content': node.content,
                'info': node.language,
                'line': node.line
            })
        elif node.type == 'list':
            list_data = {
                'start_line': node.start_line,
                'end_line': node.end_line,
                'items': []
            }
            
            # Add items
            for child in node.children:
                if child.type == 'list_item':
                    item_data = {
                        'text': child.text,
                        'line': child.line
                    }
                    
                    if child.is_task:
                        item_data['checked'] = child.is_checked
                        
                    if child.has_link:
                        item_data['has_link'] = True
                        item_data['link_url'] = child.link_url
                        item_data['link_text'] = child.link_text
                        
                    list_data['items'].append(item_data)
            
            # Add parent heading if available
            if parent_heading:
                list_data['parent_heading'] = {
                    'level': parent_heading.level,
                    'text': parent_heading.text,
                    'line': parent_heading.line,
                    'token_index': parent_heading.token_index
                }
            
            # Add to appropriate list based on type
            if node.list_type == 'task':
                result['task_lists'].append(list_data)
            else:
                result['list_blocks'].append(list_data)
        
        # Process children for non-section nodes
        if node.type != 'section':
            for child in node.children:
                process_node(child, parent_heading)
    
    # Process all root children
    for child in ast.children:
        process_node(child)
    
    return result
