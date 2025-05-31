"""
Markdown 文档特定的 URI 解析器。

提供针对 Markdown 文档的资源引用解析和查询生成功能。
"""

import re
from typing import Dict, List, Optional, Any, Tuple

from .parser import ParserProtocol
from .document import DocumentProtocol
from .resolver import ResolverProtocol, SemanticNode, NodeType


class MarkdownResolver(ResolverProtocol):
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
    
    def parse_uri(self, uri: Optional[str]) -> List[Tuple[str, str]]:
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

        - partial : 部分匹配标题
        - full    : 完全匹配标题
        - rtype   : 资源类型
        
        对应的，返回值应为 [(token_type, value)] 的形式

        """
        if uri is None:
            # 如果没有资源路径，则默认为整个文件
            return [("rtype", "#file")]
        
        result = []
        
        # 先根据 / 做切分
        parts = uri.split("/")

        # 遍历 parts
        last_full_index = -1
        for index, part in enumerate(parts):
            if part.startswith("#"):
                # 处理特殊资源类型
                if part in ["#meta", "#frontmatter"]:
                    # 统一处理为 #meta , #meta , #related 仅能出现在第一个
                    # 如果之前有值，忽略
                    result = [("rtype", "#meta")]
                elif part in ["#item", "#head"]:
                    result.append(("rtype", "#item"))
                elif part in ["#test", "#case"]:
                    result.append(("rtype", "#test"))
                elif part in ["#related", "#link"]:
                    if part == "#related":
                        result = [("rtype", "#related")]
                    else:
                        result.append(("rtype", part))
                else:
                    # 未知的特殊资源类型 , 是否需要报错？
                    result.append(("rtype", part))
                break   # 资源类型必须是最后一个，如果后面还有，忽略
            else:
                # 完全匹配标题文本
                result.append(("full", part.rstrip("/")))
                last_full_index = index
        
        # 找到最后一个 "full" 类型的位置
        
        # 如果找到了 "full" 类型的令牌
        if last_full_index >= 0:
            # 情况 1: 如果最后一个 "full" 后面是 "rtype"，则改为 "partial"
            if last_full_index < len(result) - 1 and result[last_full_index + 1][0] == "rtype":
                _, token_value = result[last_full_index]
                result[last_full_index] = ("partial", token_value)
            
            # 情况 2: 如果最后一个 "full" 同时也是最后一个令牌，且 URI 不以 / 结尾
            elif last_full_index == len(result) - 1 and not uri.endswith("/"):
                _, token_value = result[last_full_index]
                result[last_full_index] = ("partial", token_value)
        
        return result
    
    def uri_to_query(self, uri: str) -> Tuple[str, str]:
        """将资源路径转换为 tree-sitter 查询字符串。
        
        Args:
            uri: 资源路径，如 "#meta"、"#item"、"headText/subHeadText" 等
            
            1. 资源类型 token ，即 rtype 必须是最后一个，如果后续还有其他 token ，忽略
            2. #meta , #related 均为返回 frontmatter, 且仅能出现在第一个
        Returns:
            查询字符串
            uri 中剩余的部分
        Raises:
            ValueError: 当资源路径格式不正确或不支持的资源类型时抛出
        """
        tokens = self.parse_uri(uri)
        if not tokens or len(tokens) == 0:
            raise ValueError(f"无效的资源路径: {uri}")
        
        # 检查是否与 meta frontmatter 相关
        first_token_type, first_token_value = tokens[0]
        if first_token_type == "rtype" and first_token_value in ["#meta", "#related"]:
            # 返回 frontmatter 查询
            return self._markdown_frontmatter_query_template(), first_token_value

        # 处理后缀
        headPath = tokens
        last_token_type, _ = tokens[-1]
        if last_token_type == "rtype":
            headPath = headPath[:-1]
        
        # 构造 headPath 查询
        raise NotImplementedError

    
    def resolve(self, uri: str, parsed_document: DocumentProtocol) -> List[SemanticNode]:
        """将资源路径解析为 Markdown 特定的语义节点列表。
        
        Args:
            uri: 资源路径，如 "#meta"、"#item"、"headText/subHeadText" 等
            parsed_document: 已解析的文档对象
            
        Returns:
            解析后的语义节点列表
            
        Raises:
            ValueError: 当资源路径格式不正确或不支持的资源类型时抛出
        """
        if not parsed_document:
            raise ValueError("parsed_document 参数不能为 None")
        parsed = self.parse_uri(uri)
        if not parsed:
            raise ValueError(f"无效的资源路径: {uri}")
        
        query_string, rtype = self.uri_to_query(uri)
        results = []
        
        query_results = parsed_document.query_as_list(query_string)
        
        if rtype == "#meta":
            for result_name, node in query_results:
                if result_name == "frontmatter":
                    # 创建语义节点
                    semantic_node = SemanticNode.from_ts_node(node, node_type=NodeType.METADATA)
                    semantic_node.add_offset((1, 0), (-1, 0))
                    results.append(semantic_node)
                        
        return results
    
    def _create_semantic_node(self, node_name: str, node_type: NodeType, text: str, 
                          start_point: Tuple[int, int], end_point: Tuple[int, int], 
                          metadata: Optional[Dict[str, Any]] = None,
                          children: Optional[List[SemanticNode]] = None) -> SemanticNode:
        """创建语义节点。
        
        Args:
            node_name: 节点名称
            node_type: 节点类型
            text: 节点文本表示
            start_point: 起始位置（行，列）
            end_point: 结束位置（行，列）
            metadata: 可选的元数据
            children: 可选的子节点列表
            
        Returns:
            新创建的语义节点
        """
        node = SemanticNode(
            node_name=node_name,
            node_type=node_type,
            text=text,
            start_point=start_point,
            end_point=end_point,
            metadata=metadata or {}
        )
        
        # 添加子节点
        if children:
            for child in children:
                node.add_child(child)
                
        return node
    
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
        
        使用 tree-sitter 查询语法提取 frontmatter 内容，并通过 offset 指令
        去除 YAML 内容前后的 --- 分隔符。
        
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
