"""Implementation of the MessageFile protocol according to REQ010 specifications.

This module provides classes for working with message files in Markdown format,
which use percent notation and footnote syntax for metadata.
"""

import os
import re
import uuid
import json
import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Union, Tuple, cast

import frontmatter
from markdown_it import MarkdownIt
from markdown_it.token import Token

from textcase.protocol.vfs import VFS
from textcase.protocol.message import (
    MessageOutput, CodeExecutionOutput, MessageItem, Message, 
    FunctionCall, MessageStore
)
from textcase.protocol.agent import AgentProtocol, AgentFactoryProtocol
from textcase.core.project import Project
from textcase.core.logging import get_logger
from textcase.core.markdown_ast import parse_markdown, RootNode, HeadingNode

# Get logger for this module
logger = get_logger(__name__)

# Regular expressions for parsing message files
PERCENT_PATTERN = re.compile(r'^(#{1,5})\s*(%{2,3})(?:\s+([^\[]+))?(?:\[(\^[^\]]+)\])?')
FOOTNOTE_PATTERN = re.compile(r'^\[(\^[^\]]+)\]:\s*\[([^\]]+)\](.*)')
FOOTNOTE_ATTR_PATTERN = re.compile(r'(\w+)=(?:"([^"]*)"|(\S+))')


class BaseMessageOutput:
    """Base implementation of the MessageOutput protocol."""
    
    def __init__(self, content_value: str, mime_type_value: str = "text/plain", nonce_value: Optional[str] = None):
        """Initialize a message output.
        
        Args:
            content_value: The content of the output
            mime_type_value: The MIME type of the content (default: text/plain)
            nonce_value: Optional unique identifier for the output
        """
        self._content = content_value
        self._mime_type = mime_type_value
        self._nonce = nonce_value or str(uuid.uuid4())
        
    @property
    def content(self) -> str:
        """Get the content of the output."""
        return self._content
    
    @property
    def mime_type(self) -> str:
        """Get the MIME type of the content."""
        return self._mime_type
    
    @property
    def nonce(self) -> Optional[str]:
        """Get the unique identifier for the output."""
        return self._nonce
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert the output to a dictionary."""
        return {
            "content": self._content,
            "mime_type": self._mime_type,
            "nonce": self._nonce
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'BaseMessageOutput':
        """Create a message output from a dictionary."""
        return cls(
            content_value=data.get("content", ""),
            mime_type_value=data.get("mime_type", "text/plain"),
            nonce_value=data.get("nonce")
        )


class BaseCodeExecutionOutput(BaseMessageOutput):
    """Base implementation of the CodeExecutionOutput protocol."""
    
    def __init__(
        self, 
        stdout_value: str = "", 
        stderr_value: str = "", 
        status_value: int = 0, 
        duration_value: float = 0.0, 
        lang_value: str = "python",
        mime_type_value: str = "text/plain",
        nonce_value: Optional[str] = None
    ):
        """Initialize a code execution output.
        
        Args:
            stdout_value: The standard output content
            stderr_value: The standard error content
            status_value: The execution status code
            duration_value: The execution duration in seconds
            lang_value: The programming language of the executed code
            mime_type_value: The MIME type of the content
            nonce_value: Optional unique identifier for the output
        """
        # Format the content with stdout and stderr prefixes
        content_lines = []
        if stdout_value:
            for line in stdout_value.splitlines():
                content_lines.append(f"stdout> {line}")
        if stderr_value:
            for line in stderr_value.splitlines():
                content_lines.append(f"stderr> {line}")
        
        content = "\n".join(content_lines)
        super().__init__(content, mime_type_value, nonce_value)
        
        self._stdout = stdout_value
        self._stderr = stderr_value
        self._status = status_value
        self._duration = duration_value
        self._lang = lang_value
    
    @property
    def stdout_content(self) -> str:
        """Get the standard output content."""
        return self._stdout
    
    @property
    def stderr_content(self) -> str:
        """Get the standard error content."""
        return self._stderr
    
    @property
    def status(self) -> int:
        """Get the execution status code."""
        return self._status
    
    @property
    def duration(self) -> float:
        """Get the execution duration in seconds."""
        return self._duration
    
    @property
    def lang(self) -> str:
        """Get the programming language of the executed code."""
        return self._lang
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert the code execution output to a dictionary."""
        result = super().to_dict()
        result.update({
            "stdout": self._stdout,
            "stderr": self._stderr,
            "status": self._status,
            "duration": self._duration,
            "lang": self._lang
        })
        return result
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'BaseCodeExecutionOutput':
        """Create a code execution output from a dictionary."""
        return cls(
            stdout_value=data.get("stdout", ""),
            stderr_value=data.get("stderr", ""),
            status_value=data.get("status", 0),
            duration_value=data.get("duration", 0.0),
            lang_value=data.get("lang", "python"),
            mime_type_value=data.get("mime_type", "text/plain"),
            nonce_value=data.get("nonce")
        )


