"""
基于 tree-sitter 的文本解析器模块。

提供通用的文本解析能力，支持多种语言和文件类型。
解析器不直接进行文件 IO，需要调用者传入文件内容。
"""
import hashlib
from typing import Any, Dict, List, Optional, Protocol, Union

from tree_sitter import Language, Node, Parser as TSParser, Tree
from tree_sitter_language_pack import get_language

from .document import Document, DocumentProtocol
from .document_type import DocumentType

__all__ = ['Parser', 'ParserProtocol']

class ParserProtocol(Protocol):
    """解析器协议。
    
    定义了解析器的基本接口，用于将文本内容解析为文档对象。
    """
    
    def parse(self, content: Union[str, bytes]) -> DocumentProtocol:
        """解析文本内容，生成文档对象。
        
        Args:
            content: 要解析的文本内容，可以是字符串或字节
            
        Returns:
            解析后的文档对象
        """

class Parser(ParserProtocol):
    """基于 tree-sitter 的通用文本解析器。
    
    此解析器不直接进行文件 IO，需要调用者传入文件内容。
    可以根据文件扩展名自动选择合适的解析器，也支持手动指定解析器类型。
    """
    
    def __init__(self, document_type: Optional[Union[DocumentType, str]] = None, 
                 extension: Optional[str] = None, cache_size: int = 100):
        """初始化解析器。
        
        Args:
            document_type: 文档类型，可以是 DocumentType 枚举或字符串，如果为 None，则尝试从 extension 推断
            extension: 文件扩展名，用于在 document_type 为 None 时推断文档类型
            cache_size: 缓存大小，默认为100个解析结果
            
        Raises:
            ValueError: 当无法确定文档类型时抛出
        """
        if document_type is None and extension is None:
            raise ValueError("必须指定 document_type 或 extension 之一")
            
        if document_type is None:
            self.document_type = DocumentType.from_extension(extension)
        else:
            self.document_type = document_type
        
        if self.document_type == DocumentType.UNKNOWN:
            raise ValueError(f"无法为扩展名 {extension} 确定文档类型")
            
        # 初始化语言和解析器
        try:
            self.language = self.document_type.get_language()
            self.parser = self.document_type.get_parser()
        except Exception as e:
            raise ValueError(f"初始化解析器失败: {str(e)}")
    

    def parse(self, content: Union[str, bytes]) -> DocumentProtocol:
        """解析文本内容，生成文档对象。
        
        Args:
            content: 要解析的文本内容，可以是字符串或字节
            
        Returns:
            解析后的文档对象
        """
        
        # 未命中缓存，执行解析
        if isinstance(content, str):
            content_bytes = content.encode('utf-8')
        else:
            content_bytes = content
            content = content_bytes.decode('utf-8') if isinstance(content_bytes, bytes) else content
            
        tree = self.parser.parse(content_bytes)
        
        # 创建 Document 对象
        document = Document(self.document_type, tree, content)
        
        return document

    def reparse(self, new_content: bytes, document: Document) -> Tree:
        """重新解析文档。"""
        return self.parser.parse(new_content, document.tree)
