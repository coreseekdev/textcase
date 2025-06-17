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
"""Agent implementation for LLM interactions.

This module provides the Agent and AgentFactory classes for managing
LLM agents with specific configurations and system prompts.
"""

import logging
import yaml
from typing import Dict, List, Optional, Any, AsyncGenerator
from pathlib import Path

from ...protocol.llm import AgentProtocol, AgentFactoryProtocol, LLMResponseProtocol
from .factory import LLMFactory
from .provider import LLMProvider, LLMResponse

logger = logging.getLogger(__name__)


class Agent(AgentProtocol):
    """Agent implementation for LLM interactions.
    
    This class represents an LLM agent with specific configuration,
    model, provider, and system prompt.
    """
    
    def __init__(
        self,
        name: str,
        provider: LLMProvider,
        model: str,
        config: Dict[str, Any],
        system_prompt: Optional[str] = None
    ):
        """Initialize agent.
        
        Args:
            name: Agent name
            provider: LLM provider instance
            model: Model name to use
            config: Agent configuration
            system_prompt: Optional system prompt
        """
        self._name = name
        self._provider = provider
        self._model = model
        self._config = config.copy()
        self._system_prompt = system_prompt
        
        logger.debug(f"Initialized agent '{name}' with model '{model}' and provider '{provider.provider_name}'")
    
    @property
    def name(self) -> str:
        """Get the agent name.
        
        Returns:
            The name of this agent
        """
        return self._name
    
    @property
    def model(self) -> str:
        """Get the model used by this agent.
        
        Returns:
            The model name
        """
        return self._model
    
    @property
    def provider(self) -> str:
        """Get the provider used by this agent.
        
        Returns:
            The provider name
        """
        return self._provider.provider_name
    
    @property
    def system_prompt(self) -> Optional[str]:
        """Get the system prompt for this agent.
        
        Returns:
            The system prompt or None if not set
        """
        return self._system_prompt
    
    @property
    def config(self) -> Dict[str, Any]:
        """Get the agent configuration.
        
        Returns:
            Dictionary containing agent configuration
        """
        return self._config.copy()
    
    async def generate(self, prompt: str, **kwargs) -> LLMResponseProtocol:
        """Generate a response using this agent.
        
        Args:
            prompt: The input prompt
            **kwargs: Additional parameters that override agent defaults
            
        Returns:
            LLMResponseProtocol object containing the response
        """
        # Merge agent config with provided kwargs
        params = self._config.copy()
        params.update(kwargs)
        
        # Add system prompt if available
        if self._system_prompt and 'system_prompt' not in params:
            params['system_prompt'] = self._system_prompt
        
        logger.debug(f"Agent '{self._name}' generating response with model '{self._model}'")
        
        return await self._provider.generate(prompt, self._model, **params)
    
    async def generate_stream(self, prompt: str, **kwargs) -> AsyncGenerator[str, None]:
        """Generate a streaming response using this agent.
        
        Args:
            prompt: The input prompt
            **kwargs: Additional parameters that override agent defaults
            
        Yields:
            Chunks of generated text
        """
        # Merge agent config with provided kwargs
        params = self._config.copy()
        params.update(kwargs)
        
        # Add system prompt if available
        if self._system_prompt and 'system_prompt' not in params:
            params['system_prompt'] = self._system_prompt
        
        logger.debug(f"Agent '{self._name}' generating streaming response with model '{self._model}'")
        
        async for chunk in self._provider.generate_stream(prompt, self._model, **params):
            yield chunk
    
    def __repr__(self) -> str:
        """String representation of the agent.
        
        Returns:
            String representation
        """
        return f"Agent(name='{self._name}', model='{self._model}', provider='{self.provider}')"


