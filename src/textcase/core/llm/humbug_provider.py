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
"""Humbug-based LLM provider implementation.

This module provides the HumbugProvider class that integrates with the
Humbug AI library for LLM interactions.
"""

import asyncio
import json
import logging
from typing import Dict, List, Optional, Any, AsyncGenerator
import yaml
from pathlib import Path

try:
    from humbug.ai.ai_provider import AIProvider
    from humbug.ai.ai_backend_settings import AIBackendSettings
    from humbug.ai.ai_message import AIMessage, AIMessageSource
    HUMBUG_AVAILABLE = True
except ImportError:
    HUMBUG_AVAILABLE = False
    # Fallback classes
    class AIProvider:
        @staticmethod
        def create_backends(settings):
            return {}
    
    class AIBackendSettings:
        pass
    
    class AIMessage:
        def __init__(self, *args, **kwargs):
            pass
    
    class AIMessageSource:
        USER = "user"
        SYSTEM = "system"

from .conversation_settings import TextcaseConversationSettings
from .provider import LLMProvider, LLMResponse
from ...protocol.llm import LLMProviderProtocol, LLMResponseProtocol

logger = logging.getLogger(__name__)


class HumbugProvider(LLMProvider):
    """Humbug-based LLM provider implementation.
    
    This class implements the LLMProviderProtocol interface using the Humbug AI library.
    """
    
    def __init__(self, provider_name: str, backend_settings: Dict[str, AIBackendSettings]):
        """Initialize HumbugProvider.
        
        Args:
            provider_name: Name of the provider (e.g., 'openai', 'anthropic')
            backend_settings: Dictionary of backend settings
        """
        super().__init__(provider_name)
        
        if not HUMBUG_AVAILABLE:
            raise ImportError("Humbug library is not available. Please install it to use HumbugProvider.")
        
        logger.info(f"Initializing HumbugProvider for provider: {provider_name}")
        logger.debug(f"Backend settings: {backend_settings}")
        
        self.backend_settings = backend_settings
        
        try:
            logger.debug("Creating backends using AIProvider.create_backends")
            self.backends = AIProvider.create_backends(backend_settings)
            
            if not self.backends:
                logger.error("No backends were created from the provided configuration")
                raise ValueError(f"No backends were created. Check your configuration.")
                
            logger.debug(f"Available backends: {list(self.backends.keys())}")
            
            if provider_name not in self.backends:
                available = list(self.backends.keys())
                logger.error(f"Provider '{provider_name}' not found in available backends: {available}")
                raise ValueError(f"Provider '{provider_name}' not found in available backends: {available}")
                
            self.backend = self.backends[provider_name]
            logger.info(f"Successfully initialized backend for provider: {provider_name}")
        except Exception as e:
            logger.exception(f"Error initializing HumbugProvider: {str(e)}")
            raise
    
    @property
    def supported_models(self) -> List[str]:
        """Get list of supported models.
        
        Returns:
            List of model names supported by this provider
        """
        if not hasattr(self, 'backend') or not self.backend:
            return []
        
        try:
            # Get models from backend configuration
            if hasattr(self.backend, 'models'):
                return list(self.backend.models.keys())
            elif hasattr(self.backend, 'get_models'):
                return self.backend.get_models()
            else:
                # Fallback: try to get from backend settings
                settings = self.backend_settings.get(self.provider_name)
                if settings and hasattr(settings, 'models'):
                    return list(settings.models.keys())
                return []
        except Exception as e:
            logger.warning(f"Could not get supported models: {e}")
            return []
    
    async def generate(self, prompt: str, model: str, **kwargs) -> LLMResponse:
        """Generate a response from the LLM.
        
        Args:
            prompt: The prompt to send to the LLM
            model: The model to use
            **kwargs: Additional provider-specific parameters
            
        Returns:
            LLMResponse object containing the generated content
        """
        request_id = f"{model}-{str(id(prompt))[:8]}"
        logger.info(f"[{request_id}] Starting LLM request with model: {model}")
        
        temperature = kwargs.get('temperature', 0.7)
        max_tokens = kwargs.get('max_tokens', None)
        top_p = kwargs.get('top_p', None)
        system_prompt = kwargs.get('system_prompt', None)
        
        # Log request parameters
        logger.info(f"[{request_id}] Using provider: {self.provider_name}")
        logger.info(f"[{request_id}] Model: {model}")
        logger.debug(f"[{request_id}] Temperature: {temperature}")
        if max_tokens:
            logger.debug(f"[{request_id}] Max tokens: {max_tokens}")
        if top_p:
            logger.debug(f"[{request_id}] Top P: {top_p}")
            
        # Create conversation settings
        conversation_settings = TextcaseConversationSettings(
            model=model,
            temperature=temperature,
            max_tokens=max_tokens
        )
        
        # Prepare messages
        messages = []
        if system_prompt:
            messages.append(AIMessage(content=system_prompt, source=AIMessageSource.SYSTEM))
        messages.append(AIMessage(content=prompt, source=AIMessageSource.USER))
        
        try:
            logger.debug(f"[{request_id}] Sending request to backend")
            
            # Generate response using the backend
            response = await self.backend.generate(
                messages=messages,
                conversation_settings=conversation_settings
            )
            
            # Extract content from response
            if hasattr(response, 'content'):
                content = response.content
            elif hasattr(response, 'text'):
                content = response.text
            elif isinstance(response, str):
                content = response
            else:
                content = str(response)
            
            # Create metadata
            metadata = {
                'request_id': request_id,
                'temperature': temperature,
                'max_tokens': max_tokens,
                'top_p': top_p
            }
            
            # Add response metadata if available
            if hasattr(response, 'metadata'):
                metadata.update(response.metadata)
            
            logger.info(f"[{request_id}] Successfully generated response (length: {len(content)})")
            
            return LLMResponse(
                content=content,
                model=model,
                provider=self.provider_name,
                metadata=metadata
            )
            
        except Exception as e:
            logger.error(f"[{request_id}] Error generating response: {e}")
            raise
    
    async def generate_stream(self, prompt: str, model: str, **kwargs) -> AsyncGenerator[str, None]:
        """Generate a streaming response from the LLM.
        
        Args:
            prompt: The prompt to send to the LLM
            model: The model to use
            **kwargs: Additional provider-specific parameters
            
        Yields:
            Chunks of generated text
        """
        request_id = f"{model}-{str(id(prompt))[:8]}-stream"
        logger.info(f"[{request_id}] Starting streaming LLM request with model: {model}")
        
        temperature = kwargs.get('temperature', 0.7)
        max_tokens = kwargs.get('max_tokens', None)
        top_p = kwargs.get('top_p', None)
        system_prompt = kwargs.get('system_prompt', None)
        
        # Create conversation settings
        conversation_settings = TextcaseConversationSettings(
            model=model,
            temperature=temperature,
            max_tokens=max_tokens
        )
        
        # Prepare messages
        messages = []
        if system_prompt:
            messages.append(AIMessage(content=system_prompt, source=AIMessageSource.SYSTEM))
        messages.append(AIMessage(content=prompt, source=AIMessageSource.USER))
        
        try:
            logger.debug(f"[{request_id}] Starting streaming generation")
            
            # Generate streaming response using the backend
            async for chunk in self.backend.generate_stream(
                messages=messages,
                conversation_settings=conversation_settings
            ):
                # Extract content from chunk
                if hasattr(chunk, 'content'):
                    content = chunk.content
                elif hasattr(chunk, 'text'):
                    content = chunk.text
                elif isinstance(chunk, str):
                    content = chunk
                else:
                    content = str(chunk)
                
                if content:
                    yield content
            
            logger.info(f"[{request_id}] Completed streaming generation")
            
        except Exception as e:
            logger.error(f"[{request_id}] Error in streaming generation: {e}")
            raise
    
    @classmethod
    def from_config(cls, config: Dict[str, Any]) -> 'HumbugProvider':
        """Create provider instance from configuration.
        
        Args:
            config: Configuration dictionary
            
        Returns:
            HumbugProvider instance
        """
        if not HUMBUG_AVAILABLE:
            raise ImportError("Humbug library is not available. Please install it to use HumbugProvider.")
        
        provider_name = config.get('name', 'humbug')
        
        # Convert config to backend settings
        backend_settings = {}
        
        # Handle different config formats
        if 'backends' in config:
            # Direct backend configuration
            for backend_name, backend_config in config['backends'].items():
                backend_settings[backend_name] = AIBackendSettings(**backend_config)
        elif 'api_key' in config or 'api_base' in config:
            # Single backend configuration
            backend_config = {
                'api_key': cls.parse_template_variables(config.get('api_key', '')),
                'api_base': config.get('api_base'),
                'api_version': config.get('api_version'),
                'models': config.get('models', {})
            }
            # Remove None values
            backend_config = {k: v for k, v in backend_config.items() if v is not None}
            backend_settings[provider_name] = AIBackendSettings(**backend_config)
        else:
            raise ValueError("Invalid configuration: missing backend settings")
        
        return cls(provider_name, backend_settings)