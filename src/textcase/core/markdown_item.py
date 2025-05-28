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
        return False
    
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
            frontmatter.dump(post, self._path)
            return True
        
        return False  # Link already exists
    
    def make_link_markdown(self, target: CaseItem, label: Optional[str] = None) -> bool:
        """Create a link from this document to the target document.
        
        Args:
            target: The target CaseItem to link to
            label: Optional label for the link
        
        Returns:
            True if the link was successfully created, False otherwise
        """
        ...

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
