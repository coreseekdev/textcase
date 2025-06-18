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
"""Ask command for LLM interactions.

This module provides the ask command that allows users to interact with
LLM models through various providers and agents.
"""

import asyncio
import sys
from typing import Optional, Tuple
import click

from ...textcase import TextCase
from ...llm import LLMFactory, AgentFactory



def _parse_model_or_agent(model_or_agent: str) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    """Parse model or agent specification.
    
    Args:
        model_or_agent: Model/agent specification in format:
                       - 'provider:model' (e.g., 'openai:gpt-4')
                       - 'model' (e.g., 'gpt-4')
                       - 'agent_name' (e.g., 'default')
    
    Returns:
        Tuple of (provider, model, agent_name)
    """
    if ':' in model_or_agent:
        # Format: provider:model
        parts = model_or_agent.split(':', 1)
        return parts[0], parts[1], None
    else:
        # Could be either a model name or agent name
        # We'll let the factory determine this
        return None, model_or_agent, model_or_agent


async def _generate_response(
    agent_factory: AgentFactory,
    prompt: str,
    provider: Optional[str],
    model: Optional[str],
    agent_name: Optional[str],
    stream: bool,
    temperature: Optional[float],
    max_tokens: Optional[int]
) -> None:
    """Generate and display LLM response.
    
    Args:
        agent_factory: Agent factory instance
        prompt: User prompt
        provider: Provider name (optional)
        model: Model name (optional)
        agent_name: Agent name (optional)
        stream: Whether to use streaming
        temperature: Temperature setting
        max_tokens: Maximum tokens
    """
    # Prepare kwargs
    kwargs = {}
    if temperature is not None:
        kwargs['temperature'] = temperature
    if max_tokens is not None:
        kwargs['max_tokens'] = max_tokens

    # Try to create agent by name first
    agent = None
    if agent_name and agent_factory.agent_exists(agent_name):
        click.echo(f"Using agent: {agent_name}", err=True)
        agent = agent_factory.create_agent(agent_name, **kwargs)
    elif model:
        # Create agent with specific model
        click.echo(f"Using model: {model}", err=True)
        if provider:
            click.echo(f"Using provider: {provider}", err=True)
        agent = agent_factory.create_agent_with_model(model, provider, **kwargs)
    else:
        raise click.ClickException("Must specify either a valid agent name or model")

    if stream:
        # Streaming response
        click.echo(f"Streaming response from {agent.model}...", err=True)
        click.echo("", err=True)  # Empty line

        async for chunk in agent.generate_stream(prompt, **kwargs):
            click.echo(chunk, nl=False)

        click.echo("")  # Final newline
    else:
        # Non-streaming response
        click.echo(f"Generating response from {agent.model}...", err=True)
        click.echo("", err=True)  # Empty line

        response = await agent.generate(prompt, **kwargs)
        click.echo(response.content)

        # Show metadata if available
        if response.metadata:
            click.echo("", err=True)
            click.echo(f"Model: {response.model}", err=True)
            click.echo(f"Provider: {response.provider}", err=True)

            # Show token usage if available
            if 'usage' in response.metadata:
                usage = response.metadata['usage']
                if isinstance(usage, dict):
                    for key, value in usage.items():
                        click.echo(f"{key}: {value}", err=True)



@click.command()
@click.argument('prompt', required=True)
@click.option(
    '-m', '--model',
    help='Model or agent to use. Format: [provider:]model or agent_name'
)
@click.option(
    '-s', '--stream',
    is_flag=True,
    help='Enable streaming output'
)
@click.option(
    '-t', '--temperature',
    type=float,
    help='Temperature for response generation (0.0-2.0)'
)
@click.option(
    '--max-tokens',
    type=int,
    help='Maximum number of tokens to generate'
)
@click.pass_context
def ask(ctx, prompt: str, model: Optional[str], stream: bool, temperature: Optional[float], max_tokens: Optional[int]):
    """Ask a question to an LLM model or agent.
    
    This command allows you to interact with various LLM models through different providers
    or use pre-configured agents.
    
    Examples:
    
        # Use a specific model with provider
        textcase ask "What is Python?" -m openai:gpt-4
        
        # Use a model (auto-detect provider)
        textcase ask "What is Python?" -m gpt-4
        
        # Use a named agent
        textcase ask "What is Python?" -m default
        
        # Use streaming output
        textcase ask "Write a story" -m gpt-4 --stream
        
        # Set temperature and max tokens
        textcase ask "Be creative" -m gpt-4 -t 1.2 --max-tokens 500
    """
    # Get TextCase instance from context
    textcase: TextCase = ctx.obj['textcase']
    
    # Validate temperature
    if temperature is not None and (temperature < 0.0 or temperature > 2.0):
        raise click.BadParameter("Temperature must be between 0.0 and 2.0")
    
    # Validate max_tokens
    if max_tokens is not None and max_tokens <= 0:
        raise click.BadParameter("Max tokens must be positive")
    
    # Use default model if not specified
    if not model:
        model = 'default'  # Try default agent first
    
    # Parse model or agent specification
    provider, parsed_model, agent_name = _parse_model_or_agent(model)
    
    try:
        # Start services if not already started
        textcase.start_services()
        
        # Create LLM factory
        llm_factory = LLMFactory(textcase.resource_manager)
        
        # Create agent factory
        agent_factory = AgentFactory(llm_factory, textcase)
        
        # Generate response
        asyncio.run(_generate_response(
            agent_factory=agent_factory,
            prompt=prompt,
            provider=provider,
            model=parsed_model,
            agent_name=agent_name,
            stream=stream,
            temperature=temperature,
            max_tokens=max_tokens
        ))
        
    except KeyboardInterrupt:
        click.echo("\nInterrupted by user", err=True)
        sys.exit(1)
    except Exception as e:
        raise click.ClickException(str(e))
    finally:
        # Stop services
        try:
            textcase.stop_services()
        except Exception:
            pass  # Ignore cleanup errors