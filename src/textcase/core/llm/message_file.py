"""Implementation of the MessageFile protocol."""

import os
import uuid
import json
from pathlib import Path
from typing import Dict, List, Optional, Any, Union, cast

import frontmatter
from markdown_it import MarkdownIt

from textcase.protocol.vfs import VFS
from textcase.protocol.message import (
    MessageFile as MessageFileProtocol,
    Message, MessageOutput, MessageItem, FunctionCall
)
from textcase.core.project import Project
from textcase.core.logging import get_logger

# Get logger for this module
logger = get_logger(__name__)


class MarkdownMessageFile(MessageFileProtocol):
    """Implementation of the MessageFile protocol using markdown files with frontmatter."""
    
    def __init__(self, project: Project, path: Path):
        """
        Initialize a message file.
        
        Args:
            project: The project this message file belongs to
            path: Path to the message file
        """
        self.project = project
        self._path = path
        self._vfs = project._vfs  # Access protected member for VFS
        
        # Initialize data structures
        self.items: List[Union[Message, FunctionCall]] = []
        self.agents: List[Dict[str, Any]] = []
        self._default_agent_name: Optional[str] = None
        
        # Load the file if it exists
        if self._vfs.exists(self._path):
            self.load()
    
    def get_path(self) -> Path:
        """Get the path to the message file."""
        return self._path
    
    def get_items(self) -> List[Union[Message, FunctionCall]]:
        """Get all message items (messages and function calls) in the file."""
        return self.items
    
    def get_agents(self) -> List[Dict[str, Any]]:
        """Get all agents defined in the file."""
        return self.agents
    
    def get_item(self, index_or_name: Union[int, str]) -> Optional[Union[Message, FunctionCall]]:
        """
        Get a message item by index or name.
        
        Args:
            index_or_name: The index or name of the item to get
            
        Returns:
            The message item, or None if not found
        """
        if isinstance(index_or_name, int):
            if 0 <= index_or_name < len(self.items):
                return self.items[index_or_name]
            return None
        else:  # str
            for item in self.items:
                if item.name == index_or_name:
                    return item
            return None
    
    def __getitem__(self, index_or_name: Union[int, str]) -> Union[Message, FunctionCall]:
        """
        Get a message item by index or name.
        
        Args:
            index_or_name: The index or name of the item to get
            
        Returns:
            The message item
            
        Raises:
            KeyError: If the item is not found
        """
        item = self.get_item(index_or_name)
        if item is None:
            raise KeyError(f"Item '{index_or_name}' not found")
        return item
    
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
        """
        # Generate a name if not provided
        if name is None:
            name = f"item_{len(self.items) + 1}"
        elif self.get_item(name) is not None:
            raise ValueError(f"Item with name '{name}' already exists")
        
        # Create the message
        message = Message(content, name, mime_type, agent_name, timeout)
        
        # Add to the list
        self.items.append(message)
        
        # Save the file
        self.save()
        
        return message
    
    def add_function_call(self, function_name: str, args: Optional[Dict[str, Any]] = None,
                         name: Optional[str] = None, timeout: Optional[int] = None) -> FunctionCall:
        """
        Add a function call to the file.
        
        Args:
            function_name: The name of the function to call
            args: Optional arguments for the function
            name: Optional name for the function call
            timeout: Optional timeout in seconds
            
        Returns:
            The added function call
        """
        # Generate a name if not provided
        if name is None:
            name = f"item_{len(self.items) + 1}"
        elif self.get_item(name) is not None:
            raise ValueError(f"Item with name '{name}' already exists")
        
        # Create the function call
        function_call = FunctionCall(function_name, args, name, timeout)
        
        # Add to the list
        self.items.append(function_call)
        
        # Save the file
        self.save()
        
        return function_call
    
    def save(self) -> None:
        """Save the message file."""
        # Create the parent directory if it doesn't exist
        parent_dir = self._path.parent
        if not self._vfs.exists(parent_dir):
            self._vfs.makedirs(parent_dir)
        
        # Prepare the frontmatter data
        metadata = {
            "agents": [agent for agent in self.agents]
        }
        
        # Prepare the content
        content = self._serialize_items()
        
        # Create the frontmatter post
        post = frontmatter.Post(content, **metadata)
        
        # Write to file
        with self._vfs.open(self._path, "w") as f:
            f.write(frontmatter.dumps(post))
        
        logger.info(f"Saved message file to {self._path}")
    
    def load(self) -> None:
        """Load the message file from disk."""
        try:
            # Read the file
            with self._vfs.open(self._path, "r") as f:
                post = frontmatter.load(f)
            
            # Extract the frontmatter
            metadata = dict(post.metadata)
            
            # Extract agents
            self.agents = metadata.get("agents", [])
            
            # Parse the content to extract items
            self.items = self._parse_items(post.content)
            
            logger.info(f"Loaded message file from {self._path}")
        except Exception as e:
            logger.exception(f"Error loading message file: {str(e)}")
            # Initialize empty structures
            self.items = []
            self.agents = []
    
    def _serialize_items(self) -> str:
        """Serialize message items to a string."""
        # Convert items to a list of dictionaries
        item_dicts = [item.to_dict() for item in self.items]
        
        # Format as JSON with indentation
        return json.dumps(item_dicts, indent=2)
    
    def _parse_items(self, content: str) -> List[Union[Message, FunctionCall]]:
        """Parse message items from a string."""
        try:
            # Parse the JSON content
            item_dicts = json.loads(content)
            
            # Convert dictionaries to Message or FunctionCall objects
            items = []
            for data in item_dicts:
                if data.get("type") == "function_call":
                    items.append(FunctionCall.from_dict(data))
                else:  # message
                    items.append(Message.from_dict(data))
            return items
        except json.JSONDecodeError:
            logger.warning(f"Failed to parse items as JSON, trying to parse as markdown")
            return self._parse_items_from_markdown(content)
    
    def _parse_items_from_markdown(self, content: str) -> List[Union[Message, FunctionCall]]:
        """Parse message items from markdown content."""
        # This is a placeholder for future implementation
        # In a real implementation, this would parse markdown sections into messages and function calls
        logger.warning("Markdown parsing not fully implemented, returning empty item list")
        return []


class MessageFileFactory:
    """Factory for creating MessageFile instances."""
    
    @staticmethod
    def create_message_file(project: Project, path: Path) -> MessageFileProtocol:
        """
        Create a MessageFile instance.
        
        Args:
            project: The project this message file belongs to
            path: Path to the message file
            
        Returns:
            A MessageFile instance
        """
        # Ensure the path has the correct extension
        if not str(path).endswith(".msg.md"):
            path = Path(f"{path}.msg.md")
        
        return MarkdownMessageFile(project, path)
    
    @staticmethod
    def get_message_file(project: Project, module_prefix: str, item_id: str) -> MessageFileProtocol:
        """
        Get a MessageFile instance for a specific module item.
        
        Args:
            project: The project this message file belongs to
            module_prefix: The prefix of the module (e.g., 'CHAT')
            item_id: The ID of the item (e.g., '001')
            
        Returns:
            A MessageFile instance
        """
        # Find the module
        module = None
        if project.prefix == module_prefix:
            module = project
        else:
            for submodule in project.get_submodules():
                if hasattr(submodule, 'prefix') and submodule.prefix == module_prefix:
                    module = submodule
                    break
        
        if module is None:
            raise ValueError(f"Module with prefix '{module_prefix}' not found")
        
        # Get module settings
        settings = module.config.settings
        separator = settings.get('sep', '')
        
        # Format the item ID
        full_id = f"{module_prefix}{separator}{item_id}"
        
        # Create the path
        path = module.path / f"{full_id}.msg.md"
        
        return MarkdownMessageFile(project, path)
