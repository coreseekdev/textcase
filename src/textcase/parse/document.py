"""
文档抽象模块。

提供对解析后文档的抽象表示，封装语法树并提供查询接口。
"""

from typing import Any, Dict, List, Optional, Tuple, Union, Protocol
from collections.abc import Sequence

# 导入 tree-sitter 类型
from tree_sitter import Language, Node, Tree, Point
from .document_type import DocumentType

__all__ = ['Document', 'DocumentProtocol']


class DocumentProtocol(Protocol):
    """文档协议。
    
    定义文档对象的基本接口。
    """
    
    def query(self, query_string: str) -> dict[str, list[Node]]:
        """在文档中执行查询。"""
        ...
    
    def query_as_list(self, query_string: str) -> List[Tuple[str, Node]]:
        """在文档中执行查询，返回(捕获名, 节点)元组的列表。"""
        ...

    def get_root_node(self) -> Node:
        """获取文档的根节点。"""
        ...
        
    def get_text(self, start_point: Union[Point, Tuple[int, int], None] = None, end_point: Union[Point, Tuple[int, int], None] = None) -> str:
        """获取指定范围的文本。"""
        ...

    def get_bytes(self, start_byte: Optional[int] = None, end_byte: Optional[int] = None) -> bytes:
        """获取指定范围的字节数据。"""
        ...

    def replace_bytes(self, start_byte: int, end_byte: int, new_bytes: bytes = b'') -> bytes:
        """替换指定范围的字节数据。"""
        ...

    def update_content(self, new_bytes: bytes) -> None:
        """更新文档内容。"""
        ...

class Document(DocumentProtocol):
    """解析后的文档抽象。
    
    封装解析后的语法树，提供统一的查询接口。
    """
    
    def __init__(self, docType: DocumentType, tree: Tree, content: bytes):
        """初始化文档对象。
        
        Args:
            docType: 文档类型
            tree: 解析后的语法树
            content: 原始文本内容
        """
        self.tree = tree
        self.content = content
        self.language = docType.get_language()

    def query(self, query_string: str) -> dict[str, list[Node]]:
        """在文档中执行查询。
        
        Args:
            query_string: 查询字符串
            
        Returns:
            查询结果列表，每个结果包含节点信息和捕获名
        """
        # 执行查询
        if not self.language or not self.tree:
            return []

        query = self.language.query(query_string)
        return query.captures(self.tree.root_node)
        
    def query_as_list(self, query_string: str) -> List[Tuple[str, Node]]:
        """在文档中执行查询，返回(捕获名, 节点)元组的列表。
        
        这个方法返回原始的查询结果格式，方便后续处理。
        
        Args:
            query_string: 查询字符串
            
        Returns:
            包含(捕获名, 节点)元组的列表
        """
        if not self.language or not self.tree:
            return []
            
        query = self.language.query(query_string)
        captures = query.captures(self.tree.root_node)
        
        results = []
        for capture_name, nodes in captures.items():
            for node in nodes:
                results.append((capture_name, node))
                
        return results
        
    def get_root_node(self) -> Node:
        """获取文档的根节点。
        
        Returns:
            根节点对象
        """
        return self.tree.root_node if self.tree else None
        
    def get_text(self, start_point: Union[Point, Tuple[int, int], None] = None, end_point: Union[Point, Tuple[int, int], None] = None) -> str:
        """根据行列位置获取指定范围的文本。
        
        Args:
            start_point: 起始位置 (行, 列)，默认为文档开头
            end_point: 结束位置 (行, 列)，默认为文档结尾
            
        Returns:
            指定范围的文本
        """
        if not self.content:
            return ""
            
        if not start_point and not end_point:
            return self.content
        
        if isinstance(self.content, bytes):
            content = self.content.decode('utf-8')   # NOTE: 可能性能有影响，暂时不优化
        else:
            content = self.content
        
        # 将文本拆分为行
        lines = content.splitlines(True)
        
        # 默认值
        start_line = start_point[0] if start_point else 0
        start_col = start_point[1] if start_point else 0
        end_line = end_point[0] if end_point else len(lines) - 1
        end_col = end_point[1] if end_point else len(lines[end_line]) if end_line < len(lines) else 0
        
        # 确保行号在有效范围内
        start_line = max(0, min(start_line, len(lines) - 1))
        end_line = max(0, min(end_line, len(lines) - 1))
        
        # 提取文本
        if start_line == end_line:
            # 同一行内
            line = lines[start_line]
            return line[start_col:end_col]
        else:
            # 多行
            result = []
            # 第一行
            result.append(lines[start_line][start_col:])
            # 中间行
            for i in range(start_line + 1, end_line):
                result.append(lines[i])
            # 最后一行
            result.append(lines[end_line][:end_col])
            return "".join(result)
    
    def get_bytes(self, start_byte: Optional[int] = None, end_byte: Optional[int] = None) -> bytes:
        """根据字节范围获取指定范围的原始字节数据。
        
        Args:
            start_byte: 起始字节位置，默认为文档开头
            end_byte: 结束字节位置，默认为文档结尾
            
        Returns:
            指定范围的字节数据
        """
        if not self.content:
            return b""
            
        # 将内容转换为字节
        content_bytes = self.content if isinstance(self.content, bytes) else self.content.encode('utf-8')
            
        # 处理默认值
        if start_byte is None:
            start_byte = 0
        if end_byte is None:
            end_byte = len(content_bytes)
            
        # 确保字节范围有效
        start_byte = max(0, min(start_byte, len(content_bytes)))
        end_byte = max(0, min(end_byte, len(content_bytes)))
        
        # 直接返回字节范围
        return content_bytes[start_byte:end_byte]
        
    def replace_bytes(self, start_byte: int, end_byte: int, new_bytes: bytes = b'') -> bytes:
        """替换指定范围的字节数据。"""
        if not self.content:
            return
        
        # 将内容转换为字节
        content_bytes = self.content if isinstance(self.content, bytes) else self.content.encode('utf-8')
            
        # 确保字节范围有效
        start_byte = max(0, min(start_byte, len(content_bytes)))
        end_byte = max(0, min(end_byte, len(content_bytes)))
        
        # 替换字节范围
        return content_bytes[:start_byte] + new_bytes + content_bytes[end_byte:]

    def get_text_by_byte_range(self, start_byte: Optional[int] = None, end_byte: Optional[int] = None) -> str:
        """根据字节范围获取指定范围的文本。
        
        这是 get_bytes 的包装方法，将字节转换为文本。
        
        Args:
            start_byte: 起始字节位置，默认为文档开头
            end_byte: 结束字节位置，默认为文档结尾
            
        Returns:
            指定范围的文本
        """
        byte_data = self.get_bytes(start_byte, end_byte)
        return byte_data.decode('utf-8')

    def update_content(self, new_bytes: bytes) -> None:
        """更新文档内容。"""
        self.content = new_bytes