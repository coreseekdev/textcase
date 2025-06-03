"""LLM protocol package.

This package contains protocol interfaces for LLM and agent functionality.
"""

from __future__ import annotations

# Import all protocols from submodules
from .llm import (
    LLMResponseProtocol,
    LLMProviderProtocol
)

from .agent import (
    AgentProtocol,
    AgentFactoryProtocol
)

from .message import (
    MessageStore,
    Message,
    MessageOutput,
    MessageItem,
    FunctionCall,
    CodeExecutionOutput
)

# Re-export all symbols
__all__ = [
    # LLM protocols
    'LLMResponseProtocol',
    'LLMProviderProtocol',
    
    # Agent protocols
    'AgentProtocol',
    'AgentFactoryProtocol',
    
    # Message protocols
    'MessageStore',
    'Message',
    'MessageOutput',
    'MessageItem',
    'FunctionCall',
    'CodeExecutionOutput'
]
