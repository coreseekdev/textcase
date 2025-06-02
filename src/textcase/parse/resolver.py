"""
资源解析器模块，用于将资源引用 URI 转换为文档项。

定义了解析器协议和文档项基类，以及通用的 URI 解析功能。
支持解析 [@type:identifier](path#anchor) 格式的资源引用。
"""

import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Dict, List, Optional, Pattern, Protocol, Tuple, Any, Callable, TypeVar, Union
from dataclasses import dataclass, field

from .document import DocumentProtocol, Node

__all__ = [
    'Resolver',
    'ResolverProtocol',
    'SemanticNode',  # 更改名称以区分语义节点和tree-sitter节点
    'NodeType',      # 更改名称以更好地表达其作为节点类型的本质
]


class NodeType(Enum):
    """语义节点类型枚举。"""
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
class SemanticNode:
    """语义节点类。
    
    表示文档中的一个语义结构元素，如函数、类、标题等。
    建立在tree-sitter节点之上，添加了语义信息和层次结构。
    支持嵌套结构，可以包含子节点。
    可以通过扩展关联到多个tree-sitter节点。

    # 由于 目前 markdown 已经支持了 section ，是否还需要 SemanticNode 存在疑问。
    """

    node_type: NodeType            # 节点类型
    start_point: Tuple[int, int]   # 起始位置（行，列）
    end_point: Tuple[int, int]     # 结束位置（行，列）
    metadata: Dict[str, Any] = field(default_factory=dict)  # 元数据
    children: List['SemanticNode'] = field(default_factory=list)  # 子节点列表
    ts_nodes: List[Node] = field(default_factory=list)  # 关联的tree-sitter节点列表
    # ts_node_super: Optional[Node] = None  # 关联的tree-sitter节点, 当前的 Node 是这个节点一部分（且不是子节点）， 仅仅是片段
    
    def __str__(self) -> str:
        """返回节点的字符串表示。"""
        name_display = self.node_name if self.node_name else f"<{self.node_type.name}>"
        return f"{name_display}: {self.text[:50]}{'...' if len(self.text) > 50 else ''}"
    
    def to_dict(self) -> Dict[str, Any]:
        """将节点转换为字典表示。"""
        result = {
            "node_type": self.node_type.name,
            "text": self.text,
            "start_point": self.start_point,
            "end_point": self.end_point,
            "metadata": self.metadata,
            "ts_nodes_count": len(self.ts_nodes)
        }
        
        if self.children:
            result["children"] = [child.to_dict() for child in self.children]
            
        return result
    
    def add_child(self, child: 'SemanticNode') -> None:
        """添加子节点。
        
        Args:
            child: 要添加的子节点
        """
        self.children.append(child)
    
    def find_children_by_type(self, node_type: NodeType) -> List['SemanticNode']:
        """根据类型查找子节点。
        
        Args:
            node_type: 要查找的节点类型
            
        Returns:
            符合类型的子节点列表
        """
        return [child for child in self.children if child.node_type == node_type]
    
    def find_child_by_name(self, node_name: str) -> Optional['SemanticNode']:
        """根据节点名称查找子节点。
        
        Args:
            node_name: 要查找的节点名称
            
        Returns:
            符合名称的子节点，如果未找到则返回 None
        """
        for child in self.children:
            if child.node_name == node_name:
                return child
        return None
        
    def add_ts_node(self, node: Node) -> None:
        """添加关联的tree-sitter节点。
        
        Args:
            node: 要关联的tree-sitter节点
        """
        self.ts_nodes.append(node)
        
    def expand(self, node: Node) -> None:
        """扩展节点范围以包含指定的tree-sitter节点。
        
        扩展节点的范围（start_point和end_point），使其包含指定的tree-sitter节点。
        同时将该节点添加到关联的tree-sitter节点列表中。
        
        Args:
            node: 要包含的tree-sitter节点
        """
        self.add_ts_node(node)
        
        # 更新起始位置为最小值
        self.start_point = (
            min(self.start_point[0], node.start_point[0]),
            min(self.start_point[1], node.start_point[1]) if self.start_point[0] == node.start_point[0] else 
            (self.start_point[1] if self.start_point[0] < node.start_point[0] else node.start_point[1])
        )
        
        # 更新结束位置为最大值
        self.end_point = (
            max(self.end_point[0], node.end_point[0]),
            max(self.end_point[1], node.end_point[1]) if self.end_point[0] == node.end_point[0] else 
            (self.end_point[1] if self.end_point[0] > node.end_point[0] else node.end_point[1])
        )

    def add_offset(self, start_offset: Tuple[int, int] = (0, 0), end_offset: Tuple[int, int] = (0, 0)) -> None:
        """添加偏移量到节点的起始和结束位置。
        
        这个方法不会改变节点的实际位置，而是添加一个偏移量，用于在获取文本时调整范围。
        主要用于处理需要排除某些标记（如YAML分隔符）的情况。
        
        多次调用此方法会累积偏移量，类似于 Tree-sitter 的 #offset! 指令。
        例如：add_offset((1, 0), (-1, 0)) 会将起始位置向下移动1行，结束位置向上移动1行。
        
        Args:
            start_offset: 起始位置的偏移量，格式为 (行偏移, 列偏移)
            end_offset: 结束位置的偏移量，格式为 (行偏移, 列偏移)
        """
        # 获取当前偏移量，如果没有则初始化为 (0, 0)
        current_start_offset = self.metadata.get('start_offset', (0, 0))
        current_end_offset = self.metadata.get('end_offset', (0, 0))
        
        # 累积偏移量
        new_start_offset = (
            current_start_offset[0] + start_offset[0],
            current_start_offset[1] + start_offset[1]
        )
        
        new_end_offset = (
            current_end_offset[0] + end_offset[0],
            current_end_offset[1] + end_offset[1]
        )
        
        # 更新偏移量
        self.metadata['start_offset'] = new_start_offset
        self.metadata['end_offset'] = new_end_offset
    
    def get_text(self, doc: DocumentProtocol) -> str:
        """获取节点的文本内容。
        
        如果节点有偏移量设置，会应用这些偏移量来调整获取的文本范围。
        
        Args:
            doc: 文档对象
            
        Returns:
            调整后范围内的文本内容
        """
        # 获取偏移量，如果没有设置则使用默认值 (0, 0)
        start_offset = self.metadata.get('start_offset', (0, 0))
        end_offset = self.metadata.get('end_offset', (0, 0))
        
        # 计算实际的起始和结束位置
        actual_start = (
            self.start_point[0] + start_offset[0],
            self.start_point[1] + start_offset[1] if start_offset[0] == 0 else start_offset[1]
        )
        
        actual_end = (
            self.end_point[0] + end_offset[0],
            self.end_point[1] + end_offset[1] if end_offset[0] == 0 else end_offset[1]
        )
        
        return doc.get_text(actual_start, actual_end)
    
    @classmethod
    def from_ts_node(cls, node: Node, node_type: NodeType) -> 'SemanticNode':
        """从tree-sitter节点创建语义节点。
        
        Args:
            node: tree-sitter节点
            node_type: 节点类型
            node_name: 节点名称，如果为None则使用tree-sitter节点的类型名称
            
        Returns:
            创建的语义节点
        """

        semantic_node = cls(
            node_type=node_type,
            start_point=(node.start_point[0], node.start_point[1]),
            end_point=(node.end_point[0], node.end_point[1]),
            metadata={"original_node_type": node.type}
        )
        
        semantic_node.add_ts_node(node)
        return semantic_node


