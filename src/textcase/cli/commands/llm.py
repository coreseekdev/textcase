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
"""LLM management command.

This module provides the llm command for managing and inspecting
LLM-related resources including providers, models, and agents.
"""

import click
import yaml
from pathlib import Path
from typing import Dict, List, Any, Optional

from ...textcase import TextCase
from ...core.llm.factory import LLMFactory
from ...core.llm.agent import AgentFactory
from ...collection.config_collection import ConfigItemImpl


def _load_yaml_config(file_path: Path) -> Optional[Dict[str, Any]]:
    """Load YAML configuration from file.
    
    Args:
        file_path: Path to YAML file
        
    Returns:
        Parsed YAML content or None if file doesn't exist or is invalid
    """
    try:
        if file_path.exists():
            with open(file_path, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f)
    except Exception:
        pass
    return None


def _load_markdown_config(file_path: Path) -> Optional[Dict[str, Any]]:
    """Load markdown configuration with frontmatter.
    
    Args:
        file_path: Path to markdown file
        
    Returns:
        Parsed frontmatter content or None if file doesn't exist or is invalid
    """
    try:
        if file_path.exists():
            import frontmatter
            with open(file_path, 'r', encoding='utf-8') as f:
                post = frontmatter.load(f)
                return post.metadata
    except Exception:
        pass
    return None


def _get_provider_configs(textcase: TextCase, check_availability: bool = False) -> Dict[str, Dict[str, Any]]:
    """Get all provider configurations.
    
    Args:
        textcase: TextCase instance
        check_availability: Whether to check provider availability
        
    Returns:
        Dictionary mapping provider names to their configurations.
        If check_availability is True, adds '_availability' key with availability info.
    """
    providers = {}
    
    # Get provider config directory by accessing config collection
    # This will trigger initialization of _config_collection_manager if needed
    provider_collections = textcase.resource_manager.get_collection('config.provider')
    if not provider_collections:
        return providers
    
    for collection_name in provider_collections.item_names():
        try:
            provider = provider_collections.get_item(collection_name)
            if isinstance(provider, ConfigItemImpl):
                # 使用 ConfigItemImpl 接口读取文档数据
                config_data = provider.data
                if config_data:
                    providers[collection_name] = config_data.copy()
                    
                    # Check availability if requested
                    if check_availability:
                        is_available, score, error_msg = provider.check_availability()
                        providers[collection_name]['_availability'] = {
                            'available': is_available,
                            'score': score,
                            'error': error_msg
                        }
            else:
                # 兼容旧的文件系统读取方式
                provider_dir = Path(textcase.repo_root_path) / 'src' / 'data' / 'config' / 'provider' / collection_name
                
                # Look for YAML config files
                for config_file in provider_dir.glob('*.yml'):
                    if config_file.stem != 'default':
                        config = _load_yaml_config(config_file)
                        if config:
                            providers[config_file.stem] = config
                            # For file-based configs, assume available (no template variables)
                            if check_availability:
                                providers[config_file.stem]['_availability'] = {
                                    'available': True,
                                    'score': 1.0,
                                    'error': None
                                }
                            
                # Also check for .yaml files
                for config_file in provider_dir.glob('*.yaml'):
                    if config_file.stem != 'default':
                        config = _load_yaml_config(config_file)
                        if config:
                            providers[config_file.stem] = config
                            # For file-based configs, assume available (no template variables)
                            if check_availability:
                                providers[config_file.stem]['_availability'] = {
                                    'available': True,
                                    'score': 1.0,
                                    'error': None
                                }
        except Exception:
            continue
            
    return providers


