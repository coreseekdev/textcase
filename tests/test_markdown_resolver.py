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
    
    def _execute_query_and_check_results(self, markdown_resolver, parsed_document, path_components, expected_match=True, path="full"):
        """执行查询并检查结果
        
        Args:
            markdown_resolver: MarkdownResolver实例
            parsed_document: 解析后的文档
            path_components: 路径组件，可以是字符串列表、元组列表或查询字符串
            expected_match: 是否期望有匹配结果
            path: 匹配模式，"full"或"partial"
        """
        # 处理不同类型的路径组件
        if isinstance(path_components, str):
            # 如果已经是查询字符串，直接使用
            query_string = path_components
        elif isinstance(path_components, list):
            if all(isinstance(item, str) for item in path_components):
                # 如果是字符串路径列表，则转换为token元组列表
                # 根据传入的path参数决定匹配类型
                token_path = [(path, component) for component in path_components]
                query_string = markdown_resolver._build_path_query(token_path)
            else:
                # 已经是token元组列表
                query_string = markdown_resolver._build_path_query(path_components)
        else:
            assert False, f"不支持的路径组件类型: {type(path_components)}"
            
        # 确保查询字符串有效
        assert query_string is not None, "查询字符串不应为None"
        
        # 调试输出
        print(f"\n执行查询: {path_components}")
        print(f"查询字符串:\n{query_string}")
        
        try:
            # 执行查询
            query = parsed_document.language.query(query_string)
            # 查看查询的捕获方法
            print(f"查询对象方法: {dir(query)}")
            
            # 尝试使用matches而不是captures
            matches = query.matches(parsed_document.tree.root_node)
            print(f"匹配数量: {len(matches)}")
            
            # 打印匹配的类型和内容
            for i, match in enumerate(matches):
                print(f"匹配 {i}: {type(match)}, {match}")
                if hasattr(match, 'captures'):
                    for capture in match.captures:
                        print(f"  捕获: {capture.node.type} - {capture.name}")
        except Exception as e:
            print(f"查询执行错误: {e}")
            if not expected_match:
                # 如果不期望匹配，则允许查询错误
                return False
            raise
        
        # 提取目标内容
        results = []
        target_content_found = False
        
        # 处理匹配结果
        for match in matches:
            if isinstance(match, tuple) and len(match) == 2 and isinstance(match[1], dict):
                # 处理匹配字典
                match_dict = match[1]
                if 'target_content' in match_dict:
                    target_content_found = True
                    for node in match_dict['target_content']:
                        content_text = node.text.decode('utf8')
                        results.append(content_text)
                        print(f"找到目标内容: {content_text[:50]}...")
            elif hasattr(match, 'captures'):
                # 兼容旧版本
                for capture in match.captures:
                    if capture.name == "target_content":
                        target_content_found = True
                        content_text = capture.node.text.decode('utf8')
                        results.append(content_text)
                        print(f"找到目标内容: {content_text[:50]}...")
            else:
                print(f"不支持的匹配格式: {match}")
                continue
        
        if expected_match:
            assert target_content_found, "应该找到匹配的内容，但没有找到"
            assert len(results) > 0, "应该有匹配结果，但结果为空"
        else:
            assert not target_content_found or len(results) == 0, "不应该找到匹配的内容，但找到了"
            
        return target_content_found and len(results) > 0
    
    def test_one_level_path(self, markdown_resolver, parsed_nested_markdown):
        """测试单级路径匹配"""
        # 测试匹配一级标题
        path_components = [("full", "一级标题")]
        assert self._execute_query_and_check_results(markdown_resolver, parsed_nested_markdown, path_components)
        
        # 测试匹配不存在的标题
        path_components = [("full", "不存在的标题")]
        # 查询字符串应该生成，但不应该有匹配结果
        assert not self._execute_query_and_check_results(markdown_resolver, parsed_nested_markdown, path_components, expected_match=False)
    
    def test_multi_level_path(self, markdown_resolver, parsed_nested_markdown):
        """测试多级路径匹配"""
        # 测试二级路径
        path_components = [
            ("full", "一级标题"),
            ("full", "二级标题A")
        ]
        assert self._execute_query_and_check_results(markdown_resolver, parsed_nested_markdown, path_components)
        
        # 测试三级路径
        path_components = [
            ("full", "一级标题"),
            ("full", "二级标题A"),
            ("full", "TC-01: 测试用例1")
        ]
        assert self._execute_query_and_check_results(markdown_resolver, parsed_nested_markdown, path_components)
    
    def test_non_level1_starting_path(self, markdown_resolver, parsed_nested_markdown):
        """测试非一级标题起点的路径"""
        # 从二级标题开始的路径
        path_components = [
            ("full", "二级标题A"),
            ("full", "TC-01: 测试用例1")
        ]
        assert self._execute_query_and_check_results(markdown_resolver, parsed_nested_markdown, path_components)
        
        # 从三级标题开始的单级路径
        path_components = [("full", "TC-01: 测试用例1")]
        assert self._execute_query_and_check_results(markdown_resolver, parsed_nested_markdown, path_components)
    
    def test_different_heading_formats(self, markdown_resolver, parsed_nested_markdown):
        """测试不同格式的标题匹配"""
        # 测试带冒号的标题
        path_components = [("full", "TC-01: 测试用例1")]
        assert self._execute_query_and_check_results(markdown_resolver, parsed_nested_markdown, path_components)
        
        # 测试带方括号的标题
        path_components = [("full", "[TC-03]: 测试用例3")]
        assert self._execute_query_and_check_results(markdown_resolver, parsed_nested_markdown, path_components)
        
        # 测试带反引号的标题
        path_components = [("full", "`TC-4` 测试用例4")]
        assert self._execute_query_and_check_results(markdown_resolver, parsed_nested_markdown, path_components)
    
    def test_numbered_identifier_matching(self, markdown_resolver, parsed_nested_markdown):
        """测试编号标识符的匹配"""
        # 使用部分匹配测试TC-01和TC-1的匹配（忽略前导零）
        path_components = [("partial", "TC-1")]
        assert self._execute_query_and_check_results(markdown_resolver, parsed_nested_markdown, path_components)
        
        # 使用部分匹配测试REQ-001和REQ-1的匹配
        path_components = [("partial", "REQ-1")]
        assert self._execute_query_and_check_results(markdown_resolver, parsed_nested_markdown, path_components)
        
        # 使用完全匹配测试精确标题
        path_components = [("full", "TC-01: 测试用例1")]
        assert self._execute_query_and_check_results(markdown_resolver, parsed_nested_markdown, path_components)
        
        path_components = [("full", "REQ-001 需求1")]
        assert self._execute_query_and_check_results(markdown_resolver, parsed_nested_markdown, path_components)
        
        # 测试TC-4和TC-04的匹配
        path_components = [("full", "`TC-4` 测试用例4")]
        assert self._execute_query_and_check_results(markdown_resolver, parsed_nested_markdown, path_components)
    
    def test_partial_matching(self, markdown_resolver, parsed_nested_markdown):
        """测试部分匹配"""
        # 测试标题的部分匹配（只匹配标题的一部分）
        path_components = [("partial", "二级标题")]
        assert self._execute_query_and_check_results(markdown_resolver, parsed_nested_markdown, path_components, path="partial")
        
        # 测试多级路径的部分匹配
        path_components = [
            ("partial", "一级"),
            ("partial", "二级标题A"),
            ("partial", "TC-01")
        ]
        assert self._execute_query_and_check_results(markdown_resolver, parsed_nested_markdown, path_components, path="partial")
        
    def test_middle_node_path(self, markdown_resolver, parsed_nested_markdown):
        """测试从中间节点开始的路径匹配"""
        # 测试从二级标题B开始的路径
        path_components = [
            ("full", "二级标题B"),
            ("full", "[TC-03]: 测试用例3")
        ]
        assert self._execute_query_and_check_results(markdown_resolver, parsed_nested_markdown, path_components)
        
        # 测试从二级标题B开始的路径，匹配另一个子标题
        path_components = [
            ("full", "二级标题B"),
            ("full", "`TC-4` 测试用例4")
        ]
        assert self._execute_query_and_check_results(markdown_resolver, parsed_nested_markdown, path_components)
        
        # 测试从另一个一级标题开始的路径
        path_components = [
            ("full", "另一个一级标题"),
            ("full", "REQ-001 需求1")
        ]
        assert self._execute_query_and_check_results(markdown_resolver, parsed_nested_markdown, path_components)
        
        # 测试从需求标题开始的路径
        path_components = [
            ("full", "REQ-001 需求1"),
            ("full", "实现细节")
        ]
        assert self._execute_query_and_check_results(markdown_resolver, parsed_nested_markdown, path_components)

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