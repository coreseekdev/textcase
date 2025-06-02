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

        对于资源类型 rtype 包括

        - #meta
        - #item                     // 当前容器（文件|section）子节点
        - #test                     // (似乎不必要）过滤条件，满足的节点必须是可执行的测试用例
                                    // 1. 可以在实际执行前过滤
                                    // 2. 如果某个 TEST 包含多个不同的 sub-group 难以进一步定位
        - #related                  // frontmatter 中的链接
        - #link                     // 当前容器中 所有链接
                                    // 需要给出所在容器，以及所在容器的 URI
                                    // 如果是任务模式，实际预期是返回 link 所在的 listitem
        - #code                     // 当前容器中的代码块
        - #list                     // 当前容器中的列表, 进一步需要能够给出 listitem 
                                    // 例如，前述 test 的 sub-group 就可以加入 URI 定位 list
                                    // 当需要限定资源类型时，对应的 类型必须出现在 URI 中
                                    // 因为后续的定位，需要围绕该资源类型在展开
                                    // 需要能够识别是否是 task list 
        - #auto                     // 自动, 根据查询的结果，动态选择
        - #content                  // 用于匹配内容
        
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
        
        last_token_type, _ = result[-1]
        if last_token_type != "rtype":
            # 如果最后一个 token 不是 rtype，默认的 rtype 是 #item
            result.append(("rtype", "#item"))

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
        rtype, rvalue = tokens[-1]
        if rtype == "rtype" and rvalue in ["#meta", "#related"]:
            # 理论上应该检查之前的 path 为空，目前的代码处理为忽略之前的 path， 返回 frontmatter 查询
            return self._markdown_frontmatter_query_template(), rvalue

        # 处理后缀
        headPath = tokens[:-1]      # 去掉最后一个 token(资源类型)
        
        # 构造 headPath 查询
        query_string = self._build_path_query(headPath)
        if query_string is None:
            return None, rvalue
        
        return query_string, rvalue
        
    def _build_path_query(self, path_components: List[Tuple[str, str]]):
        """
        构建一个SCM查询，用于匹配指定的标题路径。
        
        Args:
            path_components: 路径组件列表，例如 ["Section 1", "Subsection 1.1"]
            exact_parent_match: 是否要求路径中间的标题精确匹配
            
        Returns:
            SCM查询字符串
        """
        if not path_components:
            return None
        
        # 构建最内层查询，使用#match谓词进行灵活匹配
        # 对于最后一个组件（目标标题），支持多种格式和编号风格
        last_match_type, last_component = path_components[-1]
        
        # 检查是否是带数字的标识符模式（如TC-01, REQ9等）
        import re
        id_pattern = re.compile(r'^([a-zA-Z_-]+)(\d+)$')
        match = id_pattern.match(last_component)
        
        # 处理标题中的特殊字符，确保正确转义
        def escape_for_regex(s):
            # 对于Tree-sitter查询中的正则表达式，需要特殊处理
            # 首先转义所有正则表达式特殊字符
            s = re.escape(s)
            s = s.replace("\\", "\\\\")
            return s

        r"""
        Ref: https://rdrr.io/cran/treesitter/man/query-matches-and-captures.html
        The regex support provided by ⁠#match?⁠ is powered by grepl().

        Escapes are a little tricky to get right within these match regex strings. 
        To use something like ⁠\s⁠ in the regex string, you need the literal text ⁠\\s⁠ to appear 
        in the string to tell the tree-sitter regex engine to escape the backslash 
        so you end up with just ⁠\s⁠ in the captured string. 
        This requires putting two literal backslash characters in the R string itself, 
        which can be accomplished with either "\\\\s" or using a raw string like r'["\\\\s"]' 
        which is typically a little easier. You can also write your queries 
        in a separate file (typically called queries.scm) and read them into R, 
        which is also a little more straightforward because you can just write something 
        like ⁠(#match? @id "^\\s$")⁠ and that will be read in correctly. 
        """

        if last_match_type == "partial":
            # 如果是部分匹配，才需要这么处理
            if match:
                # 提取前缀和数字部分
                prefix, number = match.groups()
                # 构造一个正则表达式，允许数字前有任意数量的0
                # 例如：TC-1, TC-01, TC-001都会匹配到TC-1
                # 添加边界条件，确保只匹配精确的标识符，例如TC-4不会匹配到TC-41
                title_pattern = f"(^|^\\\\[|^`|^\\\\s*){escape_for_regex(prefix)}0*{number}($|\\\\]|`|:|\\\\s|$).*"
            else:
                # 对于非数字标识符，使用更简单的匹配，但是根据语义，必须是 prefix 
                title_pattern = f"^\\\\s*{escape_for_regex(last_component)}.*" 
            # title_pattern = title_pattern.replace("\\", "\\\\") 
        else:
            # 对于完全匹配，使用精确匹配
            title_pattern = f"^{escape_for_regex(last_component)}$"
        
        inner_query = """
    (section
        (atx_heading
            (inline) @title (#match? @title "(?i){title_pattern}"))
        (_)* @target_content)
""".format(title_pattern=title_pattern)
        
        # 从倒数第二个路径组件开始，逐层向外包装查询
        for i in range(len(path_components) - 2, -1, -1):
            match_type, component = path_components[i]
            component = component.lower()
            
            # 对于父级和祖先标题，根据匹配类型决定是否要求精确匹配
            if match_type == "partial":
                # 部分匹配，允许标题包含指定组件
                title_pattern = f".*{escape_for_regex(component)}.*"
            else:
                # 精确匹配，要求标题完全匹配（不区分大小写）
                title_pattern = f"^{escape_for_regex(component)}$"
            
            # 对齐缩进
            inner_query = """(section
  (atx_heading
    (inline) @title_{i} (#match? @title_{i} "(?i){title_pattern}"))
  {inner})""".format(i=i, title_pattern=title_pattern, inner=inner_query)
        
        return inner_query

    
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
        query_results = []

        if query_string is None:
            # 如 uri == #item  则 query_string 为空
            # 对于 只有 rtype 的情况做特殊处理
            if rtype == "#item":
                ...
            if rtype == "#link":
                ...
            if rtype == "#test":
                ...
            
        query_results = parsed_document.query_as_list(query_string)
            

        if rtype == "#meta" or rtype == "#related":
            # #related 与 meta 类似，不同在与需要读取其 link 的内容
            # 为简化起见，不额外构造 Link 节点，交由外部处理
            for result_name, node in query_results:
                if result_name == "frontmatter":
                    # 创建语义节点
                    semantic_node = SemanticNode.from_ts_node(node, node_type=NodeType.METADATA)
                    semantic_node.add_offset((1, 0), (-1, 0))
                    results.append(semantic_node)
            ...
        return results
    
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
