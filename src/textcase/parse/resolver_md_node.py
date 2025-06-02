"""
Markdown 特定的语义节点构建器。

提供针对 Markdown 文档的语义节点构建功能，优化对 Markdown 特定元素的处理。
"""

from typing import Type, Dict, List, Optional, Any, Tuple
import yaml

from .document import DocumentProtocol, Node
from .resolver import DefaultSemanticNodeBuilder, SemanticNode, NodeType


class MarkdownMetadata(SemanticNode):

    def make_link(self, target: str, label: Optional[str] = None) -> bool:
        """Create a link from this document to the target document.
        
        Args:
            target: The target to link to
            label: Optional label for the link

        Returns:
            True if the link was successfully created, False otherwise
        """
        # 获取 frontmatter 内容
        fm_text = self.get_text(self.document)

        # 解析 frontmatter 内容 ， # FIXME: 后续应加入 mime type 的描述
        try:
            fm_data = yaml.safe_load(fm_text)
            if fm_data is None:
                fm_data = {}
        except Exception as e:
            print(f"Error parsing frontmatter: {e}")
            fm_data = {}
        
        # 初始化或更新 links 字典
        if 'links' not in fm_data:
            fm_data['links'] = {}
        
        # 更新目标的标签列表
        if target not in fm_data['links']:
            fm_data['links'][target] = [label] if label else []
        elif label and label not in fm_data['links'][target]:
            fm_data['links'][target].append(label)
        else:
            # 链接已存在，不需要更改， 应考虑处理为异常
            print(f"Link to {target} already exists")
            return True
        
        # 将更新后的 frontmatter 转换回 YAML 文本
        new_fm_text = yaml.dump(fm_data, default_flow_style=False, allow_unicode=True)
        new_fm_text = '---\n' + new_fm_text + '---\n'   # 需要额外加 frontmatter 的 marker.
        
        # 获取 frontmatter 节点在文件中的字节范围
        if len(self.ts_nodes) > 0:
            ts_node = self.ts_nodes[0]
            start_byte = ts_node.start_byte
            end_byte = ts_node.end_byte
            
            # 替换 frontmatter 部分, 注意，并不会实际替换文件内容，而是返回替换后的内容
            new_content = self.document.replace_bytes(
                start_byte,
                end_byte,
                new_fm_text.encode('utf-8')
            )
            self.document.update_content(new_content)
            return True
        else:
            raise NotImplementedError

        
    def get_links(self) -> Dict[str, List[str]]:
        """Get all links from this document.
        
        Returns:
            A dictionary mapping target keys to lists of labels
        """
        ...
    pass

class MarkdownSemanticNodeBuilder(DefaultSemanticNodeBuilder):
    """
    Markdown 特定的语义节点构建器。
    
    继承自默认构建器，但针对 Markdown 文档的特性进行了优化，
    能够更好地处理标题、列表项、代码块等 Markdown 特定元素。
    """
    
    def get_node_class(self, node_type: NodeType) -> Type['SemanticNode']:
        """
        获取指定节点类型的语义节点类。
        
        Args:
            node_type: 节点类型
            
        Returns:
            对应节点类型的语义节点类
        """
        if node_type == NodeType.METADATA:
            return MarkdownMetadata
        return SemanticNode