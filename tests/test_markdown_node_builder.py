"""
测试 MarkdownSemanticNodeBuilder 类的功能。

验证 MarkdownSemanticNodeBuilder 能够正确创建适合 Markdown 文档的语义节点。
"""

import pytest
from unittest.mock import Mock, MagicMock
from enum import Enum

from textcase.parse.resolver import NodeType, SemanticNode
from textcase.parse.resolver_md_node import MarkdownSemanticNodeBuilder


class TestMarkdownSemanticNodeBuilder:
    """测试 MarkdownSemanticNodeBuilder 类。"""
    
    def setup_method(self):
        """测试前的准备工作。"""
        self.builder = MarkdownSemanticNodeBuilder()
    
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
        node = self.builder.create_node(NodeType.DOCUMENT)
        
        # 验证节点属性
        assert node.node_type == NodeType.DOCUMENT
        assert node.start_point == (0, 0)
        assert node.end_point == (0, 0)
        assert isinstance(node.metadata, dict)
        assert len(node.children) == 0
        assert node.container is None
    
    def test_create_node_with_metadata(self):
        """测试创建带有元数据的节点。"""
        # 创建带有元数据的节点
        metadata = {"key": "value", "test": 123}
        node = self.builder.create_node(NodeType.DOCUMENT, metadata=metadata)
        
        # 验证元数据被正确设置
        assert node.metadata["key"] == "value"
        assert node.metadata["test"] == 123
    
    def test_create_child_node(self):
        """测试创建子节点功能。"""
        # 创建父节点
        parent = self.builder.create_node(NodeType.DOCUMENT)
        
        # 创建子节点
        child = self.builder.create_child_node(parent, NodeType.SECTION)
        
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
        node = self.builder.create_node(NodeType.HEADING, mock_node)
        
        # 验证标题特定的元数据
        assert node.metadata["heading_level"] == 2
        assert node.metadata["title_text"] == "Test Heading"
        assert node.metadata["node_name"] == "Test Heading"
    
    def test_process_list_item_node_task(self):
        """测试处理任务列表项节点的功能。"""
        # 模拟一个任务列表项节点（未完成）
        mock_node = self.create_mock_node("list_item")
        marker = self.create_mock_node("task_list_marker_unchecked")
        para = self.create_mock_node("paragraph")
        para.text = b"Task to do"
        mock_node.children = [marker, para]
        
        # 创建列表项节点
        node = self.builder.create_node(NodeType.LIST_ITEM, mock_node)
        
        # 验证任务列表项特定的元数据
        assert node.metadata["is_task_item"] is True
        assert node.metadata["task_completed"] is False
        assert node.metadata["item_text"] == "Task to do"
        
        # 模拟一个已完成的任务列表项节点
        mock_node = self.create_mock_node("list_item")
        marker = self.create_mock_node("task_list_marker_checked")
        para = self.create_mock_node("paragraph")
        para.text = b"Completed task"
        mock_node.children = [marker, para]
        
        # 创建列表项节点
        node = self.builder.create_node(NodeType.LIST_ITEM, mock_node)
        
        # 验证任务列表项特定的元数据
        assert node.metadata["is_task_item"] is True
        assert node.metadata["task_completed"] is True
        assert node.metadata["item_text"] == "Completed task"
    
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
        node = self.builder.create_node(NodeType.CODE_BLOCK, mock_node)
        
        # 验证代码块特定的元数据
        assert node.metadata["language"] == "python"
        assert node.metadata["code_content"] == "def test():\n    return True"
        assert node.metadata["node_name"] == "Code Block (python)"
    
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
        node = self.builder.create_node(NodeType.SECTION, mock_node)
        
        # 验证章节特定的元数据
        assert node.metadata["section_title"] == "Section Title"
        assert node.metadata["heading_level"] == 3
        assert node.metadata["node_name"] == "Section Title"
