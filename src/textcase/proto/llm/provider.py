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
"""LLM provider protocol.

This module defines the protocol for LLM provider implementations.
"""

from typing import Protocol, AsyncGenerator, List, Any
from abc import abstractmethod

from .response import LLMResponseProtocol


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