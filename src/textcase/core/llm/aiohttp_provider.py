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
"""AIOHttp-based LLM provider implementation.

This module provides a concrete implementation of the LLM provider
using aiohttp for AI model interactions, as an alternative to the
Humbug-based provider.
"""

import os
import json
import asyncio
from typing import Dict, Any, Optional, AsyncGenerator

import aiohttp

from .provider import LLMProvider, LLMResponse
from .conversation_settings import TextcaseConversationSettings


class AIOHttpLLMProvider(LLMProvider):
    """AIOHttp-based LLM provider.
    
    This provider uses aiohttp to communicate with LLM APIs,
    providing an alternative implementation to the Humbug-based provider.
    """
    
    def __init__(self, name: str, config: Dict[str, Any]):
        """Initialize the AIOHttp LLM provider.
        
        Args:
            name: Provider name
            config: Provider configuration
        """
        super().__init__(name, config)
        
        # Extract configuration
        self.api_key = self._resolve_template_vars(config.get('api_key', ''))
        self.api_base = self._resolve_template_vars(config.get('api_base', ''))
        self.api_version = config.get('api_version', 'v1')
        
        # Parse models configuration
        self._models = {}
        if 'models' in config:
            if isinstance(config['models'], dict):
                self._models = config['models']
            elif isinstance(config['models'], list):
                # Convert list to dict format
                for model in config['models']:
                    self._models[model] = {}
        elif 'model' in config:
            # Single model format
            if isinstance(config['model'], list):
                for model in config['model']:
                    self._models[model] = {}
            else:
                self._models[config['model']] = {}
    
    @property
    def models(self) -> list[str]:
        """Get list of supported models."""
        return list(self._models.keys())
    
    def supports_model(self, model: str) -> bool:
        """Check if provider supports the given model."""
        return model in self._models
    
    async def generate(
        self,
        prompt: str,
        model: str,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> LLMResponse:
        """Generate a response using the specified model.
        
        Args:
            prompt: Input prompt
            model: Model name
            temperature: Temperature for generation
            max_tokens: Maximum tokens to generate
            **kwargs: Additional parameters
            
        Returns:
            LLM response
            
        Raises:
            ValueError: If model is not supported
            RuntimeError: If API call fails
        """
        if not self.supports_model(model):
            raise ValueError(f"Model '{model}' not supported by provider '{self.name}'")
        
        # Prepare request payload
        payload = {
            'model': model,
            'messages': [
                {'role': 'user', 'content': prompt}
            ]
        }
        
        # Add optional parameters
        if temperature is not None:
            payload['temperature'] = temperature
        if max_tokens is not None:
            payload['max_tokens'] = max_tokens
        
        # Add any additional kwargs
        for key, value in kwargs.items():
            if key not in payload:
                payload[key] = value
        
        # Prepare headers
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {self.api_key}'
        }
        
        # Make API request
        url = f"{self.api_base.rstrip('/')}/chat/completions"
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload, headers=headers) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        raise RuntimeError(f"API request failed with status {response.status}: {error_text}")
                    
                    result = await response.json()
                    
                    # Extract response content
                    if 'choices' in result and len(result['choices']) > 0:
                        content = result['choices'][0]['message']['content']
                    else:
                        raise RuntimeError("Invalid response format from API")
                    
                    # Extract metadata
                    metadata = {
                        'usage': result.get('usage', {}),
                        'model': result.get('model', model),
                        'finish_reason': result['choices'][0].get('finish_reason') if 'choices' in result else None
                    }
                    
                    return LLMResponse(
                        content=content,
                        model=model,
                        provider=self.name,
                        metadata=metadata
                    )
        
        except aiohttp.ClientError as e:
            raise RuntimeError(f"Network error: {e}")
        except json.JSONDecodeError as e:
            raise RuntimeError(f"Invalid JSON response: {e}")
        except Exception as e:
            raise RuntimeError(f"Unexpected error: {e}")
    
    async def generate_stream(
        self,
        prompt: str,
        model: str,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> AsyncGenerator[str, None]:
        """Generate a streaming response using the specified model.
        
        Args:
            prompt: Input prompt
            model: Model name
            temperature: Temperature for generation
            max_tokens: Maximum tokens to generate
            **kwargs: Additional parameters
            
        Yields:
            Response chunks as strings
            
        Raises:
            ValueError: If model is not supported
            RuntimeError: If API call fails
        """
        if not self.supports_model(model):
            raise ValueError(f"Model '{model}' not supported by provider '{self.name}'")
        
        # Prepare request payload
        payload = {
            'model': model,
            'messages': [
                {'role': 'user', 'content': prompt}
            ],
            'stream': True
        }
        
        # Add optional parameters
        if temperature is not None:
            payload['temperature'] = temperature
        if max_tokens is not None:
            payload['max_tokens'] = max_tokens
        
        # Add any additional kwargs
        for key, value in kwargs.items():
            if key not in payload:
                payload[key] = value
        
        # Prepare headers
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {self.api_key}'
        }
        
        # Make streaming API request
        url = f"{self.api_base.rstrip('/')}/chat/completions"
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload, headers=headers) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        raise RuntimeError(f"API request failed with status {response.status}: {error_text}")
                    
                    # Process streaming response
                    async for line in response.content:
                        line = line.decode('utf-8').strip()
                        
                        if line.startswith('data: '):
                            data = line[6:]  # Remove 'data: ' prefix
                            
                            if data == '[DONE]':
                                break
                            
                            try:
                                chunk = json.loads(data)
                                if 'choices' in chunk and len(chunk['choices']) > 0:
                                    delta = chunk['choices'][0].get('delta', {})
                                    if 'content' in delta:
                                        yield delta['content']
                            except json.JSONDecodeError:
                                # Skip invalid JSON chunks
                                continue
        
        except aiohttp.ClientError as e:
            raise RuntimeError(f"Network error: {e}")
        except Exception as e:
            raise RuntimeError(f"Unexpected error: {e}")
    
    @classmethod
    def from_config(cls, name: str, config: Dict[str, Any]) -> 'AIOHttpLLMProvider':
        """Create provider instance from configuration.
        
        Args:
            name: Provider name
            config: Provider configuration
            
        Returns:
            Provider instance
        """
        return cls(name, config)