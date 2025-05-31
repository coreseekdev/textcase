"""
文本文件解析模块，基于 tree-sitter 提供通用的文本解析能力。

textcase.parse 包提供文本解析和资源引用解析功能。

主要组件：
- Parser: 基于 tree-sitter 的通用文本解析器
- Resolver: 资源引用解析器协议
- SemanticNode: 语义节点基类
- PythonResolver: Python 语言特定的解析器
- MarkdownResolver: Markdown 文档特定的解析器
"""

from .parser import Parser
from .resolver import SemanticNode, NodeType
from .resolver_py import PythonResolver
from .resolver_md import MarkdownResolver

__all__ = [
    'Parser',
    'SemanticNode',
    'NodeType',
    'PythonResolver',
    'MarkdownResolver',
]
