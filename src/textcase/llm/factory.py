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

import logging
from typing import Dict, List, Optional, Any, Type

from ..proto.resource_collection_protocol import ResourceCollectionManager
from .provider import LLMProvider
from ..collection.config_collection import ConfigItemImpl


logger = logging.getLogger(__name__)


class LLMFactory:
    """Factory for creating and managing LLM provider instances.
    
    This class handles dynamic loading of providers and maintains a registry
    of available providers and their supported models.
    """
    
    def __init__(self, resource_manager: ResourceCollectionManager):
        """Initialize the LLM factory."""
        """
            暂时规定，每次 provider 配置改变，均需要重启整个系统。
            
            因此，与 provider 相关的初始化，可以在 init 阶段完成
        """
        self._providers: Dict[str, LLMProvider] = {}
        self._model_to_provider: Dict[str, List[str]] = {}

        provider_collections = resource_manager.get_collection('config.provider')
        if not provider_collections:
            raise ValueError("No provider configuration found")
        for provider_name in provider_collections.item_names:
            provider = provider_collections.get_item(provider_name)
            if isinstance(provider, ConfigItemImpl):
                
                # 使用 ConfigItemImpl 接口读取数据
                config_data = provider.as_yaml()
                if config_data is None:
                    logger.error(f"Failed to load provider configuration: {provider_name}")
                    continue

                provider_driver = self.get_llm_driver_by_type(config_data.get('type', 'openai'))

                provider = provider_driver.from_config(config_data)

                if provider is None:
                    logger.error(f"Failed to load provider: {provider_name}")
                    continue

                # 注意：provider.provider_name 的语义上类似 driver_name， 应使用配置文件中的 provider_name
                self._providers[provider_name] = provider
                for model in provider.supported_models:
                    if model in self._model_to_provider:
                        self._model_to_provider[model].append(provider_name)
                    else:
                        self._model_to_provider[model] = [provider_name, ]
        # for provider_name

    @classmethod
    def get_llm_driver_by_type(cls, driver_name: str):
        if driver_name == 'openai':
            from .humbug_driver import HumbugDriver
            # from .aiohttp_provider import AIOHttpLLMProvider
            return HumbugDriver
        return None

    def get_provider(self, provider_name: str) -> Optional[LLMProvider]:
        """Get an existing provider instance.
        
        Args:
            provider_name: Name of the provider
            
        Returns:
            Provider instance or None if not found
        """
        return self._providers.get(provider_name)
    
    def find_provider_for_model(self, model: str) -> List[str]:
        """Find a provider that supports the given model.
        
        Args:
            model: Model name
            
        Returns:
            Provider name or None if no provider supports the model
        """
        # Check direct mapping first
        if model in self._model_to_provider:
            return self._model_to_provider[model]
        
        return []
    
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
    
    def __repr__(self) -> str:
        """String representation of the factory.
        
        Returns:
            String representation
        """
        return f"LLMFactory(providers={list(self._providers.keys())})"