def _get_agent_configs(textcase: TextCase) -> Dict[str, Dict[str, Any]]:
    """Get all agent configurations.
    
    Args:
        textcase: TextCase instance
        
    Returns:
        Dictionary mapping agent names to their configurations
    """
    agents = {}
    
    # Get agent config directory by accessing config collection
    # This will trigger initialization of _config_collection_manager if needed
    agent_collections = textcase.resource_manager.get_collection('config.agent')
    if not agent_collections:
        return agents
    
    for collection_name in agent_collections.item_names():
        try:
            agent = agent_collections.get_item(collection_name)
            if isinstance(agent, ConfigItemImpl):
                # 使用 ConfigItemImpl 接口读取文档数据
                config_data = agent.data
                if config_data:
                    agents[collection_name] = config_data
            else:
                # 兼容旧的文件系统读取方式
                agent_dir = Path(textcase.repo_root_path) / 'src' / 'data' / 'config' / 'agent' / collection_name
                
                # Look for markdown config files
                for config_file in agent_dir.glob('*.md'):
                    if config_file.stem != 'default':
                        config = _load_markdown_config(config_file)
                        if config:
                            # Also read the content for prompt preview
                            try:
                                import frontmatter
                                with open(config_file, 'r', encoding='utf-8') as f:
                                    post = frontmatter.load(f)
                                    config['prompt_preview'] = post.content[:200] + '...' if len(post.content) > 200 else post.content
                            except Exception:
                                config['prompt_preview'] = 'Unable to read prompt'
                            
                            agents[config_file.stem] = config
        except Exception:
            continue
            
    return agents


def _get_available_models(textcase, provider_filter=None, include_unavailable=False):
    """Get all available models from provider configurations.
    
    Args:
        textcase: Textcase instance
        provider_filter: Optional provider name to filter by
        include_unavailable: Whether to include models from unavailable providers
        
    Returns:
        List of model info dictionaries with provider and availability info
    """
    # Get provider configs with availability check if needed
    check_availability = not include_unavailable
    provider_configs = _get_provider_configs(textcase, check_availability=check_availability)
    
    models = []
    
    for provider_name, config in provider_configs.items():
        # Skip if filtering by provider and this isn't the one
        if provider_filter and provider_name != provider_filter:
            continue
            
        # Check provider availability
        availability_info = config.get('_availability')
        if not include_unavailable and availability_info and not availability_info['available']:
            continue
            
        # Determine provider status for display
        provider_status = ""
        if availability_info:
            if availability_info['available']:
                provider_status = "✅"
            elif availability_info['score'] > 0:
                provider_status = "⚠️"
            else:
                provider_status = "❌"
        
        model_list = []
        
        # Handle different model configuration formats
        if 'models' in config:
            if isinstance(config['models'], dict):
                for model_name, model_config in config['models'].items():
                    model_info = {
                        'name': model_name,
                        'provider': provider_name,
                        'provider_status': provider_status
                    }
                    if isinstance(model_config, dict) and 'description' in model_config:
                        model_info['description'] = model_config['description']
                    model_list.append(model_info)
            elif isinstance(config['models'], list):
                for model_name in config['models']:
                    model_list.append({
                        'name': model_name,
                        'provider': provider_name,
                        'provider_status': provider_status
                    })
        elif 'model' in config:
            if isinstance(config['model'], list):
                for model_name in config['model']:
                    model_list.append({
                        'name': model_name,
                        'provider': provider_name,
                        'provider_status': provider_status
                    })
            else:
                model_list.append({
                    'name': config['model'],
                    'provider': provider_name,
                    'provider_status': provider_status
                })
        
        models.extend(model_list)
    
    # Sort by provider name, then by model name
    models.sort(key=lambda x: (x['provider'], x['name']))
    
    return models


@click.group()
@click.pass_context
def llm(ctx):
    """Manage LLM providers, models, and agents.
    
    This command group provides tools to inspect and manage LLM-related
    resources in your TextCase project.
    """
    pass


