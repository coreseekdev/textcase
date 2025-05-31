"""
Python 语言特定的 URI 解析器。

提供针对 Python 代码的资源引用解析和查询生成功能。
"""

import re
from typing import Dict, List, Optional, Any, Tuple

from .resolver import Resolver, DocumentItem, ItemType, ResolverProtocol
from .document import DocumentProtocol


class PythonResolver(Resolver, ResolverProtocol):
    """
Python 语言特定的 URI 解析器。
    
    针对 Python 代码提供更精确的资源引用解析和查询生成。
    支持函数、类、方法、变量等 Python 特定元素的定位。
    """
    
    # 资源引用正则表达式
    # 匹配 [@type:identifier](path#anchor) 格式
    URI_PATTERN = re.compile(
        r'\[@(?P<type>[a-z]+):(?P<identifier>[^\]]+)\]'
        r'\((?P<path>[^#\)]+)(?:#(?P<anchor>[^\)]+))?\)'
    )
    
    def __init__(self):
        """初始化 Python URI 解析器。"""
        pass
        
    def parse_uri(self, uri: str) -> Optional[Dict[str, str]]:
        """解析资源引用 URI。
        
        Args:
            uri: 资源引用 URI，格式为 [@type:identifier](path#anchor)
            
        Returns:
            解析结果字典，包含 type, identifier, path, anchor 字段；
            如果解析失败，则返回 None
        """
        match = self.URI_PATTERN.match(uri)
        if not match:
            return None
            
        return match.groupdict()
    
    def uri_to_query(self, uri: str) -> str:
        """将资源引用 URI 转换为 tree-sitter 查询字符串。
        
        Args:
            uri: 资源引用 URI，格式为 [@type:identifier](path#anchor)
            
        Returns:
            查询字符串
            
        Raises:
            ValueError: 当 URI 格式不正确或不支持的资源类型时抛出
        """
        parsed = self.parse_uri(uri)
        if not parsed:
            raise ValueError(f"无效的资源引用 URI: {uri}")
            
        resource_type = parsed.get("type", "")
        anchor = parsed.get("anchor", "")
        identifier = parsed.get("identifier", "")
        
        # 根据资源类型生成查询
        if resource_type == "code":
            if anchor:
                # 检查是否包含类方法分隔符
                if "." in anchor:
                    class_name, method_name = anchor.split(".", 1)
                    return self._python_method_query_template(class_name, method_name)
                # 检查是否可能是类定义
                elif anchor[0].isupper():
                    return self._python_class_query_template(anchor)
                else:
                    # 默认假设是函数定义
                    return self._python_function_query_template(anchor)
            elif identifier:
                return self._python_identifier_query_template(identifier)
        
        raise ValueError(f"不支持的资源类型或缺少必要参数: {resource_type}")
    
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
    
    def resolve(self, uri: str, parsed_document: DocumentProtocol) -> List[DocumentItem]:
        """将资源路径解析为 Python 特定的文档项列表。
        
        Args:
            uri: 资源路径，如 "#class"、"#function"、"module.class" 等
            parsed_document: 已解析的文档对象
            
        Returns:
            解析后的文档项列表
            
        Raises:
            ValueError: 当资源路径格式不正确或不支持的资源类型时抛出
        """
        if not parsed_document:
            raise ValueError("parsed_document 参数不能为 None")
        
        # 首先解析 URI
        parsed = self.parse_uri(uri)
        if not parsed:
            raise ValueError(f"无效的资源引用 URI: {uri}")
        
        # 获取资源类型和其他信息
        resource_type = parsed.get("type", "")
        identifier = parsed.get("identifier", "")
        anchor = parsed.get("anchor", "")
        
        # 创建一个空的结果列表
        results = []
        
        # 根据资源类型和锚点生成不同的文档项
        if resource_type == "code":
            # 如果有锚点，可能是函数、类或方法
            if anchor:
                # 检查是否包含类方法分隔符
                if "." in anchor:
                    class_name, method_name = anchor.split(".", 1)
                    # 创建一个方法文档项
                    results.append(self._create_document_item(
                        node_name=method_name,
                        item_type=ItemType.METHOD,
                        text=f"方法 {method_name} 在类 {class_name} 中",
                        start_point=(0, 0),  # 实际位置需要从解析结果中获取
                        end_point=(0, 0),    # 实际位置需要从解析结果中获取
                        metadata={
                            "class_name": class_name,
                            "method_name": method_name,
                            "query": self._python_method_query_template(class_name, method_name)
                        }
                    ))
                # 检查是否可能是类定义
                elif anchor[0].isupper():
                    # 创建一个类文档项
                    results.append(self._create_document_item(
                        node_name=anchor,
                        item_type=ItemType.CLASS,
                        text=f"类 {anchor}",
                        start_point=(0, 0),  # 实际位置需要从解析结果中获取
                        end_point=(0, 0),    # 实际位置需要从解析结果中获取
                        metadata={
                            "class_name": anchor,
                            "query": self._python_class_query_template(anchor)
                        }
                    ))
                else:
                    # 默认假设是函数定义
                    results.append(self._create_document_item(
                        node_name=anchor,
                        item_type=ItemType.FUNCTION,
                        text=f"函数 {anchor}",
                        start_point=(0, 0),  # 实际位置需要从解析结果中获取
                        end_point=(0, 0),    # 实际位置需要从解析结果中获取
                        metadata={
                            "function_name": anchor,
                            "query": self._python_function_query_template(anchor)
                        }
                    ))
            # 如果没有锚点但有标识符，可能是变量或其他引用
            elif identifier:
                results.append(self._create_document_item(
                    node_name=identifier,
                    item_type=ItemType.VARIABLE,
                    text=f"标识符 {identifier}",
                    start_point=(0, 0),  # 实际位置需要从解析结果中获取
                    end_point=(0, 0),    # 实际位置需要从解析结果中获取
                    metadata={
                        "identifier": identifier,
                        "query": self._python_identifier_query_template(identifier)
                    }
                ))
        
        return results
    
    def _python_function_query_template(self, function_name: str) -> str:
        """生成 Python 函数查询模板。
        
        Args:
            function_name: 函数名称
            
        Returns:
            查询字符串
        """
        return f"""
        (
          (function_definition
            name: (identifier) @function_name
            (#eq? @function_name "{function_name}"))
        )
        """
    
    def _python_class_query_template(self, class_name: str) -> str:
        """生成 Python 类查询模板。
        
        Args:
            class_name: 类名称
            
        Returns:
            查询字符串
        """
        return f"""
        (
          (class_definition
            name: (identifier) @class_name
            (#eq? @class_name "{class_name}"))
        )
        """
    
    def _python_method_query_template(self, class_name: str, method_name: str) -> str:
        """生成 Python 类方法查询模板。
        
        Args:
            class_name: 类名称
            method_name: 方法名称
            
        Returns:
            查询字符串
        """
        return f"""
        (
          (class_definition
            name: (identifier) @class_name
            body: (block 
              (function_definition
                name: (identifier) @method_name)))
          (#eq? @class_name "{class_name}")
          (#eq? @method_name "{method_name}")
        )
        """
    
    def _python_identifier_query_template(self, identifier: str) -> str:
        """生成 Python 标识符查询模板。
        
        Args:
            identifier: 标识符
            
        Returns:
            查询字符串
        """
        return f"""
        (
          (identifier) @id
          (#eq? @id "{identifier}")
        )
        """
