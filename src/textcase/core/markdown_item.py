"""Markdown document item implementation for textcase."""

from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple, Union
import frontmatter
from markdown_it import MarkdownIt

from .module_item import FileDocumentItem
from ..protocol.module import CaseItem


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
    @staticmethod
    def parse_markdown(content: str) -> Dict[str, Any]:
        """Parse markdown content using MarkdownIt.
        
        Args:
            content: Markdown content to parse
            
        Returns:
            Dictionary with parsed information
        """
        md = MarkdownIt()
        tokens = md.parse(content)
        
        result = {
            'headings': [],
            'links': [],
            'images': [],
            'code_blocks': []
        }
        
        for token in tokens:
            if token.type == 'heading_open':
                # Get the heading level
                level = int(token.tag[1])  # h1 -> 1, h2 -> 2, etc.
                
                # Get the heading text from the next token
                if token.nesting == 1 and len(tokens) > token.map[0] + 1:
                    text_token = tokens[token.map[0] + 1]
                    if text_token.type == 'inline' and text_token.content:
                        result['headings'].append({
                            'level': level,
                            'text': text_token.content,
                            'line': token.map[0] + 1
                        })
            
            elif token.type == 'link_open':
                # Get the link URL
                href = token.attrs.get('href', '')
                
                # Get the link text from the next token
                if token.nesting == 1 and len(tokens) > token.map[0] + 1:
                    text_token = tokens[token.map[0] + 1]
                    if text_token.type == 'text' and text_token.content:
                        result['links'].append({
                            'url': href,
                            'text': text_token.content,
                            'line': token.map[0] + 1
                        })
            
            elif token.type == 'code_block' or token.type == 'fence':
                result['code_blocks'].append({
                    'content': token.content,
                    'info': token.info if hasattr(token, 'info') else '',
                    'line': token.map[0] + 1
                })
        
        return result
    
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
    
    def make_link(self, target: CaseItem, label: Optional[str] = None) -> bool:
        """Create a link from this document to the target document.
        
        This method adds a link to the YAML frontmatter of the markdown file.
        
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
        
        # Use the provided label or default to the target's key
        link_label = label or target.key
        
        # Read the file with frontmatter
        post = frontmatter.load(self._path)
        
        # Initialize links list if it doesn't exist
        if 'links' not in post.metadata:
            post.metadata['links'] = []
        
        # Add the new link if it doesn't already exist
        link_data = {'target': target.key, 'label': link_label}
        if link_data not in post.metadata['links']:
            post.metadata['links'].append(link_data)
            
            # Write the updated frontmatter and content back to the file
            frontmatter.dump(post, self._path)
            return True
        
        return False  # Link already exists
    
    def get_links(self) -> List[Tuple[str, str]]:
        """Get all links defined in this document.
        
        Returns:
            A list of tuples containing (target_key, label)
            
        Raises:
            ValueError: If the document path is not set
            FileNotFoundError: If the document file does not exist
        """
        if not self._path:
            raise ValueError(f"Document path not set for {self.key}")
        
        if not self._path.exists():
            raise FileNotFoundError(f"Document {self.key} not found at {self._path}")
        
        links = []
        
        # Read the file with frontmatter
        post = frontmatter.load(self._path)
        
        # Extract links from frontmatter
        if 'links' in post.metadata and isinstance(post.metadata['links'], list):
            for link_data in post.metadata['links']:
                if isinstance(link_data, dict) and 'target' in link_data:
                    target_key = link_data['target']
                    label = link_data.get('label', target_key)
                    links.append((target_key, label))
        
        # For backward compatibility, also check for old-style links in the content
        for line in post.content.splitlines():
            if line.startswith("LINK: "):
                target_key = line[6:].strip()  # Remove "LINK: " prefix
                # Add only if not already in the list
                if not any(target == target_key for target, _ in links):
                    links.append((target_key, target_key))
                
        return links

    def create_new_document(self, title: Optional[str] = None) -> bool:
        """Create a new markdown document with YAML frontmatter.
        
        Args:
            title: Optional title for the document, defaults to the item's key
            
        Returns:
            True if the document was created, False otherwise
            
        Raises:
            ValueError: If the document path is not set
        """
        if not self._path:
            raise ValueError(f"Document path not set for {self.key}")
        
        # Don't overwrite existing files
        if self._path.exists():
            return False
        
        # Ensure parent directory exists
        self._path.parent.mkdir(parents=True, exist_ok=True)
        
        # Create document with frontmatter
        post = frontmatter.Post(
            f"# {title or self.key}\n\n",  # Initial content with title
            links=[],  # Empty links list
            id=self.id,
            prefix=self.prefix
        )
        
        # Write to file
        frontmatter.dump(post, self._path)
        return True