@llm.command()
@click.option('--check-availability', '-c', is_flag=True, help='Check provider availability based on environment variables')
@click.pass_context
def providers(ctx, check_availability):
    """List all available LLM providers.
    
    Shows all configured LLM providers with their basic information.
    """
    textcase = ctx.obj['textcase']
    
    try:
        provider_configs = _get_provider_configs(textcase, check_availability=check_availability)
        
        if not provider_configs:
            click.echo("No providers configured.")
            click.echo("\nTo add a provider, create a configuration file in:")
            click.echo("  src/data/config/provider/<collection>/")
            return
        
        click.echo(f"Found {len(provider_configs)} provider(s):\n")
        
        for provider_name, config in provider_configs.items():
            # Get availability info if checked
            availability_info = config.get('_availability')
            
            # Choose icon based on availability
            if availability_info:
                if availability_info['available']:
                    icon = "✅"
                    status = "Available"
                elif availability_info['score'] > 0:
                    icon = "⚠️"
                    status = f"Partial ({availability_info['score']:.1%})"
                else:
                    icon = "❌"
                    status = "Unavailable"
            else:
                icon = "📡"
                status = None
            
            click.echo(f"{icon} {provider_name}")
            
            # Show availability status
            if status:
                click.echo(f"   Status: {status}")
                if not availability_info['available'] and availability_info['error']:
                    click.echo(f"   Error: {availability_info['error']}")
            
            # Show API base if available
            if 'api_base' in config:
                click.echo(f"   API Base: {config['api_base']}")
            
            # Show model count
            model_count = 0
            if 'models' in config:
                if isinstance(config['models'], dict):
                    model_count = len(config['models'])
                elif isinstance(config['models'], list):
                    model_count = len(config['models'])
            elif 'model' in config:
                if isinstance(config['model'], list):
                    model_count = len(config['model'])
                else:
                    model_count = 1
                    
            click.echo(f"   Models: {model_count}")
            click.echo()
            
    except Exception as e:
        raise click.ClickException(f"Error listing providers: {e}")


@llm.command()
@click.option('--provider', '-p', help='Filter models by provider')
@click.option('--include-unavailable', is_flag=True, help='Include models from unavailable providers')
@click.pass_context
def models(ctx, provider, include_unavailable):
    """List all available models.
    
    Shows all models from all providers, or filter by specific provider.
    By default, models from unavailable providers are hidden unless --include-unavailable is used.
    """
    textcase = ctx.obj['textcase']
    
    try:
        models = _get_available_models(textcase, provider_filter=provider, include_unavailable=include_unavailable)
        
        if not models:
            if provider:
                click.echo(f"No models found for provider '{provider}'.")
            else:
                click.echo("No models configured.")
            return
        
        if provider:
            click.echo(f"Models for provider '{provider}':\n")
        else:
            click.echo(f"Found {len(models)} model(s):\n")
        
        current_provider = None
        for model_info in models:
            # Group by provider
            if model_info['provider'] != current_provider:
                if current_provider is not None:
                    click.echo()
                current_provider = model_info['provider']
                if not provider:  # Only show provider header if not filtering
                    # Show provider status if available
                    provider_status = model_info.get('provider_status', '')
                    if provider_status:
                        click.echo(f"📡 {current_provider} {provider_status}:")
                    else:
                        click.echo(f"📡 {current_provider}:")
            
            # Show model info
            model_name = model_info['name']
            if provider:
                click.echo(f"  🤖 {model_name}")
            else:
                click.echo(f"  🤖 {model_name}")
            
            # Show additional info if available
            if 'description' in model_info:
                click.echo(f"     {model_info['description']}")
            
    except Exception as e:
        raise click.ClickException(f"Error listing models: {e}")


@llm.command()
@click.pass_context
def agents(ctx):
    """List all available agents.
    
    Shows all configured agents with their models and prompt previews.
    """
    textcase = ctx.obj['textcase']
    
    try:
        agent_configs = _get_agent_configs(textcase)
        
        if not agent_configs:
            click.echo("No agents configured.")
            click.echo("\nTo add an agent, create a configuration file in:")
            click.echo("  src/data/config/agent/<collection>/")
            return
        
        click.echo(f"Found {len(agent_configs)} agent(s):\n")
        
        for agent_name, config in agent_configs.items():
            is_default = agent_name == 'default'
            default_marker = " (default)" if is_default else ""
            
            click.echo(f"🤖 {agent_name}{default_marker}")
            
            # Show model
            if 'model' in config:
                click.echo(f"   Model: {config['model']}")
            
            # Show provider if specified
            if 'provider' in config:
                click.echo(f"   Provider: {config['provider']}")
            
            # Show temperature
            if 'temperature' in config:
                click.echo(f"   Temperature: {config['temperature']}")
            
            # Show max tokens
            if 'max_tokens' in config:
                click.echo(f"   Max Tokens: {config['max_tokens']}")
            elif 'max_output_tokens' in config:
                click.echo(f"   Max Output Tokens: {config['max_output_tokens']}")
            
            # Show prompt preview
            if 'prompt_preview' in config:
                preview = config['prompt_preview'].strip()
                if preview:
                    click.echo(f"   Prompt Preview: {preview}")
            
            click.echo()
            
    except Exception as e:
        raise click.ClickException(f"Error listing agents: {e}")


