"""Message command implementation for working with message files."""

import click
import json
from pathlib import Path
from typing import Optional, Dict, Any, List, Union

from textcase.protocol.message import Message, MessageOutput, MessageItem, FunctionCall
from textcase.core.llm.message_file import MessageFileFactory
from textcase.cli.utils import debug_echo, parse_document_id


@click.group(name="message")
@click.pass_context
def message_cmd(ctx):
    """
    Work with message files.
    
    Message files are used to record conversation history with LLMs.
    """
    pass


@message_cmd.command(name="create")
@click.argument('module_id', type=str)
@click.option('--agent', '-a', help='Agent name to use for the message file')
@click.pass_context
def create_message(ctx, module_id: str, agent: Optional[str] = None):
    """
    Create a new message file.
    
    MODULE_ID is the ID of the module item to create (e.g., CHAT001).
    """
    # Get the project from context
    project = ctx.obj['project']
    if not project:
        click.echo("Error: No valid project found.", err=True)
        ctx.exit(1)
    
    # Parse the module ID to get the module prefix and item ID
    module_prefix, item_id, _, _ = parse_document_id(module_id, project, ctx)
    
    if not module_prefix or not item_id:
        click.echo(f"Error: Invalid module ID: {module_id}", err=True)
        ctx.exit(1)
    
    try:
        # Create the message file
        message_file = MessageFileFactory.get_message_file(project, module_prefix, item_id)
        
        # Add agent if specified
        if agent:
            # Check if agent exists
            agent_dir = project.path / '.config' / 'agent'
            agent_path = agent_dir / f"{agent}.md"
            
            if not project._vfs.exists(agent_path):
                click.echo(f"Warning: Agent '{agent}' not found, using default agent", err=True)
            else:
                # Add agent to the message file
                agent_config = {
                    "name": agent,
                    "type": "named"
                }
                message_file.agents.append(agent_config)
                message_file.save()
        
        click.echo(f"Created message file: {message_file.get_path()}")
    except Exception as e:
        click.echo(f"Error creating message file: {e}", err=True)
        ctx.exit(1)


@message_cmd.command(name="add-message")
@click.argument('module_id', type=str)
@click.argument('content', type=str)
@click.option('--name', '-n', help='Name for the message')
@click.option('--mime-type', '-m', default="text/plain", help='MIME type of the content')
@click.option('--agent', '-a', help='Agent name to use for the message')
@click.option('--timeout', '-t', type=int, help='Timeout in seconds')
@click.pass_context
def add_message(ctx, module_id: str, content: str, name: Optional[str] = None, 
                mime_type: str = "text/plain", agent: Optional[str] = None, timeout: Optional[int] = None):
    """
    Add a message to a message file.
    
    MODULE_ID is the ID of the module item (e.g., CHAT001).
    CONTENT is the text content of the message.
    """
    # Get the project from context
    project = ctx.obj['project']
    if not project:
        click.echo("Error: No valid project found.", err=True)
        ctx.exit(1)
    
    # Parse the module ID to get the module prefix and item ID
    module_prefix, item_id, _, _ = parse_document_id(module_id, project, ctx)
    
    if not module_prefix or not item_id:
        click.echo(f"Error: Invalid module ID: {module_id}", err=True)
        ctx.exit(1)
    
    try:
        # Get the message file
        message_file = MessageFileFactory.get_message_file(project, module_prefix, item_id)
        
        # Add the message
        message = message_file.add_message(content, name, mime_type, agent, timeout)
        
        click.echo(f"Added message: {message.name}")
    except Exception as e:
        click.echo(f"Error adding message: {e}", err=True)
        ctx.exit(1)