# 定义类型变量用于表示解析树
T = TypeVar('T')

class ResolverProtocol(Protocol):
    """资源解析器协议。
    
    定义了资源解析器的基本接口，用于将资源引用转换为语义节点列表。
    """
    
    @abstractmethod
    def resolve(self, uri: str, parsed_document: DocumentProtocol) -> List[SemanticNode]:
        """将资源路径解析为语义节点列表。
        
        Args:
            uri: 资源路径
            parsed_document: 已解析的文档对象
            
        Returns:
            解析后的语义节点列表
            
        Raises:
            ValueError: 当资源路径格式不正确或不支持的资源类型时抛出
        """
        ...
        
    @abstractmethod
    def parse_uri(self, uri: str) -> List[Tuple[str, str]]:
        """解析资源引用 URI。
        
        Args:
            uri: 资源引用 URI
            
        Returns:
            解析结果列表，如果解析失败则返回 []
        """
        ...
        
    @abstractmethod
    def uri_to_query(self, uri: str) -> Tuple[str, str]:
        """将资源引用 URI 转换为查询字符串。
        
        Args:
            uri: 资源引用 URI
            
        Returns:
            查询字符串
            
        Raises:
            ValueError: 当 URI 格式不正确或不支持的资源类型时抛出
        """
        ...