@llm.command()
@click.pass_context
def status(ctx):
    """Show LLM system status.
    
    Displays overall status of the LLM system including counts and default configurations.
    """
    textcase = ctx.obj['textcase']
    
    try:
        provider_configs = _get_provider_configs(textcase)
        agent_configs = _get_agent_configs(textcase)
        available_models = _get_available_models(textcase, include_unavailable=True)
        
        click.echo("🔍 LLM System Status\n")
        
        # Summary counts
        click.echo(f"Providers: {len(provider_configs)}")
        click.echo(f"Models: {len(available_models)}")
        click.echo(f"Agents: {len(agent_configs)}")
        click.echo()
        
        # Default configurations
        click.echo("📋 Default Configurations:")
        
        if 'default' in agent_configs:
            default_agent = agent_configs['default']
            click.echo(f"   Default Agent: default")
            if 'model' in default_agent:
                click.echo(f"   Default Model: {default_agent['model']}")
            if 'provider' in default_agent:
                click.echo(f"   Default Provider: {default_agent['provider']}")
        else:
            click.echo("   No default agent configured")
        
        click.echo()
        
        # Configuration paths
        click.echo("📁 Configuration Paths:")
        click.echo(f"   Providers: src/data/config/provider/")
        click.echo(f"   Agents: src/data/config/agent/")
        click.echo()
        
        # Quick usage tips
        click.echo("💡 Quick Usage:")
        click.echo("   textcase ask \"Hello\" -m <model>")
        click.echo("   textcase ask \"Hello\" -m <agent>")
        click.echo("   textcase ask \"Hello\" -m <provider>:<model>")
        
    except Exception as e:
        raise click.ClickException(f"Error getting status: {e}")


@llm.command()
@click.argument('name')
@click.pass_context
def info(ctx, name: str):
    """Show detailed information about a specific provider, model, or agent.
    
    Args:
        name: Name of the provider, model, or agent to inspect
    """
    textcase = ctx.obj['textcase']
    
    try:
        provider_configs = _get_provider_configs(textcase)
        agent_configs = _get_agent_configs(textcase)
        available_models = _get_available_models(provider_configs)
        
        found = False
        
        # Check if it's a provider
        if name in provider_configs:
            found = True
            config = provider_configs[name]
            click.echo(f"📡 Provider: {name}\n")
            
            for key, value in config.items():
                if key == 'models' and isinstance(value, dict):
                    click.echo(f"Models:")
                    for model_name, model_config in value.items():
                        click.echo(f"  - {model_name}")
                        if isinstance(model_config, dict):
                            for mk, mv in model_config.items():
                                click.echo(f"    {mk}: {mv}")
                elif key == 'models' and isinstance(value, list):
                    click.echo(f"Models: {', '.join(value)}")
                else:
                    click.echo(f"{key}: {value}")
        
        # Check if it's a model
        if name in available_models:
            if found:
                click.echo("\n" + "="*50 + "\n")
            found = True
            
            click.echo(f"🤖 Model: {name}\n")
            click.echo(f"Supporting Providers: {', '.join(available_models[name])}")
            
            # Show model-specific configurations
            for provider_name in available_models[name]:
                config = provider_configs.get(provider_name, {})
                if 'models' in config and isinstance(config['models'], dict):
                    model_config = config['models'].get(name, {})
                    if model_config:
                        click.echo(f"\nConfiguration in {provider_name}:")
                        for key, value in model_config.items():
                            click.echo(f"  {key}: {value}")
        
        # Check if it's an agent
        if name in agent_configs:
            if found:
                click.echo("\n" + "="*50 + "\n")
            found = True
            
            config = agent_configs[name]
            click.echo(f"🤖 Agent: {name}\n")
            
            for key, value in config.items():
                if key == 'prompt_preview':
                    click.echo(f"Prompt Preview:\n{value}")
                else:
                    click.echo(f"{key}: {value}")
        
        if not found:
            click.echo(f"❌ '{name}' not found in providers, models, or agents.")
            click.echo("\nUse 'textcase llm status' to see available resources.")
            
    except Exception as e:
        raise click.ClickException(f"Error getting info for '{name}': {e}")