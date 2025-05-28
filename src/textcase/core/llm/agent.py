"""
LLM Agent implementation for textcase.

This module provides an Agent class that can be used to interact with LLMs
using configurations from agent definition files.
"""
import asyncio
import logging
import os
from pathlib import Path
from typing import Dict, List, Optional, Any, AsyncGenerator, Tuple

import frontmatter
from markdown_it import MarkdownIt

from textcase.core.project import Project
from textcase.core.llm import LLMResponse
from textcase.core.logging import get_logger

# Get logger for this module
logger = get_logger(__name__)


class Agent:
    """LLM Agent implementation that manages model selection and inference."""
    
    def __init__(self, project: Project, agent_name: str):
        """
        Initialize an Agent.
        
        Args:
            project: The project instance
            agent_name: Name of the agent to use
        
        Raises:
            ValueError: If the agent configuration cannot be found or is invalid
        """
        self.project = project
        self.agent_name = agent_name
        
        # Load agent configuration
        self.config, self.system_prompt = self._load_agent_config(agent_name)
        
        # Cache for providers
        self._provider_cache = {}
        
    async def generate(self, prompt: str, **kwargs) -> LLMResponse:
        """
        Generate a response using the agent's configuration.
        
        Args:
            prompt: The prompt to send to the LLM
            **kwargs: Additional parameters that override agent defaults
            
        Returns:
            LLMResponse object containing the generated content
        """
        # Get provider and model to use
        provider, model, inference_params = self._prepare_inference(kwargs)
        
        # Create the full prompt with system prompt
        full_prompt = self._create_full_prompt(prompt)
        
        # Generate the response
        logger.info(f"Generating response using agent '{self.agent_name}' with model '{model}'")
        logger.debug(f"Inference parameters: {inference_params}")
        
        return await provider.generate(full_prompt, model, **inference_params)
    
    async def generate_stream(self, prompt: str, **kwargs) -> AsyncGenerator[str, None]:
        """
        Generate a streaming response using the agent's configuration.
        
        Args:
            prompt: The prompt to send to the LLM
            **kwargs: Additional parameters that override agent defaults
            
        Returns:
            AsyncGenerator yielding content chunks as they are generated
        """
        # Get provider and model to use
        provider, model, inference_params = self._prepare_inference(kwargs)
        
        # Create the full prompt with system prompt
        full_prompt = self._create_full_prompt(prompt)
        
        # Generate the streaming response
        logger.info(f"Streaming response using agent '{self.agent_name}' with model '{model}'")
        logger.debug(f"Inference parameters: {inference_params}")
        
        async for chunk in provider.generate_stream(full_prompt, model, **inference_params):
            yield chunk
    
    def _prepare_inference(self, kwargs: Dict[str, Any]) -> Tuple[Any, str, Dict[str, Any]]:
        """
        Prepare for inference by selecting provider, model and parameters.
        
        Args:
            kwargs: User-provided parameters that override defaults
            
        Returns:
            Tuple of (provider, model_name, inference_parameters)
        """
        # Get models from config
        models = self.config.get('models', ['deepseek-v3'])
        if not models:
            raise ValueError(f"No models specified for agent '{self.agent_name}'")
        
        # Use the first model in the list
        model_name = models[0]
        
        # Find a provider for this model using project's interface
        providers = self.project.get_model_providers(model_name)
        
        if not providers:
            raise ValueError(f"No provider found for model '{model_name}'")
        
        # Use the first available provider
        provider_name = next(iter(providers.keys()))
        provider = providers[provider_name]
        
        # Prepare inference parameters from agent config and user overrides
        inference_params = {}
        
        # Add temperature if specified
        if self.config.get('use_temperature', True):
            inference_params['temperature'] = self.config.get('temperature', 0.7)
        
        # Add max tokens if specified
        if 'max_output_tokens' in self.config:
            inference_params['max_tokens'] = self.config['max_output_tokens']
        
        # Override with user-provided parameters
        for param in ['temperature', 'max_tokens', 'top_p']:
            if param in kwargs:
                inference_params[param] = kwargs[param]
        
        return provider, model_name, inference_params
    
    def _create_full_prompt(self, user_prompt: str) -> str:
        """
        Create a full prompt by combining system prompt and user prompt.
        
        Args:
            user_prompt: The user's prompt
            
        Returns:
            Full prompt for the LLM
        """
        # For now, we're using a simple concatenation
        # This might need to be adjusted based on how providers expect the format
        return f"{self.system_prompt}\n\nUser: {user_prompt}"
    
    def _load_agent_config(self, agent_name: str) -> Tuple[Dict[str, Any], str]:
        """
        Load agent configuration from file.
        
        Args:
            agent_name: Name of the agent
            
        Returns:
            Tuple of (config_dict, system_prompt)
            
        Raises:
            ValueError: If the agent configuration cannot be found or is invalid
        """
        # Look for agent config in the project's .config/agent directory
        agent_path = self.project.path / '.config' / 'agent' / f"{agent_name}.md"
        
        if not agent_path.exists():
            raise ValueError(f"Agent configuration not found: {agent_path}")
        
        try:
            # Parse the markdown file with frontmatter
            with open(agent_path, 'r', encoding='utf-8') as f:
                post = frontmatter.load(f)
            
            # Extract the frontmatter as config
            config = dict(post.metadata)
            
            # Extract the content as system prompt
            system_prompt = post.content.strip()
            
            logger.info(f"Loaded agent '{agent_name}' with models: {config.get('models', [])}")
            return config, system_prompt
            
        except Exception as e:
            logger.exception(f"Error loading agent configuration: {str(e)}")
            raise ValueError(f"Error loading agent configuration: {str(e)}")


class AgentFactory:
    """Factory for creating Agent instances."""
    
    _agents: Dict[str, Agent] = {}
    
    @classmethod
    def get_agent(cls, project: Project, agent_name: str) -> Agent:
        """
        Get or create an Agent instance.
        
        Args:
            project: The project instance
            agent_name: Name of the agent
            
        Returns:
            Agent instance
        """
        # Create a cache key that includes project path and agent name
        cache_key = f"{project.path}:{agent_name}"
        
        # Check if agent already exists in cache
        if cache_key in cls._agents:
            return cls._agents[cache_key]
        
        # Create new agent
        agent = Agent(project, agent_name)
        
        # Cache the agent
        cls._agents[cache_key] = agent
        
        return agent
    
    @classmethod
    def list_available_agents(cls, project: Project) -> List[str]:
        """
        List all available agents for a project.
        
        Args:
            project: The project instance
            
        Returns:
            List of agent names
        """
        agent_dir = project.path / '.config' / 'agent'
        
        if not agent_dir.exists():
            return []
        
        # Find all .md files in the agent directory
        agents = []
        for agent_file in agent_dir.glob('*.md'):
            agents.append(agent_file.stem)
            
        return agents
