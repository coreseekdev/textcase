# Copyright 2025 coreseek.com
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
"""LLM provider base classes and response implementations.

This module contains the base classes for LLM providers and response objects.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List, AsyncGenerator

from src.textcase.proto.llm import LLMResponseProtocol, LLMProviderProtocol


class LLMResponse(LLMResponseProtocol):
    """Standard implementation of LLM response.
    
    This class provides a concrete implementation of the LLMResponseProtocol.
    """
    
    def __init__(self, content: str, model: str, provider: str, metadata: Optional[Dict[str, Any]] = None):
        """Initialize LLM response.
        
        Args:
            content: The generated text content
            model: The model used for generation
            provider: The provider used for generation
            metadata: Optional metadata dictionary
        """
        self._content = content
        self._model = model
        self._provider = provider
        self._metadata = metadata or {}
    
    @property
    def content(self) -> str:
        """Get the response content.
        
        Returns:
            The generated text content
        """
        return self._content
    
    @property
    def model(self) -> str:
        """Get the model used for generation.
        
        Returns:
            The model name
        """
        return self._model
    
    @property
    def provider(self) -> str:
        """Get the provider used for generation.
        
        Returns:
            The provider name
        """
        return self._provider
    
    @property
    def metadata(self) -> Dict[str, Any]:
        """Get response metadata.
        
        Returns:
            Dictionary containing metadata like token counts, timing, etc.
        """
        return self._metadata
    
    def __str__(self) -> str:
        """String representation of the response.
        
        Returns:
            The response content
        """
        return self._content
    
    def __repr__(self) -> str:
        """Detailed string representation of the response.
        
        Returns:
            Detailed representation including model and provider info
        """
        return f"LLMResponse(model='{self._model}', provider='{self._provider}', content_length={len(self._content)})"


class LLMProvider(ABC, LLMProviderProtocol):
    """Abstract base class for LLM providers.
    
    This class provides a base implementation of the LLMProviderProtocol
    with common functionality and helper methods.
    """
    
    def __init__(self, provider_name: str):
        """Initialize LLM provider.
        
        Args:
            provider_name: The name of this provider
        """
        self._provider_name = provider_name
    
    @property
    def provider_name(self) -> str:
        """Get the provider name.
        
        Returns:
            The name of this provider
        """
        return self._provider_name
    
    @property
    @abstractmethod
    def supported_models(self) -> List[str]:
        """Get list of supported models.
        
        Returns:
            List of model names supported by this provider
        """
        pass
    
    @abstractmethod
    async def generate(self, prompt: str, model: str, **kwargs) -> LLMResponse:
        """Generate a response from the LLM.
        
        Args:
            prompt: The input prompt
            model: The model to use for generation
            **kwargs: Additional provider-specific parameters
            
        Returns:
            LLMResponse object containing the response
        """
        pass
    
    @abstractmethod
    async def generate_stream(self, prompt: str, model: str, **kwargs) -> AsyncGenerator[str, None]:
        """Generate a streaming response from the LLM.
        
        Args:
            prompt: The input prompt
            model: The model to use for generation
            **kwargs: Additional provider-specific parameters
            
        Yields:
            Chunks of generated text
        """
        pass
    
    def supports_model(self, model: str) -> bool:
        """Check if the provider supports a specific model.
        
        Args:
            model: The model name to check
            
        Returns:
            True if the model is supported, False otherwise
        """
        return model in self.supported_models
    
    @classmethod
    @abstractmethod
    def from_config(cls, config: Dict[str, Any]) -> 'LLMProvider':
        """Create provider instance from configuration.
        
        Args:
            config: Configuration dictionary
            
        Returns:
            Provider instance
        """
        pass
