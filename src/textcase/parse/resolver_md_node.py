"""
Markdown 特定的语义节点构建器。

提供针对 Markdown 文档的语义节点构建功能，优化对 Markdown 特定元素的处理。
"""

from typing import Dict, List, Optional, Any, Tuple

from .document import DocumentProtocol, Node
from .resolver import DefaultSemanticNodeBuilder, SemanticNode, NodeType


class MarkdownSemanticNodeBuilder(DefaultSemanticNodeBuilder):
    """
    Markdown 特定的语义节点构建器。
    
    继承自默认构建器，但针对 Markdown 文档的特性进行了优化，
    能够更好地处理标题、列表项、代码块等 Markdown 特定元素。
    """
    
    def create_node(self, node_type: NodeType, node: Optional[Node] = None, 
                   metadata: Optional[Dict[str, Any]] = None) -> SemanticNode:
        """
        创建一个新的 Markdown 语义节点。
        
        根据节点类型应用 Markdown 特定的处理逻辑，例如对标题、列表项等的特殊处理。
        
        Args:
            node_type: 节点类型
            node: 可选的tree-sitter节点，如果提供则关联到新节点
            metadata: 可选的元数据字典
            
        Returns:
            创建的语义节点
        """
        # 初始化元数据字典
        meta_dict = {}
        if metadata:
            meta_dict.update(metadata)
        
        # 如果提供了 tree-sitter 节点，使用其位置和类型信息
        start_point = (0, 0)
        end_point = (0, 0)
        
        if node:
            start_point = (node.start_point[0], node.start_point[1])
            end_point = (node.end_point[0], node.end_point[1])
            meta_dict["original_node_type"] = node.type
        
        # 创建语义节点
        semantic_node = SemanticNode(
            node_type=node_type,
            start_point=start_point,
            end_point=end_point,
            metadata=meta_dict
        )
        
        # 如果提供了 tree-sitter 节点，添加到语义节点
        if node:
            semantic_node.add_ts_node(node)
            
            # 根据节点类型应用特定处理
            if node_type == NodeType.HEADING:
                # 从标题节点中提取级别和文本内容
                self._process_heading_node(semantic_node, node)
            elif node_type == NodeType.LIST_ITEM:
                # 处理列表项，检测是否是任务列表项
                self._process_list_item_node(semantic_node, node)
            elif node_type == NodeType.CODE_BLOCK:
                # 处理代码块，提取语言信息
                self._process_code_block_node(semantic_node, node)
            elif node_type == NodeType.SECTION:
                # 处理 section 节点，提取标题信息
                self._process_section_node(semantic_node, node)
        
        return semantic_node
    
    def create_child_node(self, parent: SemanticNode, node_type: NodeType, 
                         node: Optional[Node] = None, 
                         metadata: Optional[Dict[str, Any]] = None) -> SemanticNode:
        """
        创建一个新的子语义节点并添加到父节点。
        
        Args:
            parent: 父节点
            node_type: 子节点类型
            node: 可选的tree-sitter节点，如果提供则关联到新节点
            metadata: 可选的元数据字典
            
        Returns:
            创建的子语义节点
        """
        # 创建子节点
        child_node = parent.create_child(node_type, node, metadata)
        
        # 根据节点类型应用特定处理
        if node:
            if node_type == NodeType.HEADING:
                self._process_heading_node(child_node, node)
            elif node_type == NodeType.LIST_ITEM:
                self._process_list_item_node(child_node, node)
            elif node_type == NodeType.CODE_BLOCK:
                self._process_code_block_node(child_node, node)
            elif node_type == NodeType.SECTION:
                self._process_section_node(child_node, node)
        
        return child_node
    
    def _process_heading_node(self, semantic_node: SemanticNode, node: Node) -> None:
        """
        处理标题节点，提取级别和文本内容。
        
        Args:
            semantic_node: 语义节点
            node: tree-sitter节点
        """
        # 提取标题级别（通过计算 # 的数量）
        heading_level = 0
        for child in node.children:
            if child.type == "atx_heading_marker":
                heading_level = len(child.text.decode('utf-8').strip())
                break
        
        # 提取标题文本
        title_text = ""
        for child in node.children:
            if child.type == "inline":
                title_text = child.text.decode('utf-8').strip()
                break
        
        # 更新节点元数据
        semantic_node.metadata.update({
            "heading_level": heading_level,
            "title_text": title_text,
            "node_name": title_text  # 使用标题文本作为节点名称
        })
    
    def _process_list_item_node(self, semantic_node: SemanticNode, node: Node) -> None:
        """
        处理列表项节点，检测是否是任务列表项。
        
        Args:
            semantic_node: 语义节点
            node: tree-sitter节点
        """
        # 检查是否是任务列表项（包含 [ ] 或 [x] 的列表项）
        is_task_item = False
        task_completed = False
        item_text = ""
        
        # 遍历节点的子节点，查找任务列表标记
        for child in node.children:
            if child.type == "task_list_marker_unchecked":
                is_task_item = True
                task_completed = False
            elif child.type == "task_list_marker_checked":
                is_task_item = True
                task_completed = True
            
            # 提取列表项文本
            if child.type == "paragraph":
                item_text = child.text.decode('utf-8').strip()
        
        # 更新节点元数据
        semantic_node.metadata.update({
            "is_task_item": is_task_item,
            "task_completed": task_completed if is_task_item else None,
            "item_text": item_text,
            "node_name": item_text[:30] + "..." if len(item_text) > 30 else item_text
        })
    
    def _process_code_block_node(self, semantic_node: SemanticNode, node: Node) -> None:
        """
        处理代码块节点，提取语言信息。
        
        Args:
            semantic_node: 语义节点
            node: tree-sitter节点
        """
        # 提取代码块语言
        language = None
        code_content = ""
        
        for child in node.children:
            if child.type == "info_string":
                language = child.text.decode('utf-8').strip()
            elif child.type == "code_fence_content":
                code_content = child.text.decode('utf-8')
        
        # 更新节点元数据
        semantic_node.metadata.update({
            "language": language,
            "code_content": code_content,
            "node_name": f"Code Block ({language})" if language else "Code Block"
        })
    
    def _process_section_node(self, semantic_node: SemanticNode, node: Node) -> None:
        """
        处理 section 节点，提取标题信息。
        
        Args:
            semantic_node: 语义节点
            node: tree-sitter节点
        """
        # 查找 section 的标题节点
        heading_node = None
        for child in node.children:
            if child.type == "atx_heading":
                heading_node = child
                break
        
        if heading_node:
            # 提取标题文本
            title_text = ""
            for child in heading_node.children:
                if child.type == "inline":
                    title_text = child.text.decode('utf-8').strip()
                    break
            
            # 提取标题级别
            heading_level = 0
            for child in heading_node.children:
                if child.type == "atx_heading_marker":
                    heading_level = len(child.text.decode('utf-8').strip())
                    break
            
            # 更新节点元数据
            semantic_node.metadata.update({
                "section_title": title_text,
                "heading_level": heading_level,
                "node_name": title_text  # 使用标题文本作为节点名称
            })
