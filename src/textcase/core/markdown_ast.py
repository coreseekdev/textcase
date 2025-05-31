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
        self.metadata = {
            'frontmatter': {},
            'footnotes': {}
        }
        
    def add_frontmatter(self, data: Dict[str, Any]) -> None:
        """Add frontmatter data to the root node."""
        self.metadata['frontmatter'].update(data)
        
    def add_footnote(self, id: str, content: str, line: int, footnote_type: str = None, attributes: Dict[str, Any] = None) -> None:
        """Add a footnote to the root node.
        
        Args:
            id: The footnote ID (e.g., "^1")
            content: The full footnote content
            line: The line number where the footnote appears
            footnote_type: Optional type extracted from the footnote (e.g., "message", "function_call")
            attributes: Parsed attributes from the footnote
        """
        self.metadata['footnotes'][id] = {
            'content': content,
            'line': line,
            'type': footnote_type,
            'attributes': attributes or {}
        }


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
    
    def __init__(self, content: str, line: int = -1, is_task: bool = False, is_checked: bool = False):
        super().__init__('list_item', line)
        self.content = content
        self.is_task = is_task
        self.is_checked = is_checked
        self.links = []  # Will store LinkNode objects
        
        # Extract links from content if any
        self._extract_links_from_content()
        
    def _extract_links_from_content(self):
        """Extract links from the content using regex.
        Markdown link format: [text](url)
        """
        import re
        
        # Regular expression to match Markdown links: [text](url)
        link_pattern = r'\[([^\]]+)\]\(([^)]+)\)'
        
        # Find all links in the content
        matches = re.findall(link_pattern, self.content)
        
        # Create LinkNode objects for each match
        for text, url in matches:
            link_node = LinkNode(url, text, self.line)
            self.links.append(link_node)
            
        # Set convenience flags for backward compatibility
        self.has_link = len(self.links) > 0
        if self.has_link:
            self.link_url = self.links[0].url
            self.link_text = self.links[0].text
        
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


def process_metadata_tokens(tokens: List[Any], root: RootNode, debug: bool = False) -> None:
    """Process metadata tokens such as front matter and footnotes.
    
    Args:
        tokens: List of markdown-it tokens
        root: Root node of the AST
        debug: Whether to print debug information
        
    This function processes special tokens from the enabled plugins:
    - Front-Matter: Extracts YAML frontmatter data
    - Footnotes: Processes footnote references and definitions
    - Task Lists: Identifies task list items with checkboxes
    """
    import re
    
    # Regular expression for footnotes
    # Matches patterns like [^1]: [message] name="foo" timeout=30
    FOOTNOTE_PATTERN = re.compile(r'\[([\^\d]+)\]:\s*(?:\[([^\]]+)\])?\s*(.*)')
    
    # Regular expression for footnote attributes
    # Matches name="value" or name=value patterns
    FOOTNOTE_ATTR_PATTERN = re.compile(r'(\w+)=(?:"([^"]*)"|([^\s]*))')
    
    # Process front matter
    for token in tokens:
        # Front matter is stored in the meta property of the token
        if hasattr(token, 'meta') and token.meta:
            if debug:
                print(f"DEBUG: Found front matter: {token.meta}")
            root.add_frontmatter(token.meta)
        
        # Process footnote_reference tokens (from the footnote plugin)
        if token.type == 'footnote_reference':
            if debug:
                print(f"DEBUG: Found footnote reference: {token.content}")
        
        # Process footnote_anchor tokens (from the footnote plugin)
        if token.type == 'footnote_anchor':
            if debug:
                print(f"DEBUG: Found footnote anchor: {token.content}")
        
        # Process footnote_open tokens (from the footnote plugin)
        if token.type == 'footnote_open':
            if debug:
                print(f"DEBUG: Found footnote open: {token.content}")
        
        # Process inline tokens for custom footnote format
        if token.type == 'inline' and token.content and '[^' in token.content and ']:' in token.content:
            footnote_match = FOOTNOTE_PATTERN.match(token.content)
            if footnote_match:
                footnote_id = footnote_match.group(1)  # e.g., ^1
                footnote_type = footnote_match.group(2)  # e.g., message, function_call
                footnote_attrs_text = footnote_match.group(3)  # e.g., name="foo" timeout=30
                
                # Parse attributes
                attrs = {}
                for attr_match in FOOTNOTE_ATTR_PATTERN.finditer(footnote_attrs_text):
                    attr_name = attr_match.group(1)
                    # Use quoted value if available, otherwise use unquoted value
                    attr_value = attr_match.group(2) if attr_match.group(2) is not None else attr_match.group(3)
                    
                    # Convert special values
                    if attr_value.lower() == "true":
                        attr_value = True
                    elif attr_value.lower() == "false":
                        attr_value = False
                    elif attr_value.isdigit():
                        attr_value = int(attr_value)
                    elif attr_value.replace(".", "", 1).isdigit() and attr_value.count(".") == 1:
                        attr_value = float(attr_value)
                    
                    attrs[attr_name] = attr_value
                
                # Add footnote to root metadata
                line_num = token.map[0] if hasattr(token, 'map') and token.map else -1
                root.add_footnote(
                    id=footnote_id,
                    content=token.content,
                    line=line_num,
                    footnote_type=footnote_type,
                    attributes=attrs
                )
                
                if debug:
                    print(f"DEBUG: Found footnote: id={footnote_id}, type={footnote_type}, attrs={attrs}")


