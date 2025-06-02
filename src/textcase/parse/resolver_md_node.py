"""
Markdown 特定的语义节点构建器。

提供针对 Markdown 文档的语义节点构建功能，优化对 Markdown 特定元素的处理。
"""

from typing import Type, Dict, List, Optional, Any, Tuple

from .document import DocumentProtocol, Node
from .resolver import DefaultSemanticNodeBuilder, SemanticNode, NodeType


class MarkdownMetadata(SemanticNode):

    # TODO: 处理 文件头 链接的 list 和 add 
    pass

class MarkdownSemanticNodeBuilder(DefaultSemanticNodeBuilder):
    """
    Markdown 特定的语义节点构建器。
    
    继承自默认构建器，但针对 Markdown 文档的特性进行了优化，
    能够更好地处理标题、列表项、代码块等 Markdown 特定元素。
    """
    
    def get_node_class(self, node_type: NodeType) -> Type['SemanticNode']:
        """
        获取指定节点类型的语义节点类。
        
        Args:
            node_type: 节点类型
            
        Returns:
            对应节点类型的语义节点类
        """
        if node_type == NodeType.METADATA:
            return MarkdownMetadata
        return SemanticNode