import pytest
from textcase.parse.parser import Parser
from textcase.parse.document_type import DocumentType
from textcase.parse.resolver import NodeType
from textcase.parse.resolver_md import MarkdownResolver

# Test data
SAMPLE_MARKDOWN = """---
title: 测试文档
description: 这是一个测试文档
---

# 标题1

这是一段内容。

## 子标题

- 列表项1
- 列表项2
"""

# Fixtures
@pytest.fixture
def markdown_resolver():
    return MarkdownResolver()

@pytest.fixture
def parsed_document():
    parser = Parser(document_type=DocumentType.MARKDOWN)
    return parser.parse(SAMPLE_MARKDOWN)

# Test classes
class TestParseUri:
    """Test parse_uri method of MarkdownResolver"""
    
    def test_parse_meta_uri(self, markdown_resolver):
        """Test parsing #meta URI"""
        result = markdown_resolver.parse_uri("#meta")
        assert result == [("rtype", "#meta")]
    
    def test_parse_frontmatter_uri(self, markdown_resolver):
        """Test parsing #frontmatter URI (should be same as #meta)"""
        result = markdown_resolver.parse_uri("#frontmatter")
        assert result == [("rtype", "#meta")]
    
    def test_parse_none_uri(self, markdown_resolver):
        """Test parsing None URI (should default to #file)"""
        result = markdown_resolver.parse_uri(None)
        assert result == [("rtype", "#file")]

class TestUriToQuery:
    """Test uri_to_query method of MarkdownResolver"""
    
    def test_meta_uri_to_query(self, markdown_resolver):
        """Test converting #meta URI to query"""
        query, _ = markdown_resolver.uri_to_query("#meta")
        assert "frontmatter" in query
    
    def test_frontmatter_uri_to_query(self, markdown_resolver):
        """Test converting #frontmatter URI to query"""
        meta_query, _ = markdown_resolver.uri_to_query("#meta")
        frontmatter_query, _ = markdown_resolver.uri_to_query("#frontmatter")
        assert meta_query == frontmatter_query

class TestResolve:
    """Test resolve method of MarkdownResolver"""
    
    def test_resolve_meta(self, markdown_resolver, parsed_document):
        """Test resolving #meta URI"""
        items = markdown_resolver.resolve("#meta", parsed_document=parsed_document)
        assert len(items) == 1
        assert items[0].node_type == NodeType.METADATA
        assert "title: 测试文档" in items[0].get_text(parsed_document)
        assert "description: 这是一个测试文档" in items[0].get_text(parsed_document)
        assert "---" not in items[0].get_text(parsed_document)
    
    def test_resolve_frontmatter(self, markdown_resolver, parsed_document):
        """Test resolving #frontmatter URI"""
        meta_items = markdown_resolver.resolve("#meta", parsed_document=parsed_document)
        frontmatter_items = markdown_resolver.resolve("#frontmatter", parsed_document=parsed_document)
        
        assert len(meta_items) == 1
        assert len(frontmatter_items) == 1
        assert frontmatter_items[0].node_type == meta_items[0].node_type
        assert (frontmatter_items[0].get_text(parsed_document) == 
                meta_items[0].get_text(parsed_document))