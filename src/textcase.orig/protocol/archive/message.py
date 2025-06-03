"""Protocol definitions for message files."""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, List, Optional, Any, Union, Protocol, TypeVar, Generic, runtime_checkable

from .agent import AgentProtocol, AgentFactoryProtocol


@runtime_checkable
class MessageOutput(Protocol):
    """Protocol for message outputs in a message file."""
    
    @property
    def content(self) -> str:
        """Get the content of the output."""
        ...
        
    @property
    def mime_type(self) -> str:
        """Get the MIME type of the content."""
        ...
        
    @property
    def nonce(self) -> Optional[str]:
        """Get the unique identifier for the output."""
        ...
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert the output to a dictionary."""
        ...


@runtime_checkable
class CodeExecutionOutput(MessageOutput, Protocol):
    """Protocol for code execution outputs in a message file."""
    
    @property
    def stdout_content(self) -> str:
        """Get the standard output content."""
        ...
    
    @property
    def stderr_content(self) -> str:
        """Get the standard error content."""
        ...
    
    @property
    def status(self) -> int:
        """Get the execution status code."""
        ...
    
    @property
    def duration(self) -> float:
        """Get the execution duration in seconds."""
        ...
    
    @property
    def lang(self) -> str:
        """Get the programming language of the executed code."""
        ...
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert the code execution output to a dictionary."""
        ...


T_MessageItem = TypeVar('T_MessageItem', bound='MessageItem')


@runtime_checkable
class MessageItem(Protocol):
    """Protocol for message items (Message or FunctionCall)."""
    
    @property
    def name(self) -> Optional[str]:
        """Get the name of the message item."""
        ...
    
    @property
    def timeout(self) -> Optional[int]:
        """Get the timeout in seconds."""
        ...
    
    @property
    def outputs(self) -> List[MessageOutput]:
        """Get the outputs of the message item."""
        ...
    
    @property
    def type(self) -> str:
        """Get the type of the message item."""
        ...
        
    @property
    def history(self) -> List[Dict[str, Any]]:
        """Get the history of the message item."""
        ...
    
    @property
    def heading_level(self) -> Optional[int]:
        """Get the heading level of the message item."""
        ...
    
    def add_output(self, output: MessageOutput) -> None:
        """Add an output to the message item."""
        ...
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert the message item to a dictionary."""
        ...


@runtime_checkable
class Message(MessageItem, Protocol):
    """Protocol for messages in a message file."""
    
    @property
    def content(self) -> str:
        """Get the content of the message."""
        ...
    
    @property
    def mime_type(self) -> str:
        """Get the MIME type of the content."""
        ...
    
    @property
    def agent_name(self) -> Optional[str]:
        """Get the name of the agent that generated the message."""
        ...
    
    def add_function_call(self, function_name: str, args: Optional[Dict[str, Any]] = None,
                         name: Optional[str] = None, timeout: Optional[int] = None) -> 'FunctionCall':
        """Add a function call to the message."""
        ...
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert the message to a dictionary."""
        ...


@runtime_checkable
class FunctionCall(MessageItem, Protocol):
    """Protocol for function calls in a message file."""
    
    @property
    def function_name(self) -> str:
        """Get the name of the function."""
        ...
    
    @property
    def args(self) -> Dict[str, Any]:
        """Get the arguments for the function."""
        ...
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert the function call to a dictionary."""
        ...
@runtime_checkable
class MessageStore(Protocol):
    """Protocol for message files."""
    
    def get_path(self) -> Path:
        """Get the path to the message file."""
        ...
    
    def get_items(self) -> List[MessageItem]:
        """Get all message items (messages and function calls) in the file."""
        ...
    
    def get_agents(self) -> List[Dict[str, Any]]:
        """Get all agents defined in the file."""
        ...
    
    def add_agent(self, agent_name: str, override_settings: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Add an agent to the message file.
        
        Args:
            agent_name: The name of the agent to add
            override_settings: Optional settings to override the agent's default settings
            
        Returns:
            The added agent configuration
        """
        ...
    
    def add_agent_with_definition(self, agent_name: str, definition: Dict[str, Any]) -> Dict[str, Any]:
        """
        Add an agent with a custom definition to the message file.
        
        Args:
            agent_name: The name of the agent to add
            definition: The agent definition
            
        Returns:
            The added agent configuration
        """
        ...
    
    def set_default_agent(self, agent_name: str) -> None:
        """
        Set the default agent for the message file.
        
        Args:
            agent_name: The name of the agent to set as default
            
        Raises:
            ValueError: If the agent is not found
        """
        ...
    
    def default_agent(self) -> Optional[Dict[str, Any]]:
        """
        Get the default agent for the message file.
        
        Returns:
            The default agent configuration, or None if no default agent is set
        """
        ...
    
    def add_message(self, content: str, name: Optional[str] = None, mime_type: str = "text/plain", 
                   agent_name: Optional[str] = None, timeout: Optional[int] = None) -> Message:
        """
        Add a message to the file.
        
        Args:
            content: The content of the message
            name: Optional name for the message
            mime_type: The MIME type of the content (default: text/plain)
            agent_name: Optional name of the agent that generated the message
            timeout: Optional timeout in seconds
            
        Returns:
            The added message
            
        Raises:
            ValueError: If no default agent is set and agent_name is None
        """
        ...
    
    def add_function_call(self, message_name: str, function_name: str, args: Optional[Dict[str, Any]] = None,
                         name: Optional[str] = None, timeout: Optional[int] = None) -> FunctionCall:
        """
        Add a function call to the file.
        
        Args:
            message_name: The name of the message to which the function call is added
            function_name: The name of the function to call
            args: Optional arguments for the function
            name: Optional name for the function call
            timeout: Optional timeout in seconds
            
        Returns:
            The added function call
        """
        ...
    
    def get_item(self, index_or_name: Union[int, str]) -> Optional[MessageItem]:
        """
        Get a message item by index or name.
        
        Args:
            index_or_name: The index or name of the item to get
            
        Returns:
            The message item, or None if not found
        """
        ...
    
    def save(self) -> None:
        """Save the message file."""
        ...
    
    def load(self) -> None:
        """Load the message file from disk."""
        ...