def parse_markdown(content: str, debug: bool = False) -> RootNode:
    """Parse markdown content into an AST.
    
    Args:
        content: Markdown content to parse
        debug: Whether to print debug information
        
    Returns:
        A RootNode containing the parsed Markdown AST
    """
    # Import plugins from mdit-py-plugins if available
    try:
        from mdit_py_plugins.front_matter import front_matter_plugin
        from mdit_py_plugins.footnote import footnote_plugin
        from mdit_py_plugins.tasklists import tasklists_plugin
        
        # Initialize MarkdownIt with plugins
        md = MarkdownIt()
        md.use(front_matter_plugin)
        md.use(footnote_plugin)
        md.use(tasklists_plugin)
        
        if debug:
            print("DEBUG: Using mdit-py-plugins for enhanced parsing")
    except ImportError:
        # Fallback to basic MarkdownIt if plugins are not available
        md = MarkdownIt()
        if debug:
            print("DEBUG: mdit-py-plugins not available, using basic parser")
    
    tokens = md.parse(content)
    lines = content.splitlines()
    
    if debug:
        print("DEBUG: All tokens:")
        for idx, token in enumerate(tokens):
            print(f"DEBUG: Token {idx}: {token.type} - {token.tag if hasattr(token, 'tag') else 'no tag'} - {token.content if hasattr(token, 'content') and token.content else 'no content'}")
    
    # Create the root node
    root = RootNode()
    
    # Process front matter and footnotes from tokens
    process_metadata_tokens(tokens, root, debug)
    
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
                    inline_token = tokens[j]
                    content = inline_token.content.strip()
                    children = inline_token.children if hasattr(inline_token, 'children') else []
                    
                    # Check if it's a task list item by examining children
                    is_task = False
                    is_checked = False
                    task_text = content
                    
                    # First try to detect task list items using children
                    if children:
                        # Look for checkbox pattern in the first child
                        for child_idx, child in enumerate(children):
                            if child.type == 'text' and child.content.strip().startswith('[ ]'):
                                is_task = True
                                is_checked = False
                                # Extract task text from this and subsequent children
                                task_text = child.content.strip()[4:].strip()
                                break
                            elif child.type == 'text' and child.content.strip().startswith('[x]'):
                                is_task = True
                                is_checked = True
                                # Extract task text from this and subsequent children
                                task_text = child.content.strip()[4:].strip()
                                break
                    
                    # Fallback to content-based detection if children approach didn't work
                    if not is_task and (content.startswith('[ ] ') or content.startswith('[x] ')):
                        is_task = True
                        is_checked = content.startswith('[x] ')
                        task_text = content[4:].strip()
                    
                    if is_task:
                        # Mark the list as a task list
                        current_list.list_type = 'task'
                        in_task_list = True
                        
                        # Create list item node
                        list_item = ListItemNode(task_text, item_start, True, is_checked)
                    else:
                        # Regular list item
                        list_item = ListItemNode(content, item_start, False, False)
                    
                    # Process links in the task item by examining children
                    if children:  
                        current_link = None
                        link_text_buffer = ""
                        
                        # Scan through children to find links
                        for child_idx, child in enumerate(children):
                            if child.type == 'link_open':
                                # Start of a new link
                                current_link = {
                                    'url': child.attrs.get('href', ''),
                                    'text': ''
                                }
                            elif child.type == 'link_close' and current_link:
                                # End of a link, create a LinkNode
                                current_link['text'] = link_text_buffer.strip()
                                link_node = LinkNode(current_link['url'], current_link['text'], item_start)
                                list_item.links.append(link_node)
                                
                                # Reset for next link
                                link_text_buffer = ""
                                current_link = None
                            elif child.type == 'text' and current_link is not None:
                                # Collecting text inside a link
                                link_text_buffer += child.content
                        
                        # Set convenience properties for backward compatibility
                        if list_item.links:
                            list_item.has_link = True
                            list_item.link_url = list_item.links[0].url
                            list_item.link_text = list_item.links[0].text
                    
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

