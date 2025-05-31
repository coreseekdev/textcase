"""
Protocol definitions for LLM components.

This module defines the protocols (interfaces) for LLM components such as
LLMProvider, LLMResponse, Agent, and AgentFactory.
"""
from abc import abstractmethod
from pathlib import Path
from typing import Dict, List, Optional, Any, AsyncGenerator, Protocol, runtime_checkable, ClassVar

from .module import Project


@runtime_checkable
class LLMResponseProtocol(Protocol):
    """Protocol for LLM response objects."""
    
    content: str
    usage: Dict[str, Any]
    
    def __init__(self, content: str, usage: Optional[Dict[str, Any]] = None):
        """Initialize LLMResponse."""
        ...


@runtime_checkable
class LLMProviderProtocol(Protocol):
    """Protocol for LLM providers."""
    
    @abstractmethod
    async def generate(self, prompt: str, model: str, **kwargs) -> LLMResponseProtocol:
        """
        Generate a response from the LLM.
        
        Args:
            prompt: The prompt to send to the LLM
            model: The model to use
            **kwargs: Additional provider-specific parameters
            
        Returns:
            LLMResponse object containing the generated content
        """
        ...
    
    @abstractmethod
    async def generate_stream(self, prompt: str, model: str, **kwargs) -> AsyncGenerator[str, None]:
        """
        Generate a streaming response from the LLM.
        
        Args:
            prompt: The prompt to send to the LLM
            model: The model to use
            **kwargs: Additional provider-specific parameters
            
        Returns:
            AsyncGenerator yielding content chunks as they are generated
        """
        ...
    
    @classmethod
    @abstractmethod
    def from_config(cls, config: Dict[str, Any]) -> 'LLMProviderProtocol':
        """
        Create a provider instance from a configuration dictionary.
        
        Args:
            config: Configuration dictionary
            
        Returns:
            LLMProvider instance
        """
        ...
    
    @classmethod
    def load_config(cls, config_path: Path) -> Dict[str, Any]:
        """
        Load configuration from a YAML file with environment variable substitution.
        
        Args:
            config_path: Path to the configuration file
            
        Returns:
            Configuration dictionary with environment variables substituted
        """
        ...