@message_cmd.command(name="add-function-call")
@click.argument('module_id', type=str)
@click.argument('function_name', type=str)
@click.option('--args', '-a', type=str, help='Arguments for the function as JSON string')
@click.option('--name', '-n', help='Name for the function call')
@click.option('--timeout', '-t', type=int, help='Timeout in seconds')
@click.pass_context
def add_function_call(ctx, module_id: str, function_name: str, 
                     args: Optional[str] = None, name: Optional[str] = None, timeout: Optional[int] = None):
    """
    Add a function call to a message file.
    
    MODULE_ID is the ID of the module item (e.g., CHAT001).
    FUNCTION_NAME is the name of the function to call.
    """
    # Get the project from context
    project = ctx.obj['project']
    if not project:
        click.echo("Error: No valid project found.", err=True)
        ctx.exit(1)
    
    # Parse the module ID to get the module prefix and item ID
    module_prefix, item_id, _, _ = parse_document_id(module_id, project, ctx)
    
    if not module_prefix or not item_id:
        click.echo(f"Error: Invalid module ID: {module_id}", err=True)
        ctx.exit(1)
    
    # Parse args if provided
    args_dict = None
    if args:
        try:
            args_dict = json.loads(args)
        except json.JSONDecodeError:
            click.echo(f"Error: Invalid JSON for args: {args}", err=True)
            ctx.exit(1)
    
    try:
        # Get the message file
        message_file = MessageFileFactory.get_message_file(project, module_prefix, item_id)
        
        # Add the function call
        function_call = message_file.add_function_call(function_name, args_dict, name, timeout)
        
        click.echo(f"Added function call: {function_call.name}")
    except Exception as e:
        click.echo(f"Error adding function call: {e}", err=True)
        ctx.exit(1)


@message_cmd.command(name="list")
@click.argument('module_id', type=str)
@click.pass_context
def list_messages(ctx, module_id: str):
    """
    List all items in a message file.
    
    MODULE_ID is the ID of the module item (e.g., CHAT001).
    """
    # Get the project from context
    project = ctx.obj['project']
    if not project:
        click.echo("Error: No valid project found.", err=True)
        ctx.exit(1)
    
    # Parse the module ID to get the module prefix and item ID
    module_prefix, item_id, _, _ = parse_document_id(module_id, project, ctx)
    
    if not module_prefix or not item_id:
        click.echo(f"Error: Invalid module ID: {module_id}", err=True)
        ctx.exit(1)
    
    try:
        # Get the message file
        message_file = MessageFileFactory.get_message_file(project, module_prefix, item_id)
        
        # Get all items
        items = message_file.get_items()
        
        if not items:
            click.echo(f"No items found in {module_id}")
            return
        
        # Display items
        click.echo(f"Items in {module_id}:")
        for i, item in enumerate(items):
            name = item.name or f"item_{i+1}"
            item_type = item.type if hasattr(item, 'type') else "unknown"
            
            if isinstance(item, Message):
                agent = f" (agent: {item.agent_name})" if item.agent_name else ""
                mime_type = f" ({item.mime_type})" if hasattr(item, 'mime_type') else ""
                content_preview = item.content[:50] + "..." if len(item.content) > 50 else item.content
                click.echo(f"  - {name}{agent}{mime_type} [{item_type}]: {content_preview}")
            elif isinstance(item, FunctionCall):
                args_preview = str(item.args)[:50] + "..." if len(str(item.args)) > 50 else str(item.args)
                click.echo(f"  - {name} [{item_type}]: {item.function_name}({args_preview})")
            else:
                click.echo(f"  - {name} [unknown type]")
            
            # Display outputs
            if item.outputs:
                click.echo(f"    Outputs:")
                for output in item.outputs:
                    output_preview = output.content[:30] + "..." if len(output.content) > 30 else output.content
                    click.echo(f"      - {output_preview} ({output.mime_type})")
    except Exception as e:
        click.echo(f"Error listing items: {e}", err=True)
        ctx.exit(1)


@message_cmd.command(name="list-agents")
@click.argument('module_id', type=str)
@click.pass_context
def list_agents(ctx, module_id: str):
    """
    List all agents in a message file.
    
    MODULE_ID is the ID of the module item (e.g., CHAT001).
    """
    # Get the project from context
    project = ctx.obj['project']
    if not project:
        click.echo("Error: No valid project found.", err=True)
        ctx.exit(1)
    
    # Parse the module ID to get the module prefix and item ID
    module_prefix, item_id, _, _ = parse_document_id(module_id, project, ctx)
    
    if not module_prefix or not item_id:
        click.echo(f"Error: Invalid module ID: {module_id}", err=True)
        ctx.exit(1)
    
    try:
        # Get the message file
        message_file = MessageFileFactory.get_message_file(project, module_prefix, item_id)
        
        # Get all agents
        agents = message_file.get_agents()
        
        if not agents:
            click.echo(f"No agents found in {module_id}")
            return
        
        # Display agents
        click.echo(f"Agents in {module_id}:")
        for agent in agents:
            agent_name = agent.get("name", "unnamed")
            agent_type = agent.get("type", "unknown")
            click.echo(f"  - {agent_name} (type: {agent_type})")
    except Exception as e:
        click.echo(f"Error listing agents: {e}", err=True)
        ctx.exit(1)
