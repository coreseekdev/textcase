import pytest

from textcase.parse.parser import Parser
from textcase.parse.document_type import DocumentType
from textcase.parse.resolver import ItemType
from textcase.parse.resolver_md import MarkdownResolver
from textcase.parse.document import Document


class TestMarkdownResolver:
    """测试 MarkdownResolver 类。
    
    CASE-1: 测试通过 /#meta 或 /#frontmatter 获取 Markdown 文档的元信息
    
    测试步骤:
    1. 创建 MarkdownResolver 实例
    2. 调用 parse_uri 方法解析 "#meta" 和 "#frontmatter" 路径
    3. 调用 uri_to_query 方法获取查询字符串
    4. 调用 resolve 方法获取文档项
    
    预期结果:
    1. parse_uri 应该正确解析 "#meta" 和 "#frontmatter" 路径
    2. uri_to_query 应该返回正确的查询字符串
    3. resolve 应该返回正确的文档项列表
    """
    
    def test_meta_frontmatter_resource(self):
        """测试通过 /#meta 或 /#frontmatter 获取 Markdown 文档的元信息。"""
        resolver = MarkdownResolver()
        parser = Parser(document_type=DocumentType.MARKDOWN)
        
        # 创建一个简单的 Markdown 文档用于测试
        markdown_content = """---
title: 测试文档
description: 这是一个测试文档
---

# 标题1

这是一段内容。

## 子标题

- 列表项1
- 列表项2
"""
        
        # 解析文档
        parsed_document = parser.parse(markdown_content)
        
        # 测试 #meta 路径
        meta_parsed = resolver.parse_uri("#meta")
        assert meta_parsed is not None
        assert meta_parsed["resource_type"] == "#meta"
        
        # 测试 #frontmatter 路径（应该被视为 #meta 的同义词）
        frontmatter_parsed = resolver.parse_uri("#frontmatter")
        assert frontmatter_parsed is not None
        assert frontmatter_parsed["resource_type"] == "#meta"
        
        # 测试 uri_to_query 方法
        meta_query = resolver.uri_to_query("#meta")
        frontmatter_query = resolver.uri_to_query("#frontmatter")
        
        # 两个查询应该相同
        assert meta_query == frontmatter_query
        # 查询应该包含 frontmatter
        assert "frontmatter" in meta_query
        
        # 测试 resolve 方法，传入解析器和已解析的文档
        meta_items = resolver.resolve("#meta", parsed_document=parsed_document)
        frontmatter_items = resolver.resolve("#frontmatter", parsed_document=parsed_document)
        
        # 检查结果
        assert len(meta_items) == 1
        assert len(frontmatter_items) == 1
        
        # 检查 meta 项
        meta_item = meta_items[0]
        assert meta_item.node_name == "frontmatter"
        assert meta_item.item_type == ItemType.METADATA  # 使用 METADATA 类型
        
        # 如果解析器成功解析了 frontmatter，文本应该包含实际的 frontmatter 内容
        # 检查处理后的元数据内容，应该去除了 --- 分隔符
        assert "title: 测试文档" in meta_item.text
        assert "description: 这是一个测试文档" in meta_item.text
        assert "---" not in meta_item.text  # 确保分隔符被移除
        
        # 检查位置信息是否正确
        assert meta_item.start_point == (0, 0)  # frontmatter 应该从文档开头开始
        assert meta_item.end_point[0] > 0  # 结束行应该大于 0
        
        # 检查 frontmatter 项（应该与 meta 项相同）
        frontmatter_item = frontmatter_items[0]
        assert frontmatter_item.node_name == meta_item.node_name
        assert frontmatter_item.item_type == meta_item.item_type
        assert frontmatter_item.text == meta_item.text


if __name__ == "__main__":
    # 可以直接运行此文件进行测试
    pytest.main(["-v", __file__])
