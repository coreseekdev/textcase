"""Item name generator for resource collections.

This module provides utilities for generating next available item names
with numeric numbering support and prefix filtering.
"""

from typing import List, Optional, Set, Tuple, Union
import re
from abc import ABC, abstractmethod
from ..proto.resource_collection_protocol import ItemNameGenerator


class NumericItemNameGenerator(ItemNameGenerator):
    """Generator for numeric item names with optional prefix support.
    
    This generator supports:
    - Integer numbering (001, 002, 003)
    - Decimal numbering (001.1, 001.2, 002.1)
    - Custom prefixes for filtering
    - Zero-padding configuration
    """
    
    def __init__(self, zero_padding: int = 3):
        """Initialize the generator.
        
        Args:
            zero_padding: Number of digits for zero-padding (e.g., 3 -> '001')
            allow_decimal: Whether to support decimal numbering (e.g., '001.1')
        """
        self.zero_padding = zero_padding
    
    def get_next_item_name(self, existing_items: List[str], prefix: str = '') -> str:
        """Generate the next available item name.
        
        Args:
            existing_items: List of existing item names in the collection
            prefix: Optional prefix to filter items. Examples:
                   - '' (empty): considers all numeric items
                   - '001.': considers items like '001.1', '001.2'
                   - 'REQ-': considers items like 'REQ-001', 'REQ-002'
        
        Returns:
            The next available item name as a string
            
        Examples:
            >>> generator = NumericItemNameGenerator(zero_padding=3)
            >>> generator.get_next_item_name(['001', '002', '005'])
            '006'
            >>> generator.get_next_item_name(['001.1', '001.2', '002'], '001.')
            '001.3'
        """
        if not existing_items:
            if prefix:
                return f"{prefix}1"
            return "1" if self.zero_padding <= 1 else "1".zfill(self.zero_padding)
        
        # Find all numeric values that match the prefix
        numeric_values = []
        for item in existing_items:
            numeric_part = self.get_numeric_part(item, prefix)
            if numeric_part is not None:
                numeric_values.append(numeric_part)
        
        if not numeric_values:
            # No matching items found, start from 1
            if prefix:
                return f"{prefix}1"
            return "1" if self.zero_padding <= 1 else "1".zfill(self.zero_padding)
        
        # Find the maximum value and increment
        max_value = max(numeric_values)
        
        # Handle decimal increment
        if prefix:
            return f"{prefix}{max_value + 1}"
        s = str(max_value + 1) 
        return s if self.zero_padding <= 1 else s.zfill(self.zero_padding)
    
    def get_numeric_part(self, item_name: str, prefix: str = '') -> Optional[int]:
        """Parse the numeric part from an item name.
        
        Args:
            item_name: The item name to parse
            prefix: Optional prefix to match
            
        Returns:
            The numeric value (int or float) if found, None otherwise
            
        Examples:
            >>> generator = NumericItemNameGenerator()
            >>> generator.parse_numeric_part('001', '')
            1
            >>> generator.parse_numeric_part('001.2', '001.')
            2.0
            >>> generator.parse_numeric_part('REQ-005', 'REQ-')
            5
        """
        if prefix:
            if not item_name.startswith(prefix):
                return None
            numeric_str = item_name[len(prefix):]
        else:
            numeric_str = item_name
        
        # Try to parse as integer first
        if numeric_str.isdigit():
            return int(numeric_str)
        return None
