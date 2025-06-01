#!/usr/bin/env python3
"""
演示如何使用Tree-sitter的section嵌套结构实现路径模式匹配。
这对实现REQ014中的资源引用系统很有帮助。
"""

import sys
from textcase.parse.parser import Parser
from textcase.parse.document_type import DocumentType

def build_path_query(path_components):
    """
    构建一个SCM查询，用于匹配指定的标题路径。
    
    Args:
        path_components: 路径组件列表，例如 ["Section 1", "Subsection 1.1"]
        
    Returns:
        SCM查询字符串
    """
    if not path_components:
        return None
    
    # 构建最内层查询，使用#match谓词进行灵活匹配
    inner_query = """
    (section
      (atx_heading
        (inline) @title (#match? @title "(?i){title}.*"))
      (_)* @target_content)
    """.format(title=path_components[-1].lower())
    
    # 从倒数第二个路径组件开始，逐层向外包装查询
    for i in range(len(path_components) - 2, -1, -1):
        inner_query = """
        (section
          (atx_heading
            (inline) @title_{i} (#match? @title_{i} "(?i)^{title}$"))
          {inner})
        """.format(i=i, title=path_components[i], inner=inner_query)
    
    print(f"SCM查询字符串：\n{inner_query}")
    return inner_query

def find_content_by_path(parsed_doc, path):
    """
    根据标题路径查找内容。
    
    Args:
        parsed_doc: 解析后的文档
        path: 以"/"分隔的标题路径，例如 "Section 1/Subsection 1.1"
        
    Returns:
        匹配的内容列表
    """
    path_components = path.split("/")
    query_string = build_path_query(path_components)
    
    if not query_string:
        return []
    
    # 执行查询
    language = parsed_doc.language
    query = language.query(query_string)
    captures = query.captures(parsed_doc.tree.root_node)
    
    # 提取目标内容
    results = []
    if "target_content" in captures:
        for node in captures["target_content"]:
            results.append(node.text.decode('utf8'))
    
    return results

def main():
    if len(sys.argv) < 3:
        print(f"Usage: {sys.argv[0]} <markdown_file> <heading_path>")
        print(f"Example: {sys.argv[0]} sample_heading_structure.md 'Section 1/Subsection 1.1'")
        sys.exit(1)
    
    markdown_file = sys.argv[1]
    heading_path = sys.argv[2]
    
    try:
        # 读取文件内容
        with open(markdown_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 解析Markdown
        parser = Parser(document_type=DocumentType.MARKDOWN)
        parsed_doc = parser.parse(content)
        
        # 查找指定路径的内容
        results = find_content_by_path(parsed_doc, heading_path)
        
        if results:
            print(f"\n=== 找到路径 '{heading_path}' 的内容 ===\n")
            for i, content in enumerate(results):
                print(f"内容 {i+1}:\n{content}")
        else:
            print(f"未找到路径 '{heading_path}' 的内容")
        
    except Exception as e:
        print(f"错误: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
