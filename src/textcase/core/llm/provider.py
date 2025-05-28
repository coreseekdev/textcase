"""
LLM Provider abstraction for textcase.
"""
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any, AsyncGenerator
import yaml
from pathlib import Path


class LLMResponse:
    """Response from an LLM."""
    
    def __init__(self, content: str, usage: Optional[Dict[str, Any]] = None):
        """Initialize LLMResponse."""
        self.content = content
        self.usage = usage or {}


class LLMProvider(ABC):
    """Abstract base class for LLM providers."""
    
    @abstractmethod
    async def generate(self, prompt: str, model: str, **kwargs) -> LLMResponse:
        """
        Generate a response from the LLM.
        
        Args:
            prompt: The prompt to send to the LLM
            model: The model to use
            **kwargs: Additional provider-specific parameters
            
        Returns:
            LLMResponse object containing the generated content
        """
        pass
    
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
        pass
    
    @classmethod
    @abstractmethod
    def from_config(cls, config: Dict[str, Any]) -> 'LLMProvider':
        """
        Create a provider instance from a configuration dictionary.
        
        Args:
            config: Configuration dictionary
            
        Returns:
            LLMProvider instance
        """
        pass
    
    @staticmethod
    def load_config(config_path: Path) -> Dict[str, Any]:
        """
        Load configuration from a YAML file.
        
        Args:
            config_path: Path to the configuration file
            
        Returns:
            Configuration dictionary
        """
        with open(config_path, 'r') as f:
            return yaml.safe_load(f)
