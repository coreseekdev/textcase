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

        if len(link_target_nodes) == 0:
            # "Region {region} not found in document {self.key}"
            # 说明需要手工创建 link 的容器，可能是 meta ，可能是 head
            # 需要对 region 进行额外的解析
            parts = resolver.parse_uri(region)
            if parts is None:
                raise ValueError(f"Invalid region: {region}")
            ptype, pvalue = parts[-1]
            if ptype == 'rtype' and pvalue == '#meta':
                # 尝试自动创建
                new_ctx = resolver.ensure_markdown_meta(parsed_document)
                if new_ctx:
                    new_tree = parser.reparse(new_ctx, parsed_document)
                    parsed_document.update_content(new_ctx, new_tree)
                    
                    link_target_nodes = resolver.resolve(region, parsed_document=parsed_document)
                
            # FIXME: 如果是 head ?

        if len(link_target_nodes) == 0:
            # 尝试自动创建，没有成功
            raise ValueError(f"Region {region} not found in document {self.key}")

        # 获取 target 节点
        target_node = link_target_nodes[0]

        new_content = target_node.make_link(target.key, label)
        if new_content:
            # update file , 理论上可以继续 reparse + update_content  更新document, 
            # 但是 add link 的目的已经完成，且目前的实现就是（在同一个文件）读取 + 写入
            # 因此，不额外处理。
            with open(self._path, 'wb') as f:
                f.write(new_content)
            return True
        return False
        