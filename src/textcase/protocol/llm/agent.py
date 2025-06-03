"""
Protocol definitions for Agent components.

This module defines the protocols (interfaces) for Agent components such as
Agent and AgentFactory.
"""
from pathlib import Path
from typing import Dict, List, Optional, Any, AsyncGenerator, Protocol, runtime_checkable, ClassVar

from ..resource.module import Project
from .llm import LLMResponseProtocol


@runtime_checkable
class AgentProtocol(Protocol):
    """Protocol for LLM agents."""
    
    project: Project
    agent_name: Optional[str]
    config: Dict[str, Any]
    system_prompt: str
    
    def __init__(self, project: Project, agent_name: str = None, 
                 system_prompt: str = None, config: Dict[str, Any] = None):
        """
        Initialize an Agent.
        
        Args:
            project: The project instance
            agent_name: Name of the agent to use (optional if system_prompt and config are provided)
            system_prompt: System prompt to use (optional if agent_name is provided)
            config: Configuration dictionary (optional if agent_name is provided)
        """
        ...
    
    def get_definition(self) -> str:
        """
        Get the agent's definition as a string in markdown format with YAML frontmatter.
        
        Returns:
            String containing the agent's definition in markdown format with YAML frontmatter
        """
        ...
    
    async def generate(self, prompt: str, **kwargs) -> LLMResponseProtocol:
        """
        Generate a response using the agent's configuration.
        
        Args:
            prompt: The prompt to send to the LLM
            **kwargs: Additional parameters that override agent defaults
            
        Returns:
            LLMResponse object containing the generated content
        """
        ...
    
    async def generate_stream(self, prompt: str, **kwargs) -> AsyncGenerator[str, None]:
        """
        Generate a streaming response using the agent's configuration.
        
        Args:
            prompt: The prompt to send to the LLM
            **kwargs: Additional parameters that override agent defaults
            
        Returns:
            AsyncGenerator yielding content chunks as they are generated
        """
        ...


@runtime_checkable
class AgentFactoryProtocol(Protocol):
    """Protocol for agent factories."""
    
    _agents: ClassVar[Dict[str, AgentProtocol]]
    
    @classmethod
    def get_agent(cls, project: Project, agent_name: str = None, 
                  model: str = None, provider: str = None) -> AgentProtocol:
        """
        Get or create an Agent instance.
        
        Args:
            project: The project instance
            agent_name: Name of the agent (optional if model is provided)
            model: Model name to use for a default agent (optional if agent_name is provided)
            provider: Provider name to use for a default agent (optional)
            
        Returns:
            Agent instance
        """
        ...
    
    @classmethod
    def list_available_agents(cls, project: Project) -> List[str]:
        """
        List all available agents for a project.
        
        Args:
            project: The project instance
            
        Returns:
            List of agent names
        """
        ...