class BaseMessageItem:
    """Base implementation of the MessageItem protocol."""
    
    def __init__(
        self, 
        name_value: Optional[str] = None, 
        timeout_value: Optional[int] = None,
        heading_level_value: Optional[int] = None
    ):
        """Initialize a message item.
        
        Args:
            name_value: Optional name for the message item
            timeout_value: Optional timeout in seconds
            heading_level_value: Optional heading level (1-5)
        """
        self._name = name_value
        self._timeout = timeout_value
        self._outputs: List[MessageOutput] = []
        self._history: List[Dict[str, Any]] = []
        self._heading_level = heading_level_value
    
    @property
    def name(self) -> Optional[str]:
        """Get the name of the message item."""
        return self._name
    
    @property
    def timeout(self) -> Optional[int]:
        """Get the timeout in seconds."""
        return self._timeout
    
    @property
    def outputs(self) -> List[MessageOutput]:
        """Get the outputs of the message item."""
        return self._outputs
    
    @property
    def type(self) -> str:
        """Get the type of the message item."""
        return "message_item"
    
    @property
    def history(self) -> List[Dict[str, Any]]:
        """Get the history of the message item."""
        return self._history
    
    @property
    def heading_level(self) -> Optional[int]:
        """Get the heading level of the message item."""
        return self._heading_level
    
    def add_output(self, output: MessageOutput) -> None:
        """Add an output to the message item."""
        self._outputs.append(output)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert the message item to a dictionary."""
        return {
            "name": self._name,
            "timeout": self._timeout,
            "outputs": [output.to_dict() for output in self._outputs],
            "type": self.type,
            "history": self._history.copy(),
            "heading_level": self._heading_level
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'BaseMessageItem':
        """Create a message item from a dictionary."""
        item = cls(
            name_value=data.get("name"),
            timeout_value=data.get("timeout"),
            heading_level_value=data.get("heading_level")
        )
        
        # Add outputs
        for output_data in data.get("outputs", []):
            if "stdout" in output_data or "stderr" in output_data:
                output = BaseCodeExecutionOutput.from_dict(output_data)
            else:
                output = BaseMessageOutput.from_dict(output_data)
            item.add_output(output)
        
        # Add history
        item._history = data.get("history", []).copy()
        
        return item


class BaseMessage(BaseMessageItem):
    """Base implementation of the Message protocol."""
    
    def __init__(
        self, 
        content_value: str, 
        name_value: Optional[str] = None, 
        mime_type_value: str = "text/plain",
        agent_name_value: Optional[str] = None, 
        timeout_value: Optional[int] = None,
        heading_level_value: Optional[int] = None
    ):
        """Initialize a message.
        
        Args:
            content_value: The content of the message
            name_value: Optional name for the message
            mime_type_value: The MIME type of the content (default: text/plain)
            agent_name_value: Optional name of the agent that generated the message
            timeout_value: Optional timeout in seconds
            heading_level_value: Optional heading level (1-5)
        """
        super().__init__(name_value, timeout_value, heading_level_value)
        self._content = content_value
        self._mime_type = mime_type_value
        self._agent_name = agent_name_value
        self._function_calls: List[BaseFunctionCall] = []
    
    @property
    def content(self) -> str:
        """Get the content of the message."""
        return self._content
    
    @property
    def mime_type(self) -> str:
        """Get the MIME type of the content."""
        return self._mime_type
    
    @property
    def agent_name(self) -> Optional[str]:
        """Get the name of the agent that generated the message."""
        return self._agent_name
    
    @property
    def type(self) -> str:
        """Get the type of the message item."""
        return "message"
    
    def add_function_call(
        self, 
        function_name: str, 
        args: Optional[Dict[str, Any]] = None,
        name: Optional[str] = None, 
        timeout: Optional[int] = None
    ) -> 'BaseFunctionCall':
        """Add a function call to the message.
        
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
            name = f"{self.name}_func_{len(self._function_calls) + 1}"
        
        # Create the function call
        function_call = BaseFunctionCall(
            function_name_value=function_name,
            args_value=args or {},
            name_value=name,
            timeout_value=timeout,
            heading_level_value=self.heading_level + 1 if self.heading_level is not None else None
        )
        
        # Add to the list
        self._function_calls.append(function_call)
        
        return function_call
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert the message to a dictionary."""
        result = super().to_dict()
        result.update({
            "content": self._content,
            "mime_type": self._mime_type,
            "agent_name": self._agent_name,
            "function_calls": [fc.to_dict() for fc in self._function_calls]
        })
        return result
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'BaseMessage':
        """Create a message from a dictionary."""
        message = cls(
            content_value=data.get("content", ""),
            name_value=data.get("name"),
            mime_type_value=data.get("mime_type", "text/plain"),
            agent_name_value=data.get("agent_name"),
            timeout_value=data.get("timeout"),
            heading_level_value=data.get("heading_level")
        )
        
        # Add outputs
        for output_data in data.get("outputs", []):
            if "stdout" in output_data or "stderr" in output_data:
                output = BaseCodeExecutionOutput.from_dict(output_data)
            else:
                output = BaseMessageOutput.from_dict(output_data)
            message.add_output(output)
        
        # Add function calls
        for fc_data in data.get("function_calls", []):
            fc = BaseFunctionCall.from_dict(fc_data)
            message._function_calls.append(fc)
        
        # Add history
        message._history = data.get("history", []).copy()
        
        return message


class BaseFunctionCall(BaseMessageItem):
    """Base implementation of the FunctionCall protocol."""
    
    def __init__(
        self, 
        function_name_value: str, 
        args_value: Dict[str, Any] = None,
        name_value: Optional[str] = None, 
        timeout_value: Optional[int] = None,
        heading_level_value: Optional[int] = None
    ):
        """Initialize a function call.
        
        Args:
            function_name_value: The name of the function to call
            args_value: Arguments for the function
            name_value: Optional name for the function call
            timeout_value: Optional timeout in seconds
            heading_level_value: Optional heading level (1-5)
        """
        super().__init__(name_value, timeout_value, heading_level_value)
        self._function_name = function_name_value
        self._args = args_value or {}
    
    @property
    def function_name(self) -> str:
        """Get the name of the function."""
        return self._function_name
    
    @property
    def args(self) -> Dict[str, Any]:
        """Get the arguments for the function."""
        return self._args
    
    @property
    def type(self) -> str:
        """Get the type of the message item."""
        return "function_call"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert the function call to a dictionary."""
        result = super().to_dict()
        result.update({
            "function_name": self._function_name,
            "args": self._args
        })
        return result
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'BaseFunctionCall':
        """Create a function call from a dictionary."""
        fc = cls(
            function_name_value=data.get("function_name", ""),
            args_value=data.get("args", {}),
            name_value=data.get("name"),
            timeout_value=data.get("timeout"),
            heading_level_value=data.get("heading_level")
        )
        
        # Add outputs
        for output_data in data.get("outputs", []):
            if "stdout" in output_data or "stderr" in output_data:
                output = BaseCodeExecutionOutput.from_dict(output_data)
            else:
                output = BaseMessageOutput.from_dict(output_data)
            fc.add_output(output)
        
        # Add history
        fc._history = data.get("history", []).copy()
        
        return fc


