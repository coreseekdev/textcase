"""Protocol definitions for message files."""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, List, Optional, Any, Union, Tuple, overload, Protocol, TypeVar, Generic


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
    
    @abstractmethod
    def to_dict(self) -> Dict[str, Any]:
        """Convert the output to a dictionary."""
        ...


class MessageOutputBuilder(Protocol):
    """Builder for creating MessageOutput instances."""
    
    @abstractmethod
    def with_content(self, content: str) -> 'MessageOutputBuilder':
        """Set the content of the output."""
        ...
    
    @abstractmethod
    def with_mime_type(self, mime_type: str) -> 'MessageOutputBuilder':
        """Set the MIME type of the content."""
        ...
    
    @abstractmethod
    def with_nonce(self, nonce: str) -> 'MessageOutputBuilder':
        """Set the unique identifier for the output."""
        ...
    
    @abstractmethod
    def build(self) -> MessageOutput:
        """Build and return a MessageOutput instance."""
        ...


T_MessageItem = TypeVar('T_MessageItem', bound='MessageItem')

class MessageItemBuilder(Generic[T_MessageItem]):
    """Base builder for message items."""
    
    @abstractmethod
    def with_name(self, name: str) -> 'MessageItemBuilder[T_MessageItem]':
        """Set the name of the message item."""
        ...
    
    @abstractmethod
    def with_timeout(self, timeout: int) -> 'MessageItemBuilder[T_MessageItem]':
        """Set the timeout in seconds."""
        ...
    
    @abstractmethod
    def with_output(self, output: MessageOutput) -> 'MessageItemBuilder[T_MessageItem]':
        """Add an output to the message item."""
        ...
    
    @abstractmethod
    def build(self) -> T_MessageItem:
        """Build and return a MessageItem instance."""
        ...


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
    
    @abstractmethod
    def add_output(self, output: MessageOutput) -> None:
        """Add an output to the message item."""
        ...
    
    @abstractmethod
    def to_dict(self) -> Dict[str, Any]:
        """Convert the message item to a dictionary."""
        ...


class FunctionCall(Protocol):
    """Protocol for function calls in a message file."""
    
    @property
    def function_name(self) -> str:
        """Get the name of the function to call."""
        ...
    
    @property
    def args(self) -> Dict[str, Any]:
        """Get the arguments for the function."""
        ...
    
    @property
    def name(self) -> Optional[str]:
        """Get the name of the function call."""
        ...
    
    @property
    def timeout(self) -> Optional[int]:
        """Get the timeout in seconds."""
        ...
    
    @property
    def outputs(self) -> List[MessageOutput]:
        """Get the outputs of the function call."""
        ...
    
    @property
    def type(self) -> str:
        """Get the type of the function call."""
        ...
    
    @abstractmethod
    def add_output(self, output: MessageOutput) -> None:
        """Add an output to the function call."""
        ...
    
    @abstractmethod
    def to_dict(self) -> Dict[str, Any]:
        """Convert the function call to a dictionary."""
        ...


class Message(Protocol):
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
    
    @property
    def name(self) -> Optional[str]:
        """Get the name of the message."""
        ...
    
    @property
    def timeout(self) -> Optional[int]:
        """Get the timeout in seconds."""
        ...
    
    @property
    def outputs(self) -> List[MessageOutput]:
        """Get the outputs of the message."""
        ...
    
    @property
    def type(self) -> str:
        """Get the type of the message."""
        ...
    
    @abstractmethod
    def add_output(self, output: MessageOutput) -> None:
        """Add an output to the message."""
        ...
    
    @abstractmethod
    def add_function_call(self, function_call: FunctionCall) -> None:
        """Add a function call to the message."""
        ...
    
    @abstractmethod
    def to_dict(self) -> Dict[str, Any]:
        """Convert the message to a dictionary."""
        ...


# Factory methods for creating message items from dictionaries
def create_message_item_from_dict(data: Dict[str, Any]) -> MessageItem:
    """Create a message item from a dictionary.
    
    This is a factory method that creates the appropriate message item based on the data.
    The concrete implementation will be provided by the concrete classes.
    
    Args:
        data: The dictionary containing the message item data
        
    Returns:
        A MessageItem instance (either Message or FunctionCall)
    """
    # Implementation will be provided by concrete classes
    ...


class FunctionCallBuilder(MessageItemBuilder['FunctionCall']):
    """Builder for creating FunctionCall instances."""
    
    @abstractmethod
    def with_function_name(self, function_name: str) -> 'FunctionCallBuilder':
        """Set the name of the function to call."""
        ...
    
    @abstractmethod
    def with_args(self, args: Dict[str, Any]) -> 'FunctionCallBuilder':
        """Set the arguments for the function."""
        ...


class MessageBuilder(MessageItemBuilder['Message']):
    """Builder for creating Message instances."""
    
    @abstractmethod
    def with_content(self, content: str) -> 'MessageBuilder':
        """Set the content of the message."""
        ...
    
    @abstractmethod
    def with_mime_type(self, mime_type: str) -> 'MessageBuilder':
        """Set the MIME type of the content."""
        ...
    
    @abstractmethod
    def with_agent_name(self, agent_name: str) -> 'MessageBuilder':
        """Set the name of the agent that generated the message."""
        ...
    
    @abstractmethod
    def with_function_call(self, function_call: FunctionCall) -> 'MessageBuilder':
        """Add a function call to the message."""
        ...


class MessageFile(ABC):
    """Protocol for message files."""
    
    @abstractmethod
    def get_path(self) -> Path:
        """Get the path to the message file."""
        ...
    
    @abstractmethod
    def get_items(self) -> List[MessageItem]:
        """Get all message items (messages and function calls) in the file."""
        ...
    
    @abstractmethod
    def get_agents(self) -> List[Dict[str, Any]]:
        """Get all agents defined in the file."""
        ...
    
    @abstractmethod
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
    
    @abstractmethod
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
    
    @abstractmethod
    def set_default_agent(self, agent_name: str) -> None:
        """
        Set the default agent for the message file.
        
        Args:
            agent_name: The name of the agent to set as default
            
        Raises:
            ValueError: If the agent is not found
        """
        ...
    
    @abstractmethod
    def default_agent(self) -> Optional[Dict[str, Any]]:
        """
        Get the default agent for the message file.
        
        Returns:
            The default agent configuration, or None if no default agent is set
        """
        ...
    
    @abstractmethod
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
    
    @abstractmethod
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
    
    @abstractmethod
    def get_item(self, index_or_name: Union[int, str]) -> Optional[MessageItem]:
        """
        Get a message item by index or name.
        
        Args:
            index_or_name: The index or name of the item to get
            
        Returns:
            The message item, or None if not found
        """
        ...
    
    @abstractmethod
    def save(self) -> None:
        """Save the message file."""
        ...
    
    @abstractmethod
    def load(self) -> None:
        """Load the message file from disk."""
        ...
