"""
Ask command implementation for testing LLM inference capabilities.
"""
import asyncio
import click
from pathlib import Path
from typing import Optional

from textcase.core.llm import LLMFactory


@click.command()
@click.argument('model_or_provider', type=str)
@click.argument('prompt', type=str)
@click.option('--stream/--no-stream', default=True, help='Stream the response or wait for complete response')
@click.option('--temperature', type=float, default=0.7, help='Temperature for response generation (0.0-1.0)')
@click.pass_context
def ask(ctx, model_or_provider: str, prompt: str, stream: bool = True, temperature: float = 0.7):
    """
    Test LLM inference capabilities.
    
    MODEL_OR_PROVIDER can be:
      - A model name (e.g., gpt-4o-mini): Uses the first provider that supports this model
      - A provider:model pair (e.g., openai:gpt-4o-mini): Uses the specified provider and model
      - An agent name (future feature): Uses the agent's model selection logic
    
    PROMPT is the text to send to the LLM.
    
    Examples:
      ask gpt-4o-mini "What is the capital of France?"
      ask xty:gpt-4o-mini "Explain quantum computing in simple terms"
    """
    # Parse model_or_provider
    if ':' in model_or_provider:
        # Format: provider:model
        provider_name, model_name = model_or_provider.split(':', 1)
    else:
        # Format: model (find first provider that supports it)
        model_name = model_or_provider
        provider_name = None
    
    # 获取项目对象
    project = ctx.obj.get('project')
    if not project:
        click.echo("Error: No active project found.", err=True)
        ctx.exit(1)
        
    # 获取提供商配置目录
    config_dir = project.path / '.config' / 'provider'
    if not config_dir.exists():
        click.echo(f"Error: Provider configuration directory not found: {config_dir}", err=True)
        ctx.exit(1)
    
    try:
        if provider_name:
            # Use specified provider
            config_path = config_dir / f"{provider_name}.yml"
            if not config_path.exists():
                click.echo(f"Error: Provider configuration not found: {config_path}", err=True)
                ctx.exit(1)
            
            provider = LLMFactory.get_provider(provider_name, config_path)
            
            # Run the LLM inference
            if stream:
                asyncio.run(stream_response(provider, prompt, model_name, temperature))
            else:
                response = asyncio.run(provider.generate(prompt, model_name, temperature=temperature))
                click.echo(response.content)
                
                # Print usage statistics if available
                if response.usage:
                    click.echo("\nUsage statistics:")
                    for key, value in response.usage.items():
                        click.echo(f"  {key}: {value}")
        else:
            # Find provider that supports the model
            providers = LLMFactory.get_model_providers(config_dir, model_name)
            
            if not providers:
                click.echo(f"Error: No provider found for model: {model_name}", err=True)
                ctx.exit(1)
            
            # Use the first provider that supports the model
            provider_name = next(iter(providers.keys()))
            provider = providers[provider_name]
            
            click.echo(f"Using provider: {provider_name}")
            
            # Run the LLM inference
            if stream:
                asyncio.run(stream_response(provider, prompt, model_name, temperature))
            else:
                response = asyncio.run(provider.generate(prompt, model_name, temperature=temperature))
                click.echo(response.content)
                
                # Print usage statistics if available
                if response.usage:
                    click.echo("\nUsage statistics:")
                    for key, value in response.usage.items():
                        click.echo(f"  {key}: {value}")
    
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        ctx.exit(1)


async def stream_response(provider, prompt, model, temperature):
    """Stream the response from the LLM."""
    try:
        # Stream the response chunk by chunk
        accumulated_text = ""
        
        async for chunk in provider.generate_stream(prompt, model, temperature=temperature):
            # Print only the new chunk, not the full response each time
            click.echo(chunk, nl=False)
            accumulated_text += chunk
            
        click.echo()  # Final newline after streaming is complete
    except Exception as e:
        click.echo(f"\nError: {e}", err=True)
