"""
资源解析器模块，用于将资源引用 URI 转换为文档项。

定义了解析器协议和文档项基类，以及通用的 URI 解析功能。
支持解析 [@type:identifier](path#anchor) 格式的资源引用。
"""

import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Dict, List, Optional, Pattern, Protocol, Tuple, Any, Callable, TypeVar

from .document import DocumentProtocol

__all__ = [
    'Resolver',
    'ResolverProtocol',
    'DocumentItem',
    'ItemType',
]


class ItemType(Enum):
    """文档项类型枚举。"""
    NAME_SPACE = auto()   # 命名空间
    FUNCTION = auto()     # 函数
    CLASS = auto()        # 类
    METHOD = auto()       # 方法
    VARIABLE = auto()     # 变量
    EXPR = auto()         # 表达式
    IMPORT = auto()       # 导入语句
    INTERFACE = auto()    # 接口
    HEADING = auto()      # 标题
    PARAGRAPH = auto()    # 段落
    CODE_BLOCK = auto()   # 代码块
    LIST_ITEM = auto()    # 列表项
    LIST_BLOCK = auto()   # 列表块
    LINK = auto()         # 链接
    TEXT = auto()         # 文本
    TEXT_BLOCK = auto()   # 文本块
    SECTION = auto()      # 段落区域
    METADATA = auto()     # 元数据
    GENERIC = auto()      # 通用项


@dataclass
class DocumentItem:
    """文档项基类。
    
    表示文档中的一个结构化元素，如函数、类、标题等。
    支持嵌套结构，可以包含子项。
    """
    node_name: str                  # 节点名称，对应 tree-sitter 节点的名称，如果不是单一节点可为空
    item_type: ItemType            # 项目类型
    text: str                      # 项目文本表示
    start_point: Tuple[int, int]   # 起始位置（行，列）
    end_point: Tuple[int, int]     # 结束位置（行，列）
    metadata: Dict[str, Any] = field(default_factory=dict)  # 元数据
    children: List['DocumentItem'] = field(default_factory=list)  # 子项列表
    
    def __str__(self) -> str:
        """返回项目的字符串表示。"""
        name_display = self.node_name if self.node_name else f"<{self.item_type.name}>"
        return f"{name_display}: {self.text[:50]}{'...' if len(self.text) > 50 else ''}"
    
    def to_dict(self) -> Dict[str, Any]:
        """将项目转换为字典表示。"""
        result = {
            "node_name": self.node_name,
            "item_type": self.item_type.name,
            "text": self.text,
            "start_point": self.start_point,
            "end_point": self.end_point,
            "metadata": self.metadata
        }
        
        if self.children:
            result["children"] = [child.to_dict() for child in self.children]
            
        return result
    
    def add_child(self, child: 'DocumentItem') -> None:
        """添加子项。
        
        Args:
            child: 要添加的子项
        """
        self.children.append(child)
    
    def find_child_by_type(self, item_type: ItemType) -> List['DocumentItem']:
        """根据类型查找子项。
        
        Args:
            item_type: 要查找的项目类型
            
        Returns:
            符合类型的子项列表
        """
        return [child for child in self.children if child.item_type == item_type]
    
    def find_child_by_name(self, node_name: str) -> Optional['DocumentItem']:
        """根据节点名称查找子项。
        
        Args:
            node_name: 要查找的节点名称
            
        Returns:
            符合名称的子项，如果未找到则返回 None
        """
        for child in self.children:
            if child.node_name == node_name:
                return child
        return None


# 定义类型变量用于表示解析树
T = TypeVar('T')

class ResolverProtocol(Protocol):
    """资源解析器协议。
    
    定义了资源解析器的基本接口，用于将资源引用转换为文档项列表。
    """
    
    @abstractmethod
    def resolve(self, uri: str, parsed_document: DocumentProtocol) -> List[DocumentItem]:
        """将资源路径解析为文档项列表。
        
        Args:
            uri: 资源路径
            parsed_document: 已解析的文档对象
            
        Returns:
            解析后的文档项列表
            
        Raises:
            ValueError: 当资源路径格式不正确或不支持的资源类型时抛出
        """
        ...
        
    @abstractmethod
    def parse_uri(self, uri: str) -> Optional[Dict[str, str]]:
        """解析资源引用 URI。
        
        Args:
            uri: 资源引用 URI
            
        Returns:
            解析结果字典，如果解析失败则返回 None
        """
        ...
        
    @abstractmethod
    def uri_to_query(self, uri: str) -> str:
        """将资源引用 URI 转换为查询字符串。
        
        Args:
            uri: 资源引用 URI
            
        Returns:
            查询字符串
            
        Raises:
            ValueError: 当 URI 格式不正确或不支持的资源类型时抛出
        """
        ...


class Resolver(ABC, ResolverProtocol):
    """资源解析器基类。
    
    提供资源解析的通用实现，子类可以重写特定方法以提供特定语言的解析功能。
    """
    
    @abstractmethod
    def resolve(self, uri: str, parsed_document: DocumentProtocol) -> List[DocumentItem]:
        """将资源路径解析为文档项列表。
        
        Args:
            uri: 资源路径
            parsed_document: 已解析的文档对象
            
        Returns:
            解析后的文档项列表
            
        Raises:
            ValueError: 当资源路径格式不正确或不支持的资源类型时抛出
        """
        pass
        
    @abstractmethod
    def parse_uri(self, uri: str) -> Optional[Dict[str, str]]:
        """解析资源引用 URI。
        
        Args:
            uri: 资源引用 URI
            
        Returns:
            解析结果字典，如果解析失败则返回 None
        """
        pass
        
    @abstractmethod
    def uri_to_query(self, uri: str) -> str:
        """将资源引用 URI 转换为查询字符串。
        
        Args:
            uri: 资源引用 URI
            
        Returns:
            查询字符串
            
        Raises:
            ValueError: 当 URI 格式不正确或不支持的资源类型时抛出
        """
        pass