class AgentFactory(AgentFactoryProtocol):
    """Factory for creating and managing agent instances.
    
    This class handles loading agent configurations and creating
    agent instances with appropriate providers.
    """
    
    def __init__(self, llm_factory: LLMFactory, textcase_instance):
        """Initialize agent factory.
        
        Args:
            llm_factory: LLM factory for creating providers
            textcase_instance: TextCase instance for configuration access
        """
        self._llm_factory = llm_factory
        self._textcase = textcase_instance
        self._agents_cache: Dict[str, Agent] = {}
        
        logger.debug("Initialized AgentFactory")
    
    def create_agent(self, name: str, **kwargs) -> Agent:
        """Create an agent by name.
        
        Args:
            name: The agent name
            **kwargs: Additional parameters for agent creation
            
        Returns:
            Agent instance
        """
        # Check cache first
        cache_key = f"{name}:{hash(str(sorted(kwargs.items())))}"
        if cache_key in self._agents_cache:
            return self._agents_cache[cache_key]
        
        logger.info(f"Creating agent: {name}")
        
        try:
            # Load agent configuration
            agent_config = self._load_agent_config(name)
            
            # Override with provided kwargs
            agent_config.update(kwargs)
            
            # Extract required fields
            model = agent_config.get('model')
            provider_name = agent_config.get('provider')
            system_prompt = agent_config.get('system_prompt')
            
            if not model:
                raise ValueError(f"Agent '{name}' configuration missing 'model' field")
            
            # Find or create provider
            if provider_name:
                provider = self._get_or_create_provider(provider_name)
            else:
                # Find provider that supports the model
                provider_name = self._llm_factory.find_provider_for_model(model)
                if not provider_name:
                    raise ValueError(f"No provider found for model '{model}'")
                provider = self._llm_factory.get_provider(provider_name)
                if not provider:
                    raise ValueError(f"Provider '{provider_name}' not available")
            
            # Create agent
            agent = Agent(
                name=name,
                provider=provider,
                model=model,
                config=agent_config,
                system_prompt=system_prompt
            )
            
            # Cache the agent
            self._agents_cache[cache_key] = agent
            
            logger.info(f"Successfully created agent '{name}' with model '{model}'")
            return agent
            
        except Exception as e:
            logger.error(f"Failed to create agent '{name}': {e}")
            raise
    
    def create_agent_with_model(self, model: str, provider: Optional[str] = None, **kwargs) -> Agent:
        """Create an agent with a specific model.
        
        Args:
            model: The model to use
            provider: The provider to use (optional)
            **kwargs: Additional parameters for agent creation
            
        Returns:
            Agent instance
        """
        # Generate a name for the agent
        agent_name = f"default-{model}"
        if provider:
            agent_name = f"default-{provider}-{model}"
        
        logger.info(f"Creating agent with model: {model}")
        
        try:
            # Find or create provider
            if provider:
                llm_provider = self._get_or_create_provider(provider)
            else:
                provider_name = self._llm_factory.find_provider_for_model(model)
                if not provider_name:
                    raise ValueError(f"No provider found for model '{model}'")
                llm_provider = self._llm_factory.get_provider(provider_name)
                if not llm_provider:
                    raise ValueError(f"Provider '{provider_name}' not available")
                provider = provider_name
            
            # Create default configuration
            config = {
                'model': model,
                'provider': provider,
                'temperature': kwargs.get('temperature', 0.7),
                'max_tokens': kwargs.get('max_tokens'),
            }
            config.update(kwargs)
            
            # Create agent
            agent = Agent(
                name=agent_name,
                provider=llm_provider,
                model=model,
                config=config,
                system_prompt=kwargs.get('system_prompt')
            )
            
            logger.info(f"Successfully created agent with model '{model}' and provider '{provider}'")
            return agent
            
        except Exception as e:
            logger.error(f"Failed to create agent with model '{model}': {e}")
            raise
    
    def list_agents(self) -> List[str]:
        """List available agent names.
        
        Returns:
            List of available agent names
        """
        try:
            # Get agent collection
            collection, _ = self._textcase.resource_manager.parse_resource_reference("config.agent")
            if collection:
                return collection.list_items()
            return []
        except Exception as e:
            logger.warning(f"Could not list agents: {e}")
            return []
    
    def agent_exists(self, name: str) -> bool:
        """Check if an agent exists.
        
        Args:
            name: The agent name to check
            
        Returns:
            True if the agent exists, False otherwise
        """
        return name in self.list_agents()
    
    def _load_agent_config(self, name: str) -> Dict[str, Any]:
        """Load agent configuration from file.
        
        Args:
            name: Agent name
            
        Returns:
            Agent configuration dictionary
        """
        try:
            # Get agent collection and item
            collection = self._textcase.resource_manager.parse_resource_reference(f"config.agent")

            # Get item
            item = collection.get_item(name)

            if not collection or not item:
                raise ValueError(f"Agent '{name}' not found")
            
            # Read agent configuration
            content = item.read_content()
            
            # Parse YAML front matter if present
            # Agent 默认应该是 markdown
            if content.startswith('---\n'):
                parts = content.split('---\n', 2)
                if len(parts) >= 2:
                    yaml_content = parts[1]
                    config = yaml.safe_load(yaml_content) or {}
                    
                    # Add system prompt from markdown content if present
                    if len(parts) >= 3:
                        markdown_content = parts[2].strip()
                        if markdown_content:
                            config['system_prompt'] = markdown_content
                    
                    return config
            
            # Fallback: treat entire content as system prompt
            return {'system_prompt': content}
            
        except Exception as e:
            logger.error(f"Failed to load agent config for '{name}': {e}")
            raise ValueError(f"Failed to load agent config for '{name}': {e}")
    
    def _get_or_create_provider(self, provider_name: str) -> LLMProvider:
        """Get or create a provider instance.
        
        Args:
            provider_name: Provider name
            
        Returns:
            Provider instance
        """
        # Check if provider already exists
        provider = self._llm_factory.get_provider(provider_name)
        if provider:
            return provider
        
        # Load provider configuration and create instance
        try:
            provider_config = self._load_provider_config(provider_name)
            return self._llm_factory.create_provider(provider_name, provider_config)
        except Exception as e:
            logger.error(f"Failed to get or create provider '{provider_name}': {e}")
            raise
    
    def _load_provider_config(self, provider_name: str) -> Dict[str, Any]:
        """Load provider configuration from file.
        
        Args:
            provider_name: Provider name
            
        Returns:
            Provider configuration dictionary
        """
        try:
            # Get provider collection and item
            collection = self._textcase.resource_manager.parse_resource_reference(f"config.provider")

            item = collection.get_item(provider_name)
            if not collection or not item:
                raise ValueError(f"Provider '{provider_name}' not found")
            
            # Read and parse provider configuration
            content = item.read_content()
            config = yaml.safe_load(content)
            
            if not config:
                raise ValueError(f"Invalid provider configuration for '{provider_name}'")
            
            # Add provider name to config
            config['name'] = provider_name
            
            return config
            
        except Exception as e:
            logger.error(f"Failed to load provider config for '{provider_name}': {e}")
            raise ValueError(f"Failed to load provider config for '{provider_name}': {e}")
    
    def clear_cache(self) -> None:
        """Clear the agent cache."""
        self._agents_cache.clear()
        logger.debug("Cleared agent cache")