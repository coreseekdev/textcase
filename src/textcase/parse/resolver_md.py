"""
Markdown 文档特定的 URI 解析器。

提供针对 Markdown 文档的资源引用解析和查询生成功能。
"""

import re
from typing import Dict, List, Optional, Any, Tuple

from .parser import ParserProtocol
from .document import DocumentProtocol
from .resolver import Resolver, ResolverProtocol, DocumentItem, ItemType


class MarkdownResolver(Resolver, ResolverProtocol):
    """
Markdown 文档特定的 URI 解析器。
    
    针对 Markdown 文档提供更精确的资源引用解析和查询生成。
    支持标题、列表项、代码块等 Markdown 特定元素的定位。
    """
    
    # 资源路径正则表达式，支持 #meta、#item 等格式
    URI_PATH_PATTERN = re.compile(
        r"^(?:(?P<resource_type>[^/]+)(?:/(?P<resource_params>.+))?)?$"
    )
    
    def __init__(self):
        """初始化 Markdown URI 解析器。"""
        pass
    
    def parse_uri(self, uri: str) -> Optional[Dict[str, str]]:
        """解析资源路径。
        
        注意：这里只处理 / 之后的部分，文件标识符已经由上层处理
        支持的资源路径格式如：
        - #meta 或 #frontmatter         ：文件的 frontmatter
        - #item                         ：第一级标题
        - headText/subHeadText          ：嵌套标题
        - #test                         ：测试用例
        - headPath/#test                ：指定路径下的测试用例
        - #related                      ：frontmatter 中的链接
        - #link                         ：所有链接
        - headPath/#link                ：指定标题下的链接
        - headPath/#item                ：指定标题下的 sub  head
        - headPrefix                    ：标题前缀（如 CASE-1）
        - headText                      ：应理解为 匹配 或 部分匹配标题文本
        - headText/                     ：匹配标题文本(全部匹配)
        
        相应的，输出的 Token 可以分为

        - partialHead : 部分匹配标题
        - fullHead    : 完全匹配标题
        - resourceType: 资源类型
        
        对应的，返回值应为 [(token_type, value)] 的形式

        """
        if not uri:
            # 如果没有资源路径，则默认为整个文件
            return {"resource_type": "#file"}
            
        # 解析资源路径
        match = self.URI_PATH_PATTERN.match(uri)
        if not match:
            return None
        
        result = {}
        
        # 获取资源类型和参数
        resource_type = match.group("resource_type")
        resource_params_str = match.group("resource_params")
        
        # 如果没有资源类型，则默认为文件本身
        if not resource_type:
            result["resource_type"] = "#file"
            return result
        
        # 处理资源类型，支持 #meta 和 #frontmatter 作为同义词
        if resource_type == "#frontmatter":
            resource_type = "#meta"
            
        # 设置资源类型
        result["resource_type"] = resource_type
        
        # 处理 headPrefix 类型
        if resource_type == "#headPrefix" and resource_params_str:
            result["prefix_pattern"] = resource_params_str
        # 处理其他带参数的资源类型
        elif resource_params_str:
            result["resource_params"] = resource_params_str.split("/")
        
        return result
    
    def uri_to_query(self, uri: str) -> str:
        """将资源路径转换为 tree-sitter 查询字符串。
        
        Args:
            uri: 资源路径，如 "#meta"、"#item"、"headText/subHeadText" 等
            
        Returns:
            查询字符串
            
        Raises:
            ValueError: 当资源路径格式不正确或不支持的资源类型时抛出
        """
        parsed = self.parse_uri(uri)
        if not parsed:
            raise ValueError(f"无效的资源路径: {uri}")
        
        resource_type = parsed.get("resource_type", "")
        resource_params = parsed.get("resource_params", [])
        
        # 根据资源类型生成不同的查询
        if resource_type == "#meta":
            # 查询 frontmatter
            return self._markdown_frontmatter_query_template()
        elif resource_type == "#item":
            # 查询第一级标题
            return self._markdown_level1_heading_query_template()
        elif resource_type == "#test":
            # 查询测试用例
            return self._markdown_test_case_query_template()
        elif resource_type == "headPrefix":
            # 查询带有特定前缀的标题
            prefix_pattern = parsed.get("prefix_pattern")
            if prefix_pattern:
                return self._markdown_heading_prefix_query_template(prefix_pattern)
        elif resource_type == "#link":
            # 查询链接
            if resource_params and resource_params[0] == "#meta":
                return self._markdown_frontmatter_link_query_template()
            return self._markdown_link_query_template()
        elif resource_type == "#file":
            # 查询整个文件
            return self._markdown_file_query_template()
        else:
            # 其他资源类型可能是标题文本
            if resource_params:
                # 处理嵌套标题的情况
                return self._markdown_nested_heading_query_template(resource_type, resource_params)
            else:
                # 处理单个标题的情况
                return self._markdown_heading_query_template(resource_type)
        
        raise ValueError(f"不支持的资源类型或缺少必要参数: {uri}")

    
    def resolve(self, uri: str, parsed_document: DocumentProtocol) -> List[DocumentItem]:
        """将资源路径解析为 Markdown 特定的文档项列表。
        
        Args:
            uri: 资源路径，如 "#meta"、"#item"、"headText/subHeadText" 等
            parsed_document: 已解析的文档对象
            
        Returns:
            解析后的文档项列表
            
        Raises:
            ValueError: 当资源路径格式不正确或不支持的资源类型时抛出
        """
        if not parsed_document:
            raise ValueError("parsed_document 参数不能为 None")
        parsed = self.parse_uri(uri)
        if not parsed:
            raise ValueError(f"无效的资源路径: {uri}")
        
        resource_type = parsed.get("resource_type", "")
        resource_params = parsed.get("resource_params", [])
        
        # 创建结果列表
        results = []
        
        # 根据资源类型生成不同的结果
        if resource_type == "#meta":
            # 处理 frontmatter
            query_string = self._markdown_frontmatter_query_template()
            
            if parsed_document:
                try:
                    # 直接使用文档对象的查询方法
                    query_results = parsed_document.query(query_string)
                    
                    # 如果找到了 frontmatter
                    if query_results and len(query_results) > 0:
                        for result in query_results:
                            if result.get("name") == "frontmatter":
                                node = result.get("node")
                                if node:
                                    # 获取准确的位置信息
                                    start_point = (node.start_point[0], node.start_point[1])
                                    end_point = (node.end_point[0], node.end_point[1])
                                    
                                    # 使用文档对象的 get_text 方法获取文本
                                    text = parsed_document.get_text(start_point, end_point)
                                    
                                    # 如果没有文本内容，直接返回空字符串
                                    if not text:
                                        meta_content = ""
                                    else:
                                        # 处理元数据内容，去除 --- 分隔符，提取实际的键值对
                                        clean_text = text.strip()
                                        if clean_text.startswith('---') and '---' in clean_text[3:]:
                                            # 提取 --- 之间的内容
                                            meta_content = clean_text[3:].split('---', 1)[0].strip()
                                        else:
                                            meta_content = clean_text
                                
                                    results.append(self._create_document_item(
                                        node_name="frontmatter",
                                        item_type=ItemType.METADATA,
                                        text=meta_content,  # 使用处理后的元数据内容
                                        start_point=start_point,
                                        end_point=end_point,
                                        metadata={
                                            "query": query_string,
                                            "node": node
                                        }
                                    ))
                                else:
                                    # 如果没有节点信息，使用默认值
                                    results.append(self._create_document_item(
                                        node_name="frontmatter",
                                        item_type=ItemType.METADATA,
                                        text=result.get("text", ""),
                                        start_point=result.get("start_point", (0, 0)),
                                        end_point=result.get("end_point", (0, 0)),
                                        metadata={
                                            "query": query_string
                                        }
                                    ))
                except Exception as e:
                    # 如果查询失败，记录错误但不中断执行
                    print(f"查询 frontmatter 时出错: {str(e)}")
                    # 继续使用默认项
            
            # 如果没有提供解析器或文档，或者没有找到结果，返回空元数据项
            if not results:
                results.append(self._create_document_item(
                    node_name="frontmatter",
                    item_type=ItemType.METADATA,
                    text="",  # 不提供默认文本
                    start_point=(0, 0),
                    end_point=(0, 0),
                    metadata={
                        "query": query_string,
                        "empty": True
                    }
                ))
        elif resource_type == "#item":
            # 处理第一级标题
            results.append(self._create_document_item(
                node_name="level1_heading",
                item_type=ItemType.HEADING,
                text="第一级标题",
                start_point=(0, 0),
                end_point=(0, 0),
                metadata={
                    "query": self._markdown_level1_heading_query_template()
                }
            ))
        elif resource_type == "#test":
            # 处理测试用例
            results.append(self._create_document_item(
                node_name="test_case",
                item_type=ItemType.TEST_CASE,
                text="测试用例",
                start_point=(0, 0),
                end_point=(0, 0),
                metadata={
                    "query": self._markdown_test_case_query_template()
                }
            ))
        elif resource_type == "headPrefix":
            # 处理带有特定前缀的标题
            prefix_pattern = parsed.get("prefix_pattern")
            if prefix_pattern:
                results.append(self._create_document_item(
                    node_name=f"prefix_{prefix_pattern}",
                    item_type=ItemType.HEADING,
                    text=f"带有前缀 {prefix_pattern} 的标题",
                    start_point=(0, 0),
                    end_point=(0, 0),
                    metadata={
                        "prefix": prefix_pattern,
                        "query": self._markdown_heading_prefix_query_template(prefix_pattern)
                    }
                ))
        elif resource_type == "#link":
            # 处理链接
            if resource_params and resource_params[0] == "#meta":
                results.append(self._create_document_item(
                    node_name="frontmatter_link",
                    item_type=ItemType.LINK,
                    text="frontmatter 中的链接",
                    start_point=(0, 0),
                    end_point=(0, 0),
                    metadata={
                        "query": self._markdown_frontmatter_link_query_template()
                    }
                ))
            else:
                results.append(self._create_document_item(
                    node_name="link",
                    item_type=ItemType.LINK,
                    text="文档中的链接",
                    start_point=(0, 0),
                    end_point=(0, 0),
                    metadata={
                        "query": self._markdown_link_query_template()
                    }
                ))
        elif resource_type == "#file":
            # 处理整个文件
            results.append(self._create_document_item(
                node_name="file",
                item_type=ItemType.DOCUMENT,
                text="整个文件",
                start_point=(0, 0),
                end_point=(0, 0),
                metadata={
                    "query": self._markdown_file_query_template()
                }
            ))
        else:
            # 其他资源类型可能是标题文本
            if resource_params:
                # 处理嵌套标题
                parent_heading = resource_type
                child_heading = resource_params[0]
                results.append(self._create_document_item(
                    node_name=f"{parent_heading}_{child_heading}",
                    item_type=ItemType.HEADING,
                    text=f"标题 {child_heading} (父标题: {parent_heading})",
                    start_point=(0, 0),
                    end_point=(0, 0),
                    metadata={
                        "parent_heading": parent_heading,
                        "child_heading": child_heading,
                        "query": self._markdown_nested_heading_query_template(parent_heading, resource_params)
                    }
                ))
            else:
                # 处理单个标题
                results.append(self._create_document_item(
                    node_name=resource_type,
                    item_type=ItemType.HEADING,
                    text=f"标题 {resource_type}",
                    start_point=(0, 0),
                    end_point=(0, 0),
                    metadata={
                        "query": self._markdown_heading_query_template(resource_type)
                    }
                ))
        
        return results
    
    def _create_document_item(self, node_name: str, item_type: ItemType, text: str, 
                             start_point: Tuple[int, int], end_point: Tuple[int, int], 
                             metadata: Optional[Dict[str, Any]] = None,
                             children: Optional[List[DocumentItem]] = None) -> DocumentItem:
        """创建文档项。
        
        Args:
            node_name: 节点名称
            item_type: 项目类型
            text: 项目文本表示
            start_point: 起始位置（行，列）
            end_point: 结束位置（行，列）
            metadata: 可选的元数据
            children: 可选的子项列表
            
        Returns:
            新创建的文档项
        """
        item = DocumentItem(
            node_name=node_name,
            item_type=item_type,
            text=text,
            start_point=start_point,
            end_point=end_point,
            metadata=metadata or {}
        )
        
        # 添加子项
        if children:
            for child in children:
                item.add_child(child)
                
        return item
    
    def _markdown_heading_query_template(self, heading_text: str) -> str:
        """生成 Markdown 标题查询模板。
        
        Args:
            heading_text: 标题文本
            
        Returns:
            查询字符串
        """
        return f"""
        (
          (atx_heading
            (atx_heading_marker)
            (heading_content) @heading_content)
          (#match? @heading_content ".*{heading_text}.*")
        )
        """
    
    def _markdown_level1_heading_query_template(self) -> str:
        """生成 Markdown 第一级标题查询模板。
        
        Returns:
            查询字符串
        """
        return """
        (
          (atx_heading
            (atx_heading_marker) @marker
            (heading_content))
          (#eq? @marker "#")
        )
        """
    
    def _markdown_nested_heading_query_template(self, parent_heading: str, child_headings: List[str]) -> str:
        """生成嵌套标题查询模板。
        
        Args:
            parent_heading: 父标题文本
            child_headings: 子标题文本列表
            
        Returns:
            查询字符串
        """
        child_heading = child_headings[0] if child_headings else ""
        return f"""
        (
          (document
            (atx_heading
              (atx_heading_marker)
              (heading_content) @parent_heading
              (#match? @parent_heading ".*{parent_heading}.*"))
            .+
            (atx_heading
              (atx_heading_marker)
              (heading_content) @child_heading
              (#match? @child_heading ".*{child_heading}.*")))
        )
        """
    
    def _markdown_frontmatter_query_template(self) -> str:
        """生成 Markdown frontmatter 查询模板。
        
        Returns:
            查询字符串
        """
        return """
        (
          (document
            (minus_metadata) @frontmatter)
        )
        """
    
    def _markdown_test_case_query_template(self, case_id: str = None) -> str:
        """生成 Markdown 测试用例查询模板。
        
        Args:
            case_id: 可选的测试用例 ID
            
        Returns:
            查询字符串
        """
        if case_id:
            return f"""
            (
              (atx_heading
                (atx_heading_marker)
                (heading_content) @heading_content)
              (#match? @heading_content "{case_id}")
            )
            """
        else:
            # 匹配 CASE-* 或 TST-* 格式的测试用例标题
            return """
            (
              (atx_heading
                (atx_heading_marker)
                (heading_content) @heading_content)
              (#match? @heading_content "(CASE-|TST-)\\w+")
            )
            """
    
    def _markdown_heading_prefix_query_template(self, prefix: str) -> str:
        """生成带有特定前缀的标题查询模板。
        
        Args:
            prefix: 标题前缀
            
        Returns:
            查询字符串
        """
        return f"""
        (
          (atx_heading
            (atx_heading_marker)
            (heading_content) @heading_content)
          (#match? @heading_content "(\\[{prefix}[^\\]]*\\]|{prefix}[^:]*:).*")
        )
        """
    
    def _markdown_link_query_template(self) -> str:
        """生成 Markdown 链接查询模板。
        
        Returns:
            查询字符串
        """
        return """
        (
          (link) @link
        )
        """
    
    def _markdown_frontmatter_link_query_template(self) -> str:
        """生成 Markdown frontmatter 中的链接查询模板。
        
        Returns:
            查询字符串
        """
        return """
        (
          (document
            (frontmatter
              (pair
                key: (_) @key
                value: (_) @value
                (#match? @key ".*link.*"))))
        )
        """
    
    def _markdown_file_query_template(self) -> str:
        """生成整个 Markdown 文件的查询模板。
        
        Returns:
            查询字符串
        """
        return """
        (
          (document) @document
        )
        """
    
    def _markdown_content_query_template(self, content: str) -> str:
        """生成 Markdown 内容查询模板。
        
        Args:
            content: 要查找的内容
            
        Returns:
            查询字符串
        """
        return f"""
        (
          [
            (paragraph) @para
            (atx_heading) @heading
            (fenced_code_block) @code_block
          ]
          (#match? @para ".*{content}.*")
          (#match? @heading ".*{content}.*")
          (#match? @code_block ".*{content}.*")
        )
        """
    
    def _markdown_code_block_query_template(self, language: Optional[str] = None) -> str:
        """生成 Markdown 代码块查询模板。
        
        Args:
            language: 可选的代码块语言
            
        Returns:
            查询字符串
        """
        if language:
            return f"""
            (
              (fenced_code_block
                (info_string) @info
                (#match? @info "{language}"))
            )
            """
        else:
            return """
            (
              (fenced_code_block) @code_block
            )
            """
