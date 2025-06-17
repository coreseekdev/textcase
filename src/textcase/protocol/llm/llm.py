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
"""LLM component protocols.

This module defines the protocols for LLM components including
response objects and provider interfaces.
"""

from typing import Protocol, AsyncGenerator, Dict, Any, Optional, List
from abc import abstractmethod


class LLMResponseProtocol(Protocol):
    """Protocol for LLM response objects.
    
    Defines the interface that LLM response objects should implement.
    """
    
    @property
    def content(self) -> str:
        """Get the response content.
        
        Returns:
            The generated text content
        """
        ...
    
    @property
    def model(self) -> str:
        """Get the model used for generation.
        
        Returns:
            The model name
        """
        ...
    
    @property
    def provider(self) -> str:
        """Get the provider used for generation.
        
        Returns:
            The provider name
        """
        ...
    
    @property
    def metadata(self) -> Dict[str, Any]:
        """Get response metadata.
        
        Returns:
            Dictionary containing metadata like token counts, timing, etc.
        """
        ...


class LLMProviderProtocol(Protocol):
    """Protocol for LLM provider implementations.
    
    Defines the interface that LLM providers should implement.
    """
    
    @property
    def provider_name(self) -> str:
        """Get the provider name.
        
        Returns:
            The name of this provider
        """
        ...
    
    @property
    def supported_models(self) -> List[str]:
        """Get list of supported models.
        
        Returns:
            List of model names supported by this provider
        """
        ...
    
    @abstractmethod
    async def generate(self, prompt: str, model: str, **kwargs) -> LLMResponseProtocol:
        """Generate a response from the LLM.
        
        Args:
            prompt: The input prompt
            model: The model to use for generation
            **kwargs: Additional provider-specific parameters
            
        Returns:
            LLMResponseProtocol object containing the response
        """
        ...
    
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
        ...
    
    @abstractmethod
    def supports_model(self, model: str) -> bool:
        """Check if the provider supports a specific model.
        
        Args:
            model: The model name to check
            
        Returns:
            True if the model is supported, False otherwise
        """
        ...
    
    @classmethod
    @abstractmethod
    def from_config(cls, config: Dict[str, Any]) -> 'LLMProviderProtocol':
        """Create provider instance from configuration.
        
        Args:
            config: Configuration dictionary
            
        Returns:
            Provider instance
        """
        ...