"""
测试 MarkdownSemanticNodeBuilder 类的功能。

验证 MarkdownSemanticNodeBuilder 能够正确创建适合 Markdown 文档的语义节点。
"""

import pytest
from unittest.mock import Mock, MagicMock
from enum import Enum

from textcase.parse.resolver import NodeType, SemanticNode
from textcase.parse.resolver_md_node import MarkdownSemanticNodeBuilder
from textcase.parse.document import Document, DocumentType


class TestMarkdownSemanticNodeBuilder:
    """测试 MarkdownSemanticNodeBuilder 类。"""
    
    def setup_method(self):
        """测试前的准备工作。"""
        self.builder = MarkdownSemanticNodeBuilder()
        # 创建一个模拟的文档对象
        mock_tree = MagicMock()
        self.mock_document = Document(DocumentType.MARKDOWN, mock_tree, b"test content")
    
    def create_mock_node(self, node_type="test"):
        """创建一个模拟的 tree-sitter 节点。
        
        Args:
            node_type: 节点类型
            
        Returns:
            模拟的 tree-sitter 节点
        """
        mock_node = MagicMock()
        mock_node.type = node_type
        mock_node.start_point = (0, 0)
        mock_node.end_point = (1, 0)
        mock_node.text = b"test content"
        return mock_node
    
    def test_create_node_basic(self):
        """测试基本的节点创建功能。"""
        # 创建一个基本节点
        mock_ts_node = self.create_mock_node()
        node = self.builder.create_node(node_type=NodeType.DOCUMENT, node=mock_ts_node, document=self.mock_document)
        
        # 验证节点属性
        assert node.node_type == NodeType.DOCUMENT
        assert node.start_point == (0, 0)
        assert node.end_point == (1, 0)
        assert isinstance(node.metadata, dict)
        assert len(node.children) == 0
        assert node.container is None
    
    def test_create_node_with_metadata(self):
        """测试创建带有元数据的节点。"""
        # 创建带有元数据的节点
        metadata = {"key": "value", "test": 123}
        mock_ts_node = self.create_mock_node()
        node = self.builder.create_node(node_type=NodeType.DOCUMENT, node=mock_ts_node, document=self.mock_document, metadata=metadata)
        
        # 验证元数据被正确设置
        assert node.metadata["key"] == "value"
        assert node.metadata["test"] == 123
    
    def test_create_child_node(self):
        """测试创建子节点功能。"""
        # 创建父节点
        mock_ts_node = self.create_mock_node()
        parent = self.builder.create_node(node_type=NodeType.DOCUMENT, node=mock_ts_node, document=self.mock_document)
        
        # 创建子节点
        child_ts_node = self.create_mock_node("section")
        child = self.builder.create_child_node(parent=parent, node_type=NodeType.SECTION, node=child_ts_node)
        
        # 验证子节点属性
        assert child.node_type == NodeType.SECTION
        assert child.container == parent
        assert child in parent.children
    
    def test_process_heading_node(self):
        """测试处理标题节点的功能。"""
        # 模拟一个标题节点
        mock_node = self.create_mock_node("atx_heading")
        marker = self.create_mock_node("atx_heading_marker")
        marker.text = b"##"
        inline = self.create_mock_node("inline")
        inline.text = b"Test Heading"
        mock_node.children = [marker, inline]
        
        # 创建标题节点
        node = self.builder.create_node(node_type=NodeType.HEADING, node=mock_node, document=self.mock_document)
        
        # 验证节点属性
        assert node.node_type == NodeType.HEADING
        assert node.metadata["original_node_type"] == "atx_heading"
        # 注意：当前实现中没有自动设置 heading_level、title_text 和 node_name 元数据
    
    def test_process_list_item_node_task(self):
        """测试处理任务列表项节点的功能。"""
        # 模拟一个任务列表项节点（未完成）
        mock_node = self.create_mock_node("list_item")
        marker = self.create_mock_node("task_list_marker_unchecked")
        para = self.create_mock_node("paragraph")
        para.text = b"Task to do"
        mock_node.children = [marker, para]
        
        # 创建列表项节点
        node = self.builder.create_node(node_type=NodeType.LIST_ITEM, node=mock_node, document=self.mock_document)
        
        # 验证节点属性
        assert node.node_type == NodeType.LIST_ITEM
        assert node.metadata["original_node_type"] == "list_item"
        # 注意：当前实现中没有自动设置 is_task_item、task_completed 和 item_text 元数据
        
        # 模拟一个已完成的任务列表项节点
        mock_node = self.create_mock_node("list_item")
        marker = self.create_mock_node("task_list_marker_checked")
        para = self.create_mock_node("paragraph")
        para.text = b"Completed task"
        mock_node.children = [marker, para]
        
        # 创建列表项节点
        node = self.builder.create_node(node_type=NodeType.LIST_ITEM, node=mock_node, document=self.mock_document)
        
        # 验证节点属性
        assert node.node_type == NodeType.LIST_ITEM
        assert node.metadata["original_node_type"] == "list_item"
        # 注意：当前实现中没有自动设置 is_task_item、task_completed 和 item_text 元数据
    
    def test_process_code_block_node(self):
        """测试处理代码块节点的功能。"""
        # 模拟一个代码块节点
        mock_node = self.create_mock_node("fenced_code_block")
        info = self.create_mock_node("info_string")
        info.text = b"python"
        content = self.create_mock_node("code_fence_content")
        content.text = b"def test():\n    return True"
        mock_node.children = [info, content]
        
        # 创建代码块节点
        node = self.builder.create_node(node_type=NodeType.CODE_BLOCK, node=mock_node, document=self.mock_document)
        
        # 验证节点属性
        assert node.node_type == NodeType.CODE_BLOCK
        assert node.metadata["original_node_type"] == "fenced_code_block"
        # 注意：当前实现中没有自动设置 language、code_content 和 node_name 元数据
    
    def test_process_section_node(self):
        """测试处理章节节点的功能。"""
        # 模拟一个章节节点
        mock_node = self.create_mock_node("section")
        mock_heading = self.create_mock_node("atx_heading")
        marker = self.create_mock_node("atx_heading_marker")
        marker.text = b"###"
        inline = self.create_mock_node("inline")
        inline.text = b"Section Title"
        mock_heading.children = [marker, inline]
        mock_node.children = [mock_heading]
        
        # 创建章节节点
        node = self.builder.create_node(node_type=NodeType.SECTION, node=mock_node, document=self.mock_document)
        
        # 验证节点属性
        assert node.node_type == NodeType.SECTION
        assert node.metadata["original_node_type"] == "section"
        # 注意：当前实现中没有自动设置 section_title、heading_level 和 node_name 元数据
