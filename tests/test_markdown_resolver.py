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

# 包含多级嵌套标题和不同格式标题的测试数据
NESTED_MARKDOWN = """---
title: 嵌套标题测试
---

# 一级标题

一级内容

## 二级标题A

二级A内容

### TC-01: 测试用例1

测试用例1内容

### TC-2: 测试用例2

测试用例2内容

## 二级标题B

二级B内容

### [TC-03]: 测试用例3

测试用例3内容

### `TC-4` 测试用例4

测试用例4内容

# 另一个一级标题

另一个一级内容

## REQ-001 需求1

需求1内容

### 实现细节

实现细节内容
"""

# Fixtures
@pytest.fixture
def markdown_resolver():
    return MarkdownResolver()

@pytest.fixture
def parsed_nested_markdown():
    parser = Parser(document_type=DocumentType.MARKDOWN)
    return parser.parse(NESTED_MARKDOWN)

@pytest.fixture
def parsed_document():
    parser = Parser(document_type=DocumentType.MARKDOWN)
    return parser.parse(SAMPLE_MARKDOWN)


class TestPathMatching:
    
    def _execute_query_and_check_results(self, markdown_resolver, parsed_doc, path_components, exact_parent_match=True, expected_match=True):
        """执行查询并验证结果"""
        # 构建查询字符串
        query_string = markdown_resolver._build_path_query(path_components, exact_parent_match=exact_parent_match)
        if query_string is None:
            return False
            
        # 执行查询
        language = parsed_doc.language
        query = language.query(query_string)
        captures = query.captures(parsed_doc.tree.root_node)
        
        # 提取目标内容
        results = []
        target_content_found = False
        for capture in captures:
            node, name = capture
            if name == "target_content":
                target_content_found = True
                results.append(node.text.decode('utf8'))
        
        if expected_match:
            assert target_content_found, "应该找到匹配的内容，但没有找到"
            assert len(results) > 0, "应该有匹配结果，但结果为空"
        else:
            assert not target_content_found or len(results) == 0, "不应该找到匹配的内容，但找到了"
            
        return target_content_found and len(results) > 0
    
    def test_one_level_path(self, markdown_resolver, parsed_nested_markdown):
        """测试单级路径匹配"""
        # 测试匹配一级标题
        path = ["一级标题"]
        assert self._execute_query_and_check_results(markdown_resolver, parsed_nested_markdown, path)
        
        # 测试匹配不存在的标题
        path = ["不存在的标题"]
        # 查询字符串应该生成，但不应该有匹配结果
        assert not self._execute_query_and_check_results(markdown_resolver, parsed_nested_markdown, path, expected_match=False)
    
    def test_multi_level_path(self, markdown_resolver, parsed_nested_markdown):
        """测试多级路径匹配"""
        # 测试二级路径
        path = ["一级标题", "二级标题A"]
        assert self._execute_query_and_check_results(markdown_resolver, parsed_nested_markdown, path)
        
        # 测试三级路径
        path = ["一级标题", "二级标题A", "TC-01: 测试用例1"]
        assert self._execute_query_and_check_results(markdown_resolver, parsed_nested_markdown, path)
    
    def test_non_level1_starting_path(self, markdown_resolver, parsed_nested_markdown):
        """测试非一级标题起点的路径"""
        # 从二级标题开始的路径
        path = ["二级标题A", "TC-01: 测试用例1"]
        assert self._execute_query_and_check_results(markdown_resolver, parsed_nested_markdown, path)
        
        # 从三级标题开始的单级路径
        path = ["TC-01: 测试用例1"]
        assert self._execute_query_and_check_results(markdown_resolver, parsed_nested_markdown, path)
    
    def test_different_heading_formats(self, markdown_resolver, parsed_nested_markdown):
        """测试不同格式的标题匹配"""
        # 测试带冒号的标题
        path = ["TC-01: 测试用例1"]
        assert self._execute_query_and_check_results(markdown_resolver, parsed_nested_markdown, path)
        
        # 测试带方括号的标题
        path = ["[TC-03]: 测试用例3"]
        assert self._execute_query_and_check_results(markdown_resolver, parsed_nested_markdown, path)
        
        # 测试带反引号的标题
        path = ["`TC-4` 测试用例4"]
        assert self._execute_query_and_check_results(markdown_resolver, parsed_nested_markdown, path)
    
    def test_numbered_identifier_matching(self, markdown_resolver, parsed_nested_markdown):
        """测试编号标识符的匹配"""
        # 测试TC-01和TC-1的匹配（忽略前导零）
        path = ["TC-1: 测试用例1"]
        assert self._execute_query_and_check_results(markdown_resolver, parsed_nested_markdown, path)
        
        # 测试REQ-001和REQ-1的匹配
        path = ["REQ-1 需求1"]
        assert self._execute_query_and_check_results(markdown_resolver, parsed_nested_markdown, path)
        
        # 测试TC-4和TC-04的匹配
        path = ["TC-04 测试用例4"]
        assert self._execute_query_and_check_results(markdown_resolver, parsed_nested_markdown, path)
    
    def test_partial_matching(self, markdown_resolver, parsed_nested_markdown):
        """测试部分匹配"""
        # 测试标题的部分匹配（只匹配标题的一部分）
        query_string, _ = markdown_resolver._find_content_by_path(
            parsed_nested_markdown.tree, ["二级标题"], exact_parent_match=False
        )
        assert query_string is not None
        assert self._execute_query_and_check_results(markdown_resolver, parsed_nested_markdown, query_string)
        
        # 测试多级路径的部分匹配
        query_string, _ = markdown_resolver._find_content_by_path(
            parsed_nested_markdown.tree, ["一级", "二级标题A", "TC-01"], exact_parent_match=False
        )
        assert query_string is not None
        assert self._execute_query_and_check_results(markdown_resolver, parsed_nested_markdown, query_string)
        
    def test_middle_node_path(self, markdown_resolver, parsed_nested_markdown):
        """测试从中间节点开始的路径匹配"""
        # 测试从二级标题B开始的路径
        query_string, _ = markdown_resolver._find_content_by_path(
            parsed_nested_markdown.tree, ["二级标题B", "[TC-03]: 测试用例3"]
        )
        assert query_string is not None
        assert self._execute_query_and_check_results(markdown_resolver, parsed_nested_markdown, query_string)
        
        # 测试从二级标题B开始的路径，匹配另一个子标题
        query_string, _ = markdown_resolver._find_content_by_path(
            parsed_nested_markdown.tree, ["二级标题B", "`TC-4` 测试用例4"]
        )
        assert query_string is not None
        assert self._execute_query_and_check_results(markdown_resolver, parsed_nested_markdown, query_string)
        
        # 测试从另一个一级标题开始的路径
        query_string, _ = markdown_resolver._find_content_by_path(
            parsed_nested_markdown.tree, ["另一个一级标题", "REQ-001 需求1"]
        )
        assert query_string is not None
        assert self._execute_query_and_check_results(markdown_resolver, parsed_nested_markdown, query_string)
        
        # 测试从需求标题开始的路径
        query_string, _ = markdown_resolver._find_content_by_path(
            parsed_nested_markdown.tree, ["REQ-001 需求1", "实现细节"]
        )
        assert query_string is not None
        assert self._execute_query_and_check_results(markdown_resolver, parsed_nested_markdown, query_string)

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