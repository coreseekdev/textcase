"""
Ask command implementation for testing LLM inference capabilities.
"""
import asyncio
import click
import logging
import sys
import time
from pathlib import Path
from typing import Optional

from textcase.core.llm import LLMFactory
from textcase.core.llm.agent import AgentFactory
from textcase.core.logging import setup_logging, get_logger

# Get logger for this module
logger = get_logger(__name__)


@click.command()
@click.argument('model_or_provider', type=str)
@click.argument('prompt', type=str)
@click.option('--stream/--no-stream', default=True, help='Stream the response or wait for complete response')
@click.option('--temperature', type=float, default=0.7, help='Temperature for response generation (0.0-1.0)')
@click.option('--max-tokens', type=int, help='Maximum tokens to generate')
@click.pass_context
def ask(ctx, model_or_provider: str, prompt: str, stream: bool = True, temperature: float = 0.7,
        max_tokens: Optional[int] = None):
    """
    Test LLM inference capabilities.
    
    MODEL_OR_PROVIDER can be:
      - A model name (e.g., gpt-4o-mini): Uses the first provider that supports this model
      - A provider:model pair (e.g., openai:gpt-4o-mini): Uses the specified provider and model
      - An agent name: Uses the agent's model selection logic
    
    PROMPT is the text to send to the LLM.
    
    Examples:
      ask gpt-4o-mini "What is the capital of France?"
      ask xty:gpt-4o-mini "Explain quantum computing in simple terms"
    """
    # Setup logging based on verbosity from context
    verbose = ctx.obj.get('verbose', False) if ctx.obj else False
    setup_logging(verbose)
    logger.info(f"Starting ask command with model/provider: {model_or_provider}")
    logger.debug(f"Stream: {stream}, Temperature: {temperature}, Max tokens: {max_tokens}, Verbose: {verbose}")
    
    # Record start time for performance tracking
    start_time = time.time()
    
    # 获取项目对象
    project = ctx.obj.get('project')
    if not project:
        logger.error("No active project found in context")
        click.echo("Error: No active project found.", err=True)
        ctx.exit(1)
        
    # Parse model_or_provider
    if ':' in model_or_provider:
        # Format: provider:model
        provider_name, model_name = model_or_provider.split(':', 1)
        logger.info(f"Parsed provider:model format: provider={provider_name}, model={model_name}")
        is_agent = False
    else:
        # Check if this is an agent name or a model name
        agent_dir = project.path / '.config' / 'agent'
        agent_path = agent_dir / f"{model_or_provider}.md"
        
        if agent_path.exists():
            # This is an agent name
            agent_name = model_or_provider
            logger.info(f"Detected agent name: {agent_name}")
            is_agent = True
        else:
            # This is a model name (find first provider that supports it)
            model_name = model_or_provider
            provider_name = None
            logger.info(f"Using model name only: {model_name}, will search for provider")
            is_agent = False
        
    # 获取提供商配置目录
    config_dir = project.path / '.config' / 'provider'
    logger.debug(f"Looking for provider configs in: {config_dir}")
    
    if not config_dir.exists():
        logger.error(f"Provider configuration directory not found: {config_dir}")
        click.echo(f"Error: Provider configuration directory not found: {config_dir}", err=True)
        ctx.exit(1)
    
    try:
        # Prepare kwargs
        kwargs = {}
        if temperature is not None:
            kwargs['temperature'] = temperature
        if max_tokens is not None:
            kwargs['max_tokens'] = max_tokens
            
        # Create agent (either named agent or default agent with model)
        if 'is_agent' in locals() and is_agent:
            # Use named agent
            logger.info(f"Using agent: {agent_name}")
            click.echo(f"Using agent: {agent_name}")
            agent = AgentFactory.get_agent(project, agent_name)
        else:
            # Use default agent with model
            logger.info(f"Using model: {model_name}, provider: {provider_name or 'auto'}")
            click.echo(f"Using model: {model_name}, provider: {provider_name or 'auto'}")
            agent = AgentFactory.get_agent(project, None, model_name, provider_name)
            
            # Add provider and model to kwargs if specified
            if provider_name:
                kwargs['provider'] = provider_name
            kwargs['model'] = model_name
        
        # Stream or generate full response
        if stream:
            logger.info("Using streaming mode")
            asyncio.run(stream_agent_response(agent, prompt, **kwargs))
        else:
            # Generate full response
            logger.info("Using non-streaming mode")
            response = asyncio.run(agent.generate(prompt, **kwargs))
            click.echo(response.content)
            
            # Log usage if available
            if response.usage:
                logger.info(f"Usage: {response.usage}")
                
            logger.debug(f"Inference parameters: {kwargs}")
            
            if stream:
                logger.info("Using streaming mode")
                asyncio.run(stream_response(provider, prompt, model_name, **kwargs))
            else:
                logger.info("Using non-streaming mode")
                response = asyncio.run(provider.generate(prompt, model_name, **kwargs))
                click.echo(response.content)
                
                # Print usage statistics if available
                if response.usage:
                    logger.debug(f"Usage statistics: {response.usage}")
                    click.echo("\nUsage statistics:")
                    for key, value in response.usage.items():
                        click.echo(f"  {key}: {value}")
    
    except Exception as e:
        logger.exception(f"Error during LLM inference: {str(e)}")
        click.echo(f"Error: {e}", err=True)
        ctx.exit(1)
        
    # Log completion time
    end_time = time.time()
    duration = end_time - start_time
    logger.info(f"Ask command completed in {duration:.2f} seconds")


