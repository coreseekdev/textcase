"""Markdown document item implementation for textcase."""

from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple, Union
import frontmatter

from .module_item import FileDocumentItem
from ..protocol.module import CaseItem
# from .markdown_ast import parse_markdown, RootNode, HeadingNode, ListNode, SectionNode


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
        self._content: Optional[bytes] = None
    
    @property
    def path(self) -> Optional[Path]:
        """Get the path to the markdown file."""
        return self._path
    
    @path.setter
    def path(self, value: Path):
        """Set the path to the markdown file."""
        self._path = value
    
    @property
    def content(self) -> bytes:
        """Get the content of the markdown file."""
        if self._content is None:
            with open(self._path, 'rb') as f:
                self._content = f.read()
        return self._content
    
    def make_link(self, target: CaseItem, label: Optional[str] = None, region: Optional[str] = None) -> bool:
        """Create a link from this document to the target document.
        
        Args:
            target: The target CaseItem to link to
            label: Optional label for the link
            region: Optional region where to create the link (e.g., "frontmatter", "content")

        Returns:
            True if the link was successfully created, False otherwise
        """
        
        if region is None:
            # 则默认在 frontmatter | meta 中创建 link
            region = '#meta'
        
        if not self._path:
            raise ValueError(f"Document path not set for {self.key}")
            
        if not self._path.exists():
            raise FileNotFoundError(f"Document {self.key} not found at {self._path}")

        # 使用 Parser 解析文档
        from textcase.parse.parser import Parser
        from textcase.parse.document_type import DocumentType
        from textcase.parse.resolver_md import MarkdownResolver
        
        parser = Parser(document_type=DocumentType.MARKDOWN)
        parsed_document = parser.parse(self.content)
        resolver = MarkdownResolver()

        # 解析 frontmatter 节点
        link_target_nodes = resolver.resolve(region, parsed_document=parsed_document)
        
        
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
            target: 目标项
            label: 可选的链接标签
            
        Returns:
            True if the link was successfully created, False otherwise
        """
    
        

        
        if not frontmatter_nodes or len(frontmatter_nodes) == 0:
            # 如果没有找到 frontmatter 节点，创建一个新的
            # 使用 python-frontmatter 创建并保存
            # FIXME: 如果完全移除 python-frontmatter 后，这部分应改为基于字符串模板渲染
            post = frontmatter.loads(content)
            post.metadata['links'] = {target.key: [label] if label else []}
            frontmatter.dump(post, self._path)
            return True
        
        # 获取 frontmatter 节点
        fm_node = frontmatter_nodes[0]

        if fm_node.make_link(target.key, label):
            # update file
            with open(self._path, 'wb') as f:
                f.write(fm_node.document.get_bytes())
            return True
        return False
    
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
            
        raise NotImplementedError