"""Markdown document item implementation for textcase."""

from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple, Union
import frontmatter

from .module_item import FileDocumentItem
from ..protocol.module import CaseItem
from .markdown_ast import parse_markdown, RootNode, HeadingNode, ListNode, SectionNode


class MarkdownItem(FileDocumentItem):
    """Represents a Markdown document item stored in the filesystem.
    
    This class extends FileDocumentItem to provide Markdown-specific functionality,
    such as creating links between documents using YAML frontmatter.
    
    Args:
        id: The unique identifier for the document
        prefix: The prefix for the document (e.g., 'REQ')
        settings: Optional settings dictionary containing formatting options
        path: Optional path to the markdown file
    """

            
    _id: str
    _prefix: str
    settings: Dict[str, Any]
    _path: Optional[Path] = None
    
    def __init__(self, id: str, prefix: str, settings: Dict[str, Any] = None, path: Optional[Path] = None):
        """Initialize the markdown item."""
        super().__init__(id=id, prefix=prefix, settings=settings or {})
        self._path = path
    
    @property
    def path(self) -> Optional[Path]:
        """Get the path to the markdown file."""
        return self._path
    
    @path.setter
    def path(self, value: Path):
        """Set the path to the markdown file."""
        self._path = value
    
    def make_link(self, target: CaseItem, label: Optional[str] = None, region: Optional[str] = None) -> bool:
        """Create a link from this document to the target document.
        
        Args:
            target: The target CaseItem to link to
            label: Optional label for the link
            region: Optional region where to create the link (e.g., "frontmatter", "content")

        Returns:
            True if the link was successfully created, False otherwise
        """
        if region is None and label is None:
            # 如果没有给出具体的 label ( 即没有给出在 markdown 文件中的位置 )
            # 则默认在 frontmatter 中创建 link
            region = 'frontmatter'
        
        if region in ['frontmatter', 'meta']:
            # 如果明确给出了是在 meta | frontmatter 中创建 link
            return self.make_link_frontmatter(target, label)
        
        # 
        return self.make_link_markdown(target, region, label)
    
    def make_link_frontmatter(self, target: CaseItem, label: Optional[str] = None) -> bool:
        """Create a link from this document to the target document.
        
        This method adds a link to the YAML frontmatter of the markdown file.
        Links are stored in the format:
        
        links:
          target_key:
            - label1
            - label2
        
        Args:
            target: The target CaseItem to link to
            label: Optional label for the link, defaults to target's key
            
        Returns:
            True if the link was successfully created, False otherwise
            
        Raises:
            ValueError: If the document path is not set
            FileNotFoundError: If the document file does not exist
        """
        if not self._path:
            raise ValueError(f"Document path not set for {self.key}")
        
        if not self._path.exists():
            raise FileNotFoundError(f"Document {self.key} not found at {self._path}")
        
        # Read the file with frontmatter
        post = frontmatter.load(self._path)
        
        # Initialize links dictionary if it doesn't exist
        if 'links' not in post.metadata:
            post.metadata['links'] = {}
        
        # Initialize the target's label list if it doesn't exist
        if target.key not in post.metadata['links']:
            post.metadata['links'][target.key] = []
        
        # If this is the first link to this target
        if target.key not in post.metadata['links']:
            # If no label is provided, store as empty list
            if label is None or label == '':
                post.metadata['links'][target.key] = []
            else:
                post.metadata['links'][target.key] = [label]
        else:
            # If we already have links to this target
            if label is not None and label != '':
                # Add the label if it doesn't exist
                if label not in post.metadata['links'][target.key]:
                    post.metadata['links'][target.key].append(label)
            
            # Write the updated frontmatter and content back to the file
            # 检查 frontmatter 是否为空，如果为空则不保存 frontmatter 部分
            if not post.metadata or post.metadata == {}:
                # 如果 frontmatter 为空，直接写入内容
                with open(self._path, 'w', encoding='utf-8') as f:
                    f.write(post.content)
            else:
                # 如果 frontmatter 不为空，使用 frontmatter 库保存
                frontmatter.dump(post, self._path)
            return True
        
        return False  # Link already exists
    
    def make_link_markdown(self, target: CaseItem, region: str, label: Optional[str] = None) -> bool:
        """Create a link from this document to the target document in a specific region.
        
        Args:
            target: The target CaseItem to link to
            region: Region path in format "Head1/Head2/..." to locate where to add the link
            label: Optional label for the link
        
        Returns:
            True if the link was successfully created, False otherwise
            
        Raises:
            ValueError: If the document path is not set
            FileNotFoundError: If the document file does not exist
        """
        if not self._path:
            raise ValueError(f"Document path not set for {self.key}")
            
        if not self._path.exists():
            raise FileNotFoundError(f"Document {self.key} not found at {self._path}")
            
        # Read the file content
        with open(self._path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        # Parse frontmatter and get content
        post = frontmatter.loads(content)
        markdown_content = post.content
        
        # Parse the markdown to get AST
        ast = parse_markdown(markdown_content, debug=True)
        
        # Split the region path
        if region:
            region_parts = [part.strip() for part in region.split('/')]
        else:
            # Default to "Task" if region is empty
            # region = "Task"
            region_parts = ["Task"]
            
        # Find the target heading based on region path
        target_heading = self._find_heading_by_path(ast, region_parts)
        
        if not target_heading:
            # If heading not found
            print(f"DEBUG: Heading not found for region path: {region_parts}")
            
            # Special case: If region is "Task" (default) and heading not found, append it
            if not region and len(region_parts) == 1 and region_parts[0] == "Task":
                print(f"DEBUG: Creating 'Task' heading at the end of the document")
                
                # Append the Task heading to the end of the document
                lines = markdown_content.splitlines()
                
                # Add an empty line before the heading if the document doesn't end with one
                if lines and lines[-1].strip():
                    lines.append("")
                    
                # Add the Task heading
                lines.append("## Task")
                
                # Add an empty line after the heading for the task list
                lines.append("")
                
                # Create a basic heading node for further processing
                target_heading = HeadingNode(text="Task", level=2, line=len(lines) - 2)
                
                # Update the markdown content
                markdown_content = '\n'.join(lines)
                
                # Re-parse the AST with the new heading
                ast = parse_markdown(markdown_content, debug=True)
            else:
                # For other regions, return False if heading not found
                return False
            
        # Generate the link text (without task list marker)
        link_text = f"[{target.key}]({target.path.name}) {label or ''}".rstrip()
        
        # Insert the task list item
        lines = markdown_content.splitlines()
        
        # Find the heading line number
        heading_line = target_heading.line
        
        # Find the actual heading line in the file
        actual_heading_line = self._find_actual_heading_line(lines, target_heading)
        if actual_heading_line == -1:
            actual_heading_line = heading_line
            print(f"DEBUG: Using token-based heading line: {actual_heading_line}")
        else:
            print(f"DEBUG: Found actual heading line: {actual_heading_line}")
        
        # Find task list associated with the heading
        task_list = self._find_task_list_for_heading(ast, target_heading)
        
        if task_list:
            # Found an existing task list, check if target already exists
            target_exists = False
            target_key = target.key
            target_path_name = target.path.name
            
            print(f"DEBUG: Checking for existing link to {target_key} in task list with {len(task_list.children)} items")
            
            # Check each list item to see if it contains a link to the target
            for idx, item in enumerate(task_list.children):
                print(f"DEBUG: Checking list item {idx}: {item.content}")
                
                # Direct content check - this is the most reliable method
                exact_link_pattern = f"[{target_key}]({target_path_name})"
                if exact_link_pattern in item.content:
                    print(f"DEBUG: Found exact link match '{exact_link_pattern}' in item content: '{item.content}'")
                    target_exists = True
                    break
                
                # Check links extracted by the parser
                if hasattr(item, 'links') and item.links:
                    print(f"DEBUG: Item has {len(item.links)} links")
                    for link in item.links:
                        print(f"DEBUG: Found link - URL: {link.url}, Text: {link.text}")
                        print(f"DEBUG: Target key: {target_key}, Target path name: {target_path_name}")
                        # Compare both text and URL for matches
                        if link.url == target_path_name:
                            print(f"DEBUG: Target {target_key} already exists in task list, skipping")
                            target_exists = True
                            break
            
            if target_exists:
                # Target already exists, don't add it again
                print(f"DEBUG: Skipping link creation as target {target_key} already exists in the task list")
                return True
            
            # Target doesn't exist, add to the end of the task list
            position = task_list.end_line
            
            # Handle the case where end_line is not properly set
            if position <= 0 or position >= len(lines):
                # Calculate a reasonable position based on the last item in the list
                if task_list.children:
                    # Find the line of the last item and add 1
                    last_item_line = max(child.line for child in task_list.children if hasattr(child, 'line'))
                    position = last_item_line + 1
                else:
                    # If no children, insert after the heading
                    position = actual_heading_line + 1
            
            print(f"DEBUG: Found existing task list, inserting at line: {position}")
            lines.insert(position, f"- [ ] {link_text}")
        else:
            # No task list found, create a new one right after the heading
            # Find the actual heading line in the file
            actual_heading_line = self._find_actual_heading_line(lines, target_heading)
            if actual_heading_line == -1:
                actual_heading_line = target_heading.line
                print(f"DEBUG: Using token-based heading line: {actual_heading_line}")
            else:
                print(f"DEBUG: Found actual heading line: {actual_heading_line}")
            
            # Find the best position to insert the task list
            # First check if there's any content after the heading
            has_content_after_heading = False
            content_end_line = actual_heading_line + 1
            
            # Find the end of the current section (next heading or end of file)
            section_end_line = len(lines)
            for i in range(actual_heading_line + 1, len(lines)):
                if lines[i].strip().startswith('#'):
                    section_end_line = i
                    break
            
            # Check if there's any non-empty content after the heading
            for i in range(actual_heading_line + 1, section_end_line):
                if lines[i].strip() and not lines[i].strip().startswith('- [ ]') and not lines[i].strip().startswith('- [x]'):
                    has_content_after_heading = True
                    content_end_line = i + 1
            
            # Determine the position to insert the task list
            if has_content_after_heading:
                # Insert after the content
                position = content_end_line
                print(f"DEBUG: Content found after heading, inserting task list after content at line: {position}")
            else:
                # Insert right after the heading
                position = actual_heading_line + 1
                print(f"DEBUG: No content after heading, inserting task list right after heading at line: {position}")
            
            # If the line at the insertion position is not empty and we're not at the end of the file,
            # add an empty line first
            if position < len(lines) and lines[position].strip():
                print(f"DEBUG: Adding empty line at insertion point: {position}")
                lines.insert(position, "")
                position += 1
            
            print(f"DEBUG: No task list found, creating new one at line: {position}")
            lines.insert(position, "")
            position += 1
            lines.insert(position, f"- [ ] {link_text}")
            
        # Reconstruct the markdown content
        post.content = '\n'.join(lines)
        
        # Write back to the file
        # 检查 frontmatter 是否为空，如果为空则不保存 frontmatter 部分
        if not post.metadata or post.metadata == {}:
            # 如果 frontmatter 为空，直接写入内容
            with open(self._path, 'w', encoding='utf-8') as f:
                f.write(post.content)
        else:
            # 如果 frontmatter 不为空，使用 frontmatter 库保存
            frontmatter.dump(post, self._path)
        
        return True
        
    def _find_heading_by_path(self, ast: RootNode, path_parts: List[str]) -> Optional[HeadingNode]:
        """Find a heading by its path.
        
        Args:
            ast: The AST root node
            path_parts: List of heading text parts to match
            
        Returns:
            The matching HeadingNode or None if not found
        """
        if not path_parts:
            return None
        
        # Collect all headings from the AST
        headings = []
        
        def collect_headings(node):
            if isinstance(node, HeadingNode):
                headings.append(node)
            for child in node.children:
                collect_headings(child)
        
        collect_headings(ast)
        
        # Debug output
        print(f"DEBUG: Looking for heading path: {path_parts}")
        print(f"DEBUG: Available headings: {[h.text for h in headings]}")
        
        # Convert all parts to lowercase for case-insensitive comparison
        path_parts_lower = [part.lower() for part in path_parts]
        
        # Find the first heading that matches the first part of the path
        current_heading = None
        for heading in headings:
            print(f"DEBUG: Comparing '{heading.text.lower()}' with '{path_parts_lower[0]}'")
            if heading.text.lower() == path_parts_lower[0]:
                current_heading = heading
                print(f"DEBUG: Found matching heading: {heading.text}")
                break
        
        if not current_heading or len(path_parts) == 1:
            print(f"DEBUG: Returning heading: {current_heading.text if current_heading else None}")
            return current_heading
        
        # For deeper paths, find headings with increasing levels
        current_level = current_heading.level
        current_line = current_heading.line
        path_index = 1
        
        while path_index < len(path_parts):
            # Find the next heading with the right level and text
            found = False
            for heading in headings:
                if (heading.line > current_line and 
                    heading.level > current_level and 
                    heading.text.lower() == path_parts_lower[path_index]):
                    current_heading = heading
                    current_level = heading.level
                    current_line = heading.line
                    path_index += 1
                    found = True
                    print(f"DEBUG: Found nested heading: {heading.text}")
                    break
            
            if not found:
                print(f"DEBUG: Could not find nested heading for: {path_parts_lower[path_index]}")
                return None
        
        print(f"DEBUG: Final heading found: {current_heading.text}")
        return current_heading
        
    def _find_task_list_position(self, content: str, heading: Dict[str, Any]) -> int:
        """Find the position to insert a task list item.
        
        Args:
            content: Markdown content
            heading: Heading dict from parse_markdown
            
        Returns:
            Line number to insert the task list item, or -1 if no task list found
        """
        lines = content.splitlines()
        heading_line = heading['line']
        heading_level = heading['level']
        
        # Find the end of the section (next heading of same or lower level)
        section_end = len(lines)
        for i in range(heading_line + 1, len(lines)):
            line = lines[i].strip()
            if line.startswith('#') and len(line) > 1 and line[1] != '#':
                # Count the number of # to determine heading level
                level_count = 0
                for char in line:
                    if char == '#':
                        level_count += 1
                    else:
                        break
                        
                if level_count <= heading_level:
                    section_end = i
                    break
                    
        # Look for existing task list items in the section
        task_list_end = -1
        for i in range(heading_line + 1, section_end):
            line = lines[i].strip()
            if line.startswith('- [ ]') or line.startswith('- [x]'):
                task_list_end = i + 1
                
        return task_list_end
        
    def _find_task_list_for_heading(self, ast: RootNode, heading: HeadingNode) -> Optional[ListNode]:
        """Find a task list that belongs to a specific heading.
        
        Args:
            ast: The AST root node
            heading: The heading to find task lists for
            
        Returns:
            The matching ListNode or None if not found
        """
        # Collect all task lists from the AST
        task_lists = []
        
        def collect_task_lists(node):
            if isinstance(node, ListNode) and node.list_type == 'task':
                task_lists.append(node)
            for child in node.children:
                collect_task_lists(child)
        
        collect_task_lists(ast)
        
        if not task_lists:
            return None
        
        # First check for task lists directly associated with this heading
        heading_line = heading.line
        heading_level = heading.level
        
        # Find the next heading of the same or higher level
        next_heading_line = float('inf')
        headings = []
        
        def collect_headings(node):
            if isinstance(node, HeadingNode):
                headings.append(node)
            for child in node.children:
                collect_headings(child)
        
        collect_headings(ast)
        
        for h in headings:
            if h.line > heading_line and h.level <= heading_level:
                next_heading_line = h.line
                break
        
        # Find task lists in this range
        section_task_lists = []
        for task_list in task_lists:
            if (task_list.start_line > heading_line and 
                task_list.start_line < next_heading_line):
                section_task_lists.append(task_list)
        
        # Return the first task list found, if any
        if section_task_lists:
            task_list = section_task_lists[0]
            
            # Ensure the task list has a valid end_line
            if task_list.end_line <= 0:
                # If we have children, set end_line to after the last child
                if task_list.children:
                    last_item_line = max(child.line for child in task_list.children if hasattr(child, 'line'))
                    task_list.end_line = last_item_line + 1
                else:
                    # If no children, set end_line to start_line + 1
                    task_list.end_line = task_list.start_line + 1
            
            return task_list
        
        return None

    def _find_actual_heading_line(self, lines: List[str], heading: HeadingNode) -> int:
        """Find the actual line number of a heading in the file.
        
        Args:
            lines: List of lines from the markdown content
            heading: The heading to find
            
        Returns:
            The actual line number or -1 if not found
        """
        # If the heading already has a valid line number, use it
        if heading.line >= 0 and heading.line < len(lines):
            return heading.line
        
        heading_text = heading.text
        heading_level = heading.level
        heading_prefix = '#' * heading_level
        
        # First try exact matching
        for i, line in enumerate(lines):
            if line.strip() == f"{heading_prefix} {heading_text}":
                return i
        
        # If exact matching fails, try looser matching
        for i, line in enumerate(lines):
            line_stripped = line.strip()
            if line_stripped.startswith(f"{heading_prefix} ") and heading_text in line_stripped:
                return i
        
        # If still not found, return -1
        return -1
        
    def get_links(self) -> Dict[str, List[str]]:
        """Get all links defined in this document.
        
        Returns:
            A dictionary mapping target keys to lists of labels.
            An empty list means the link exists but has no labels.
            
        Raises:
            ValueError: If the document path is not set
            FileNotFoundError: If the document file does not exist
        """
        ...

    def get_links_frontmatter(self) -> Dict[str, List[str]]:
        """Get all links defined in this document.
        
        Returns:
            A dictionary mapping target keys to lists of labels.
            An empty list means the link exists but has no labels.
            
        Raises:
            ValueError: If the document path is not set
            FileNotFoundError: If the document file does not exist
        """
        if not self._path:
            raise ValueError(f"Document path not set for {self.key}")
            
        if not self._path.exists():
            raise FileNotFoundError(f"Document {self.key} not found at {self._path}")
            
        try:
            # Read the file with frontmatter
            post = frontmatter.load(self._path)
            
            # Return the links dictionary or empty dict if not found
            links = post.metadata.get('links', {})
            
            # Convert all values to lists and handle empty lists properly
            result = {}
            for target, labels in links.items():
                if isinstance(labels, list):
                    # Filter out any empty strings if they exist
                    result[target] = [label for label in labels if label]
                else:
                    # Convert single value to list
                    result[target] = [labels] if labels else []
            
            return result
        except Exception as e:
            # If there's any error reading the file or parsing frontmatter,
            # return an empty dict
            print(f"Error reading links from {self._path}: {e}")
            return {}