async def stream_content(generator, source_info, **kwargs):
    """
    Stream content from any async generator (agent or provider).
    
    Args:
        generator: AsyncGenerator yielding content chunks
        source_info: String identifying the source (e.g., 'agent:demo' or 'model:gpt-4o')
        **kwargs: Additional parameters for logging
    """
    request_id = f"stream-{source_info}-{str(id(generator))[:8]}"
    logger.info(f"[{request_id}] Starting streaming response from: {source_info}")
    
    # Log parameters
    temperature = kwargs.get('temperature', 0.7)
    max_tokens = kwargs.get('max_tokens', None)
    logger.debug(f"[{request_id}] Parameters: temperature={temperature}, max_tokens={max_tokens}")
    
    # Track metrics
    start_time = time.time()
    chunk_count = 0
    total_chars = 0
    accumulated_text = ""
    
    try:
        # Stream the response chunk by chunk
        logger.info(f"[{request_id}] Starting stream")
        
        async for chunk in generator:
            chunk_count += 1
            chunk_length = len(chunk) if chunk else 0
            total_chars += chunk_length
            
            # Log chunk details periodically to avoid excessive logging
            if chunk_count == 1 or chunk_count % 10 == 0 or chunk_length == 0:
                logger.debug(f"[{request_id}] Received chunk #{chunk_count}, length: {chunk_length} chars")
                if chunk_length == 0:
                    logger.warning(f"[{request_id}] Empty chunk received")
            
            # Print only the new chunk, not the full response each time
            if chunk:
                # Use print with flush=True instead of click.echo to ensure immediate display
                print(chunk, end='', flush=True)
                accumulated_text += chunk
                
                # Log the content being displayed for debugging
                logger.debug(f"[{request_id}] Displayed content: '{chunk}'")
                
                # Double ensure flush
                sys.stdout.flush()
            
        # Log completion statistics
        end_time = time.time()
        duration = end_time - start_time
        logger.info(f"[{request_id}] Streaming completed in {duration:.2f}s")
        logger.info(f"[{request_id}] Received {chunk_count} chunks, total {total_chars} chars")
        
        # Add final newline after streaming is complete
        print("\n", flush=True)  # Use print with flush instead of click.echo
        
    except Exception as e:
        # Log the error
        end_time = time.time()
        duration = end_time - start_time
        logger.exception(f"[{request_id}] Error during streaming after {duration:.2f}s: {str(e)}")
        logger.error(f"[{request_id}] Chunks received before error: {chunk_count}")
        
        # Show error to user
        click.echo(f"\nError: {e}", err=True)
        
        # If we have partial content, log it for debugging
        if accumulated_text:
            truncated = accumulated_text[:100] + "..." if len(accumulated_text) > 100 else accumulated_text
            logger.debug(f"[{request_id}] Partial content received before error: '{truncated}'")
            logger.debug(f"[{request_id}] Partial content length: {len(accumulated_text)} chars")


async def stream_agent_response(agent, prompt, **kwargs):
    """Stream the response from an agent."""
    source_info = f"agent:{agent.agent_name}"
    generator = agent.generate_stream(prompt, **kwargs)
    await stream_content(generator, source_info, **kwargs)


async def stream_response(provider, prompt, model, **kwargs):
    """Stream the response from the LLM."""
    source_info = f"model:{model}"
    generator = provider.generate_stream(prompt, model, **kwargs)
    await stream_content(generator, source_info, **kwargs)