class MarkdownMessageFile(MessageStore):
    """Implementation of the MessageStore protocol using Markdown files.
    
    This class handles parsing and serializing message files according to REQ010 specifications,
    which use percent notation and footnote syntax for metadata.
    """
    
    def __init__(self, path: Optional[str] = None, vfs: Optional[VFS] = None):
        """Initialize a markdown message file.
        
        Args:
            path: Optional path to the message file
            vfs: Optional virtual file system to use
        """
        self._path = path
        self._vfs = vfs
        self._message_items: List[MessageItem] = []
        self._agents: Dict[str, Dict[str, Any]] = {}
        self._default_agent: Optional[str] = None
        self._frontmatter: Dict[str, Any] = {}
        
        # Load the file if a path is provided
        if path is not None and vfs is not None:
            self.load()
    
    @property
    def path(self) -> Optional[str]:
        """Get the path to the message file."""
        return self._path
    
    @path.setter
    def path(self, value: str) -> None:
        """Set the path to the message file."""
        self._path = value
    
    @property
    def vfs(self) -> Optional[VFS]:
        """Get the virtual file system."""
        return self._vfs
    
    @vfs.setter
    def vfs(self, value: VFS) -> None:
        """Set the virtual file system."""
        self._vfs = value
    
    @property
    def message_items(self) -> List[MessageItem]:
        """Get the message items."""
        return self._message_items
    
    @property
    def agents(self) -> Dict[str, Dict[str, Any]]:
        """Get the agents."""
        return self._agents
    
    @property
    def default_agent(self) -> Optional[str]:
        """Get the default agent."""
        return self._default_agent
    
    def set_default_agent(self, agent_name: str) -> None:
        """Set the default agent.
        
        Args:
            agent_name: The name of the agent to set as default
        """
        if agent_name in self._agents:
            self._default_agent = agent_name
        else:
            logger.warning(f"Agent '{agent_name}' not found, cannot set as default")
    
    def add_agent(self, agent_name: str, agent_data: Dict[str, Any]) -> None:
        """Add an agent.
        
        Args:
            agent_name: The name of the agent
            agent_data: The agent data
        """
        self._agents[agent_name] = agent_data
        
        # Set as default if no default is set
        if self._default_agent is None:
            self._default_agent = agent_name
    
    def add_message_item(self, item: MessageItem) -> None:
        """Add a message item.
        
        Args:
            item: The message item to add
        """
        self._message_items.append(item)
    
    # MessageStore protocol methods
    def add_message(self, content: str, agent_name: Optional[str] = None, name: Optional[str] = None, 
                    mime_type: str = "text/plain", timeout: Optional[int] = None) -> Message:
        """Add a message to the store.
        
        Args:
            content: The content of the message
            agent_name: Optional name of the agent that generated the message
            name: Optional name for the message
            mime_type: The MIME type of the content (default: text/plain)
            timeout: Optional timeout in seconds
            
        Returns:
            The added message
        """
        # Generate a name if not provided
        if name is None:
            name = f"message_{len(self._message_items) + 1}"
        
        # Determine heading level (use 1 for top-level messages)
        heading_level = 1
        
        # Create the message
        message = BaseMessage(
            content_value=content,
            name_value=name,
            mime_type_value=mime_type,
            agent_name_value=agent_name or self._default_agent,
            timeout_value=timeout,
            heading_level_value=heading_level
        )
        
        # Add to the list
        self.add_message_item(message)
        
        return message
    
    def add_function_call(self, function_name: str, args: Optional[Dict[str, Any]] = None,
                        name: Optional[str] = None, timeout: Optional[int] = None) -> FunctionCall:
        """Add a function call to the store.
        
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
            name = f"function_{len(self._message_items) + 1}"
        
        # Determine heading level (use 1 for top-level function calls)
        heading_level = 1
        
        # Create the function call
        function_call = BaseFunctionCall(
            function_name_value=function_name,
            args_value=args or {},
            name_value=name,
            timeout_value=timeout,
            heading_level_value=heading_level
        )
        
        # Add to the list
        self.add_message_item(function_call)
        
        return function_call
    
    def get_message_item(self, name: str) -> Optional[MessageItem]:
        """Get a message item by name.
        
        Args:
            name: The name of the message item to get
            
        Returns:
            The message item, or None if not found
        """
        for item in self._message_items:
            if item.name == name:
                return item
        return None
    
    def get_message_items(self) -> List[MessageItem]:
        """Get all message items.
        
        Returns:
            The list of message items
        """
        return self._message_items
    
    def clear(self) -> None:
        """Clear all message items."""
        self._message_items = []
    
    def load(self) -> None:
        """Load the message file from disk."""
        if not self._vfs.exists(self._path):
            # File doesn't exist, create an empty file
            self.save()
            return
        
        # Read the file content
        content = ""
        with self._vfs.open(self._path, "r") as f:
            content = f.read().decode("utf-8")
        
        # Parse the markdown content
        self._parse_markdown(content)
    
    def save(self) -> None:
        """Save the message file to disk."""
        if self._path is None or self._vfs is None:
            logger.error("Cannot save message file: path or vfs not set")
            return
        
        # Generate the markdown content
        content = self._generate_markdown()
        
        # Write the content to the file
        with self._vfs.open(self._path, "w") as f:
            f.write(content.encode("utf-8"))
    
    def _parse_markdown(self, content: str) -> None:
        """Parse the markdown content.
        
        Args:
            content: The markdown content to parse
        """
        # Reset state
        self._message_items = []
        self._agents = {}
        self._default_agent = None
        
        # Parse frontmatter
        parsed = frontmatter.loads(content)
        self._frontmatter = dict(parsed.metadata)
        content_without_frontmatter = parsed.content
        
        # Extract agents from frontmatter
        if "agents" in self._frontmatter:
            for agent_name, agent_data in self._frontmatter["agents"].items():
                self.add_agent(agent_name, agent_data)
        
        # Set default agent if specified
        if "default_agent" in self._frontmatter and self._frontmatter["default_agent"] in self._agents:
            self._default_agent = self._frontmatter["default_agent"]
        
        # Parse the markdown content using markdown_ast
        from textcase.core.markdown_ast import parse_markdown
        markdown_ast = parse_markdown(content_without_frontmatter)
        
        # Collect footnotes from the content
        footnotes = self._collect_footnotes(content_without_frontmatter)
        
        # Parse message and output cells using the AST
        self._parse_cells(markdown_ast, content_without_frontmatter, footnotes)
    
    def _collect_footnotes(self, content: str) -> Dict[str, Dict[str, Any]]:
        """Collect footnotes from the markdown content.
        
        Args:
            content: The markdown content to parse
            
        Returns:
            A dictionary of footnotes, keyed by footnote ID
        """
        footnotes: Dict[str, Dict[str, Any]] = {}
        
        # Process each line to find footnotes
        for line in content.splitlines():
            footnote_match = FOOTNOTE_PATTERN.match(line.strip())
            if footnote_match:
                footnote_id = footnote_match.group(1)  # e.g., ^1
                footnote_type = footnote_match.group(2)  # e.g., message, function_call
                footnote_attrs_text = footnote_match.group(3)  # e.g., name="foo" timeout=30
                
                # Parse attributes
                attrs = {}
                for attr_match in FOOTNOTE_ATTR_PATTERN.finditer(footnote_attrs_text):
                    attr_name = attr_match.group(1)
                    # Use quoted value if available, otherwise use unquoted value
                    attr_value = attr_match.group(2) if attr_match.group(2) is not None else attr_match.group(3)
                    
                    # Convert special values
                    if attr_value.lower() == "true":
                        attr_value = True
                    elif attr_value.lower() == "false":
                        attr_value = False
                    elif attr_value.isdigit():
                        attr_value = int(attr_value)
                    elif attr_value.replace(".", "", 1).isdigit() and attr_value.count(".") == 1:
                        attr_value = float(attr_value)
                    
                    attrs[attr_name] = attr_value
                
                # Store footnote data
                footnotes[footnote_id] = {
                    "type": footnote_type,
                    "attrs": attrs
                }
                
        return footnotes
    
    def _parse_cells(self, markdown_ast, content: str, footnotes: Dict[str, Dict[str, Any]]) -> None:
        """Parse message and output cells from markdown AST.
        
        Args:
            markdown_ast: The parsed markdown AST
            content: The original markdown content
            footnotes: Dictionary of footnotes extracted from the content
        """
        # Extract lines for content extraction
        lines = content.splitlines()
        
        # Process each line to find percent notation cells
        current_cell_lines: List[str] = []
        current_cell_type: Optional[str] = None
        current_cell_heading_level: Optional[int] = None
        current_cell_footnote: Optional[str] = None
        current_cell_title: Optional[str] = None
        current_line_index: int = 0
        cell_start_line: int = 0
        
        # Helper function to extract content between line ranges
        def extract_content(start_line: int, end_line: int) -> str:
            return "\n".join(lines[start_line:end_line]).strip()
        
        # Helper function to process the current cell
        def process_current_cell(end_line: int):
            nonlocal current_cell_lines, current_cell_type, current_cell_heading_level, current_cell_footnote, current_cell_title, cell_start_line
            
            if current_cell_type:
                # Extract cell content from the original content
                cell_content = extract_content(cell_start_line, end_line)
                
                if current_cell_type == "message":
                    # Get footnote data if available
                    footnote_data = footnotes.get(current_cell_footnote, {}) if current_cell_footnote else {}
                    footnote_attrs = footnote_data.get("attrs", {})
                    
                    # Create message
                    message = BaseMessage(
                        content_value=cell_content,
                        name_value=footnote_attrs.get("name", current_cell_title),
                        mime_type_value=footnote_attrs.get("mime_type", "text/plain"),
                        agent_name_value=footnote_attrs.get("agent_name"),
                        timeout_value=footnote_attrs.get("timeout"),
                        heading_level_value=current_cell_heading_level
                    )
                    
                    # Add to message items
                    self._message_items.append(message)
                    
                elif current_cell_type == "function_call":
                    # Get footnote data if available
                    footnote_data = footnotes.get(current_cell_footnote, {}) if current_cell_footnote else {}
                    footnote_attrs = footnote_data.get("attrs", {})
                    
                    # Parse function name and args from content
                    function_name = footnote_attrs.get("function_name", "")
                    args_str = footnote_attrs.get("args", "{}")
                    
                    # Try to parse args as JSON
                    try:
                        args = json.loads(args_str) if isinstance(args_str, str) else args_str
                    except json.JSONDecodeError:
                        logger.warning(f"Failed to parse function args: {args_str}")
                        args = {}
                    
                    # Create function call
                    fc = BaseFunctionCall(
                        function_name_value=function_name,
                        args_value=args,
                        name_value=footnote_attrs.get("name", current_cell_title),
                        timeout_value=footnote_attrs.get("timeout"),
                        heading_level_value=current_cell_heading_level
                    )
                    
                    # Add to message items
                    self._message_items.append(fc)
                    
                elif current_cell_type == "output":
                    # Get footnote data if available
                    footnote_data = footnotes.get(current_cell_footnote, {}) if current_cell_footnote else {}
                    footnote_attrs = footnote_data.get("attrs", {})
                    
                    # Check if this is a code execution output
                    if "stdout" in footnote_attrs or "stderr" in footnote_attrs:
                        output = BaseCodeExecutionOutput(
                            stdout_value=footnote_attrs.get("stdout", ""),
                            stderr_value=footnote_attrs.get("stderr", ""),
                            status_value=footnote_attrs.get("status", 0),
                            duration_value=footnote_attrs.get("duration", 0.0),
                            lang_value=footnote_attrs.get("lang", "python"),
                            mime_type_value=footnote_attrs.get("mime_type", "text/plain"),
                            nonce_value=footnote_attrs.get("nonce")
                        )
                    else:
                        output = BaseMessageOutput(
                            content_value=cell_content,
                            mime_type_value=footnote_attrs.get("mime_type", "text/plain"),
                            nonce_value=footnote_attrs.get("nonce")
                        )
                    
                    # Add to the last message item if available
                    if self._message_items:
                        self._message_items[-1].add_output(output)
            
            # Reset current cell
            current_cell_lines = []
            current_cell_type = None
            current_cell_heading_level = None
            current_cell_footnote = None
            current_cell_title = None
        
        # Process each line to find percent notation cells
        line_index = 0
        while line_index < len(lines):
            line = lines[line_index]
            
            # Check if this is a percent notation line
            percent_match = PERCENT_PATTERN.match(line.strip())
            if percent_match:
                # Process the previous cell if any
                if current_cell_type:
                    process_current_cell(line_index)
                
                # Extract cell information
                heading_level = len(percent_match.group(1))  # Number of # characters
                percent_count = len(percent_match.group(2))  # Number of % characters
                title = percent_match.group(3).strip() if percent_match.group(3) else None
                footnote_id = percent_match.group(4) if percent_match.group(4) else None
                
                # Set current cell information
                current_cell_heading_level = heading_level
                current_cell_footnote = footnote_id
                current_cell_title = title
                cell_start_line = line_index + 1  # Start content from the next line
                
                # Determine cell type based on percent count
                if percent_count == 2:  # %%
                    current_cell_type = "message"
                    
                    # Check footnote type if available
                    if footnote_id and footnote_id in footnotes:
                        footnote_type = footnotes[footnote_id].get("type")
                        if footnote_type == "function_call":
                            current_cell_type = "function_call"
                
                elif percent_count == 3:  # %%%
                    current_cell_type = "output"
            
            line_index += 1
        
        # Process the last cell if any
        if current_cell_type:
            process_current_cell(len(lines))
    
    def _generate_markdown(self) -> str:
        """Generate markdown content from message items.
        
        Returns:
            The generated markdown content
        """
        lines = []
        footnotes = []
        footnote_counter = 1
        
        # Add frontmatter
        frontmatter_dict = self._frontmatter.copy()
        
        # Add agents to frontmatter if not already present
        if self._agents and "agents" not in frontmatter_dict:
            frontmatter_dict["agents"] = {}
            for agent_name, agent_data in self._agents.items():
                frontmatter_dict["agents"][agent_name] = agent_data
        
        # Add default agent to frontmatter if not already present
        if self._default_agent and "default_agent" not in frontmatter_dict:
            frontmatter_dict["default_agent"] = self._default_agent
        
        # Generate frontmatter
        if frontmatter_dict:
            lines.append("---")
            for key, value in frontmatter_dict.items():
                if isinstance(value, dict):
                    lines.append(f"{key}:")
                    for k, v in value.items():
                        if isinstance(v, dict):
                            lines.append(f"  {k}:")
                            for k2, v2 in v.items():
                                lines.append(f"    {k2}: {json.dumps(v2)}")
                        else:
                            lines.append(f"  {k}: {json.dumps(v)}")
                else:
                    lines.append(f"{key}: {json.dumps(value)}")
            lines.append("---")
            lines.append("")
        
        # Generate message and output cells
        for item in self._message_items:
            # Determine heading level
            heading_level = item.heading_level or 1
            heading_prefix = "#" * heading_level
            
            # Generate footnote for the item
            footnote_id = f"^{footnote_counter}"
            footnote_counter += 1
            
            if isinstance(item, Message):
                # Add message cell
                if item.name:
                    lines.append(f"{heading_prefix} %% {item.name}[{footnote_id}]")
                else:
                    lines.append(f"{heading_prefix} %%[{footnote_id}]")
                
                # Add message content
                lines.append(item.content)
                lines.append("")
                
                # Add footnote for message
                footnote_attrs = []
                if item.name:
                    footnote_attrs.append(f'name="{item.name}"')
                if item.mime_type != "text/plain":
                    footnote_attrs.append(f'mime_type="{item.mime_type}"')
                if item.agent_name:
                    footnote_attrs.append(f'agent_name="{item.agent_name}"')
                if item.timeout is not None:
                    footnote_attrs.append(f'timeout={item.timeout}')
                
                footnotes.append(f"[{footnote_id}]: [message] {' '.join(footnote_attrs)}")
                
            elif isinstance(item, FunctionCall):
                # Add function call cell
                if item.name:
                    lines.append(f"{heading_prefix} %% {item.name}[{footnote_id}]")
                else:
                    lines.append(f"{heading_prefix} %%[{footnote_id}]")
                
                # Add function call content (empty by default)
                lines.append("")
                
                # Add footnote for function call
                footnote_attrs = []
                if item.name:
                    footnote_attrs.append(f'name="{item.name}"')
                footnote_attrs.append(f'function_name="{item.function_name}"')
                
                # Serialize args as JSON
                args_json = json.dumps(item.args)
                footnote_attrs.append(f'args="{args_json}"')
                
                if item.timeout is not None:
                    footnote_attrs.append(f'timeout={item.timeout}')
                
                footnotes.append(f"[{footnote_id}]: [function_call] {' '.join(footnote_attrs)}")
            
            # Add outputs for the item
            for output in item.outputs:
                # Generate footnote for the output
                output_footnote_id = f"^{footnote_counter}"
                footnote_counter += 1
                
                # Add output cell
                lines.append(f"{heading_prefix} %%%[{output_footnote_id}]")
                
                # Add output content
                if isinstance(output, CodeExecutionOutput):
                    # For code execution outputs, the content is already formatted
                    if output.stdout_content or output.stderr_content:
                        lines.append(output.content)
                else:
                    # For regular outputs, add the content directly
                    lines.append(output.content)
                
                lines.append("")
                
                # Add footnote for output
                output_footnote_attrs = []
                
                if output.mime_type != "text/plain":
                    output_footnote_attrs.append(f'mime_type="{output.mime_type}"')
                
                if output.nonce:
                    output_footnote_attrs.append(f'nonce="{output.nonce}"')
                
                if isinstance(output, CodeExecutionOutput):
                    if output.stdout_content:
                        output_footnote_attrs.append(f'stdout="{output.stdout_content}"')
                    if output.stderr_content:
                        output_footnote_attrs.append(f'stderr="{output.stderr_content}"')
                    if output.status != 0:
                        output_footnote_attrs.append(f'status={output.status}')
                    if output.duration > 0:
                        output_footnote_attrs.append(f'duration={output.duration}')
                    if output.lang != "python":
                        output_footnote_attrs.append(f'lang="{output.lang}"')
                
                footnotes.append(f"[{output_footnote_id}]: [output] {' '.join(output_footnote_attrs)}")
        
        # Add footnotes at the end
        if footnotes:
            lines.append("")
            lines.append("<!-- Footnotes -->")
            for footnote in footnotes:
                lines.append(footnote)
        
        return "\n".join(lines)


# Factory functions and utility methods
def create_message_file(path: str, vfs: VFS) -> MarkdownMessageFile:
    """Create a message file.
    
    Args:
        path: The path to the message file
        vfs: The virtual file system to use
        
    Returns:
        The created message file
    """
    return MarkdownMessageFile(path, vfs)


def is_message_file(path: str, vfs: Optional[VFS] = None) -> bool:
    """Check if a file is a message file.
    
    According to REQ010, a file is a message file if:
    1. It has a .msg.md extension, or
    2. It has a .md extension and contains a message section (default name "Discussion",
       but can be customized in frontmatter)
    
    Args:
        path: The path to the file
        vfs: Optional virtual file system to use for reading the file
        
    Returns:
        True if the file is a message file, False otherwise
    """
    # Check file extension
    if path.endswith(".msg.md"):
        return True
    
    # Check if it's a markdown file
    if not path.endswith(".md"):
        return False
    
    # Try to read the file
    try:
        # Read file content using VFS if provided, otherwise use direct file access
        content = ""
        if vfs is not None:
            if not vfs.exists(path):
                return False
            with vfs.open(path, "r") as f:
                content = f.read().decode("utf-8")
        else:
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
        
        # Parse frontmatter to check for custom message section name
        parsed = frontmatter.loads(content)
        message_section_name = parsed.metadata.get("message_section", "Discussion")
        
        # Parse the markdown to find the message section
        root = parse_markdown(parsed.content)
        for section in root.sections:
            if section.heading and section.heading.text.strip() == message_section_name:
                return True
                
        # Also check for percent notation sections which indicate a message file
        for line in content.splitlines():
            if PERCENT_PATTERN.match(line.strip()):
                return True
                               
    except Exception as e:
        logger.warning(f"Error checking if {path} is a message file: {e}")
    
    return False


def convert_to_message_file(path: str, vfs: VFS, section_name: Optional[str] = None) -> bool:
    """Convert a regular markdown file to a message file by adding a message section.
    This function assumes the file does not already have a message section.
    
    Args:
        path: The path to the file
        vfs: The virtual file system to use
        section_name: Optional custom name for the message section (default: "Discussion")
        
    Returns:
        True if the conversion was successful, False on error
    """
    if not path.endswith(".md"):
        logger.error(f"Cannot convert non-markdown file to message file: {path}")
        return False
    
    try:
        # Use the default section name if not specified
        section_name = section_name or "Discussion"
        
        # Check if the file exists
        if not vfs.exists(path):
            logger.error(f"File does not exist: {path}")
            return False
        
        # Read the file content
        content = ""
        with vfs.open(path, "r") as f:
            content = f.read().decode("utf-8")
        
        # Parse frontmatter
        parsed = frontmatter.loads(content)
        metadata = dict(parsed.metadata)
        content_without_frontmatter = parsed.content
        
        # Add the message section configuration to frontmatter
        metadata["message_section"] = section_name
        
        # Prepare the content with the new message section
        lines = content_without_frontmatter.splitlines()
        
        # Add newlines if needed
        if lines and lines[-1].strip():
            lines.append("")
            lines.append("")
        elif not lines:
            # Empty file
            lines = [""]
        
        # Add the message section heading
        lines.append(f"# {section_name}")
        lines.append("")
        
        # Create the new content with updated frontmatter and the message section
        new_content = frontmatter.dumps(frontmatter.Post("\n".join(lines), **metadata))
        
        # Write the updated content back to the file
        with vfs.open(path, "w") as f:
            f.write(new_content.encode("utf-8"))
        
        return True
        
    except Exception as e:
        logger.error(f"Error converting {path} to message file: {e}")
        return False

def create_message_output(content: str, mime_type: str = "text/plain", 
                         nonce: Optional[str] = None) -> MessageOutput:
    """Create a message output.
    
    Args:
        content: The content of the output
        mime_type: The MIME type of the content (default: text/plain)
        nonce: Optional unique identifier for the output
        
    Returns:
        The created message output
    """
    return BaseMessageOutput(content, mime_type, nonce)


def create_code_execution_output(stdout: str = "", stderr: str = "", status: int = 0,
                               duration: float = 0.0, lang: str = "python",
                               mime_type: str = "text/plain", nonce: Optional[str] = None) -> CodeExecutionOutput:
    """Create a code execution output.
    
    Args:
        stdout: The standard output content
        stderr: The standard error content
        status: The execution status code
        duration: The execution duration in seconds
        lang: The programming language of the executed code
        mime_type: The MIME type of the content
        nonce: Optional unique identifier for the output
        
    Returns:
        The created code execution output
    """
    return BaseCodeExecutionOutput(stdout, stderr, status, duration, lang, mime_type, nonce)
