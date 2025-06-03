"""
文档抽象模块。

提供对解析后文档的抽象表示，封装语法树并提供查询接口。
"""

from typing import Any, Dict, List, Optional, Tuple, Union, Protocol
from collections.abc import Sequence

# 导入 tree-sitter 类型
from tree_sitter import Language, Node, Parser, Tree, Point
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

    def update_content(self, new_bytes: bytes, parser: Parser) -> None:
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
        self._revision = 0
        self._docType = docType
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
        """替换指定范围的字节数据，并更新解析树。
        
        Args:
            start_byte: 起始字节位置
            end_byte: 结束字节位置
            new_bytes: 新的字节数据
            
        Returns:
            更新后的完整字节数据
        """
        if not self.content:
            return b''
        
        # 将内容转换为字节
        content_bytes = self.content if isinstance(self.content, bytes) else self.content.encode('utf-8')
            
        # 确保字节范围有效
        start_byte = max(0, min(start_byte, len(content_bytes)))
        end_byte = max(0, min(end_byte, len(content_bytes)))
        
        # 1. 获取受影响的节点
        affected_node = self.tree.root_node.descendant_for_byte_range(start_byte, end_byte)
        if not affected_node:
            affected_node = self.tree.root_node
        
        # 2. 计算行列位置
        # 计算起始位置的行列
        start_point = self._byte_to_point(content_bytes, start_byte)
        # 计算结束位置的行列
        old_end_point = self._byte_to_point(content_bytes, end_byte)
        
        # 3. 计算新文本的行列位置
        # 创建一个临时的字节数组，用于计算新的结束位置
        temp_content = content_bytes[:start_byte] + new_bytes
        new_end_point = self._byte_to_point(temp_content, len(temp_content))

        # 4. 更新内容
        new_content = content_bytes[:start_byte] + new_bytes + content_bytes[end_byte:]
        
        # 5. 构造 edit 请求，更新树
        self.tree.edit(
            start_byte=start_byte,
            old_end_byte=end_byte,
            new_end_byte=start_byte + len(new_bytes),
            start_point=start_point,
            old_end_point=old_end_point,
            new_end_point=new_end_point
        )
        
        # 返回新内容
        return new_content
        
    def _byte_to_point(self, content: bytes, byte_offset: int) -> tuple[int, int]:
        """将字节偏移转换为行列位置。
        
        Args:
            content: 字节内容
            byte_offset: 字节偏移
            
        Returns:
            (行, 列) 元组
        """
        # 确保偏移在有效范围内
        byte_offset = max(0, min(byte_offset, len(content)))
        
        # 如果偏移为0，直接返回(0,0)
        if byte_offset == 0:
            return (0, 0)
        
        # 截取到偏移位置的内容
        content_slice = content[:byte_offset]
        
        # 计算行数（换行符数量）
        line_count = content_slice.count(b'\n')
        
        # 如果没有换行符，列就是字节偏移
        if line_count == 0:
            return (0, byte_offset)
        
        # 找到最后一个换行符的位置
        last_newline = content_slice.rindex(b'\n')
        
        # 计算列（从最后一个换行符到偏移位置的字节数）
        column = byte_offset - last_newline - 1
        
        return (line_count, column)

    def get_text_by_byte_range(self, start_byte: Optional[int] = None, end_byte: Optional[int] = None) -> str:
        """Get text by byte range.
        
        This is a wrapper method for get_bytes that converts bytes to text.
        
        Args:
            start_byte: Start byte position, defaults to document start
            end_byte: End byte position, defaults to document end
            
        Returns:
            Text in the specified range
        """
        byte_data = self.get_bytes(start_byte, end_byte)
        return byte_data.decode('utf-8')

    def update_content(self, new_bytes: bytes, parser: Parser) -> None:
        """Update document content and reparse.
        
        Args:
            new_bytes: New document content in bytes format
        """

        self._revision += 1
        self.content = new_bytes
        self.tree = parser.reparse(new_bytes, self)
        # print("update_content", self._revision, self.content)
        """ # 不可以如此处理，因为某些语言的解析器未提供 如 sass.
        # Get current document type
        doc_type = None
        for dt in DocumentType:
            if dt.get_language() == self.language:
                doc_type = dt
                break
        """
        # 目前不需要做其他事情，因为到此时，tree 已经更新了