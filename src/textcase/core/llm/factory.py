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
"""LLM factory for creating and managing provider instances.

This module provides the LLMFactory class that handles dynamic loading
of LLM providers and finding appropriate providers for specific models.
"""

import importlib
import logging
from typing import Dict, List, Optional, Any, Type
from pathlib import Path

from ...protocol.llm import LLMProviderProtocol
from .provider import LLMProvider

logger = logging.getLogger(__name__)


class LLMFactory:
    """Factory for creating and managing LLM provider instances.
    
    This class handles dynamic loading of providers and maintains a registry
    of available providers and their supported models.
    """
    
    def __init__(self):
        """Initialize the LLM factory."""
        self._providers: Dict[str, LLMProvider] = {}
        self._provider_classes: Dict[str, Type[LLMProvider]] = {}
        self._model_to_provider: Dict[str, str] = {}
        
        # Register built-in providers
        self._register_builtin_providers()
    
    def _register_builtin_providers(self) -> None:
        """Register built-in provider classes."""
        try:
            # Try to import and register HumbugProvider
            from .humbug_provider import HumbugProvider
            self._provider_classes['humbug'] = HumbugProvider
            logger.debug("Registered HumbugProvider")
        except ImportError as e:
            logger.warning(f"Could not import HumbugProvider: {e}")
        
        try:
            # Register AIOHttpLLMProvider
            from .aiohttp_provider import AIOHttpLLMProvider
            self._provider_classes['aiohttp'] = AIOHttpLLMProvider
            logger.debug("Registered AIOHttpLLMProvider")
        except ImportError as e:
            logger.warning(f"Could not import AIOHttpLLMProvider: {e}")
    
    def register_provider_class(self, name: str, provider_class: Type[LLMProvider]) -> None:
        """Register a provider class.
        
        Args:
            name: Provider name
            provider_class: Provider class
        """
        self._provider_classes[name] = provider_class
        logger.debug(f"Registered provider class: {name}")
    
    def create_provider(self, provider_name: str, config: Dict[str, Any]) -> LLMProvider:
        """Create a provider instance from configuration.
        
        Args:
            provider_name: Name of the provider
            config: Provider configuration
            
        Returns:
            Provider instance
            
        Raises:
            ValueError: If provider is not found or configuration is invalid
        """
        if provider_name in self._providers:
            logger.debug(f"Returning existing provider instance: {provider_name}")
            return self._providers[provider_name]
        
        # Find provider class
        provider_class = self._find_provider_class(provider_name)
        if not provider_class:
            raise ValueError(f"Provider '{provider_name}' not found")
        
        try:
            # Create provider instance
            logger.info(f"Creating provider instance: {provider_name}")
            provider = provider_class.from_config(config)
            
            # Cache the provider
            self._providers[provider_name] = provider
            
            # Update model-to-provider mapping
            for model in provider.supported_models:
                self._model_to_provider[model] = provider_name
            
            logger.info(f"Successfully created provider: {provider_name}")
            return provider
            
        except Exception as e:
            logger.error(f"Failed to create provider '{provider_name}': {e}")
            raise ValueError(f"Failed to create provider '{provider_name}': {e}")
    
    def _find_provider_class(self, provider_name: str) -> Optional[Type[LLMProvider]]:
        """Find provider class by name.
        
        Args:
            provider_name: Name of the provider
            
        Returns:
            Provider class or None if not found
        """
        # Check registered classes first
        if provider_name in self._provider_classes:
            return self._provider_classes[provider_name]
        
        # Try dynamic import for common providers
        try:
            if provider_name.lower() == 'humbug':
                from .humbug_provider import HumbugProvider
                self._provider_classes[provider_name] = HumbugProvider
                return HumbugProvider
            elif provider_name.lower() == 'aiohttp':
                from .aiohttp_provider import AIOHttpLLMProvider
                self._provider_classes[provider_name] = AIOHttpLLMProvider
                return AIOHttpLLMProvider
        except ImportError:
            pass
        
        return None
    
    def get_provider(self, provider_name: str) -> Optional[LLMProvider]:
        """Get an existing provider instance.
        
        Args:
            provider_name: Name of the provider
            
        Returns:
            Provider instance or None if not found
        """
        return self._providers.get(provider_name)
    
    def find_provider_for_model(self, model: str) -> Optional[str]:
        """Find a provider that supports the given model.
        
        Args:
            model: Model name
            
        Returns:
            Provider name or None if no provider supports the model
        """
        # Check direct mapping first
        if model in self._model_to_provider:
            return self._model_to_provider[model]
        
        # Check all loaded providers
        for provider_name, provider in self._providers.items():
            if provider.supports_model(model):
                self._model_to_provider[model] = provider_name
                return provider_name
        
        return None
    
    def list_providers(self) -> List[str]:
        """List all available provider names.
        
        Returns:
            List of provider names
        """
        return list(self._provider_classes.keys())
    
    def list_loaded_providers(self) -> List[str]:
        """List all loaded provider instances.
        
        Returns:
            List of loaded provider names
        """
        return list(self._providers.keys())
    
    def list_supported_models(self, provider_name: Optional[str] = None) -> List[str]:
        """List supported models.
        
        Args:
            provider_name: Optional provider name to filter by
            
        Returns:
            List of supported model names
        """
        if provider_name:
            provider = self._providers.get(provider_name)
            return provider.supported_models if provider else []
        
        # Return all supported models from all providers
        models = set()
        for provider in self._providers.values():
            models.update(provider.supported_models)
        
        return sorted(list(models))
    
    def clear_cache(self) -> None:
        """Clear the provider cache."""
        self._providers.clear()
        self._model_to_provider.clear()
        logger.debug("Cleared provider cache")
    
    def __repr__(self) -> str:
        """String representation of the factory.
        
        Returns:
            String representation
        """
        return f"LLMFactory(providers={list(self._providers.keys())}, classes={list(self._provider_classes.keys())})"