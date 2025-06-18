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
"""Agent component protocols.

This module defines the protocols for agent components including
agent interfaces and factory interfaces.
"""

from typing import Protocol, AsyncGenerator, Dict, Any, Optional, List
from abc import abstractmethod
from .response import LLMResponseProtocol


class AgentProtocol(Protocol):
    """Protocol for agent implementations.
    
    Defines the interface that agent implementations should implement.
    """
    
    @property
    def name(self) -> str:
        """Get the agent name.
        
        Returns:
            The name of this agent
        """
        ...
    
    @property
    def model(self) -> str:
        """Get the model used by this agent.
        
        Returns:
            The model name
        """
        ...
    
    @property
    def provider(self) -> str:
        """Get the provider used by this agent.
        
        Returns:
            The provider name
        """
        ...
    
    @property
    def system_prompt(self) -> Optional[str]:
        """Get the system prompt for this agent.
        
        Returns:
            The system prompt or None if not set
        """
        ...
    
    @property
    def config(self) -> Dict[str, Any]:
        """Get the agent configuration.
        
        Returns:
            Dictionary containing agent configuration
        """
        ...
    
    @abstractmethod
    async def generate(self, prompt: str, **kwargs) -> LLMResponseProtocol:
        """Generate a response using this agent.
        
        Args:
            prompt: The input prompt
            **kwargs: Additional parameters that override agent defaults
            
        Returns:
            LLMResponseProtocol object containing the response
        """
        ...
    
    @abstractmethod
    async def generate_stream(self, prompt: str, **kwargs) -> AsyncGenerator[str, None]:
        """Generate a streaming response using this agent.
        
        Args:
            prompt: The input prompt
            **kwargs: Additional parameters that override agent defaults
            
        Yields:
            Chunks of generated text
        """
        ...


class AgentFactoryProtocol(Protocol):
    """Protocol for agent factory implementations.
    
    Defines the interface for creating and managing agent instances.
    """
    
    @abstractmethod
    def create_agent(self, name: str, **kwargs) -> AgentProtocol:
        """Create an agent by name.
        
        Args:
            name: The agent name
            **kwargs: Additional parameters for agent creation
            
        Returns:
            Agent instance
        """
        ...
    
    @abstractmethod
    def create_agent_with_model(self, model: str, provider: Optional[str] = None, **kwargs) -> AgentProtocol:
        """Create an agent with a specific model.
        
        Args:
            model: The model to use
            provider: The provider to use (optional)
            **kwargs: Additional parameters for agent creation
            
        Returns:
            Agent instance
        """
        ...
    
    @abstractmethod
    def list_agents(self) -> List[str]:
        """List available agent names.
        
        Returns:
            List of available agent names
        """
        ...
    
    @abstractmethod
    def agent_exists(self, name: str) -> bool:
        """Check if an agent exists.
        
        Args:
            name: The agent name to check
            
        Returns:
            True if the agent exists, False otherwise
        """
        ...