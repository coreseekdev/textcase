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
from ...core.llm import LLMFactory, AgentFactory


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


def _get_provider_configs(textcase: TextCase) -> Dict[str, Dict[str, Any]]:
    """Get all provider configurations.
    
    Args:
        textcase: TextCase instance
        
    Returns:
        Dictionary mapping provider names to their configurations
    """
    providers = {}
    
    # Get provider config directory
    config_manager = textcase.get_resource_manager()
    provider_collections = config_manager.get_template_collections('provider')
    
    for collection_name in provider_collections:
        try:
            # Get provider config directory
            provider_dir = Path(textcase.repo_root_path) / 'src' / 'data' / 'config' / 'provider' / collection_name
            
            # Look for YAML config files
            for config_file in provider_dir.glob('*.yml'):
                if config_file.stem != 'default':
                    config = _load_yaml_config(config_file)
                    if config:
                        providers[config_file.stem] = config
                        
            # Also check for .yaml files
            for config_file in provider_dir.glob('*.yaml'):
                if config_file.stem != 'default':
                    config = _load_yaml_config(config_file)
                    if config:
                        providers[config_file.stem] = config
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
    
    # Get agent config directory
    config_manager = textcase.get_resource_manager()
    agent_collections = config_manager.get_template_collections('agent')
    
    for collection_name in agent_collections:
        try:
            # Get agent config directory
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


def _get_available_models(providers: Dict[str, Dict[str, Any]]) -> Dict[str, List[str]]:
    """Get available models from provider configurations.
    
    Args:
        providers: Provider configurations
        
    Returns:
        Dictionary mapping model names to supporting provider names
    """
    models = {}
    
    for provider_name, config in providers.items():
        if 'models' in config:
            if isinstance(config['models'], dict):
                # New format: models as dict with model configs
                for model_name in config['models'].keys():
                    if model_name not in models:
                        models[model_name] = []
                    models[model_name].append(provider_name)
            elif isinstance(config['models'], list):
                # Old format: models as list
                for model_name in config['models']:
                    if model_name not in models:
                        models[model_name] = []
                    models[model_name].append(provider_name)
        elif 'model' in config:
            # Single model format
            if isinstance(config['model'], list):
                for model_name in config['model']:
                    if model_name not in models:
                        models[model_name] = []
                    models[model_name].append(provider_name)
            else:
                model_name = config['model']
                if model_name not in models:
                    models[model_name] = []
                models[model_name].append(provider_name)
                
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
@click.pass_context
def providers(ctx):
    """List all available LLM providers.
    
    Shows all configured LLM providers with their basic information.
    """
    textcase = ctx.obj['textcase']
    
    try:
        provider_configs = _get_provider_configs(textcase)
        
        if not provider_configs:
            click.echo("No providers configured.")
            click.echo("\nTo add a provider, create a configuration file in:")
            click.echo("  src/data/config/provider/<collection>/")
            return
        
        click.echo(f"Found {len(provider_configs)} provider(s):\n")
        
        for provider_name, config in provider_configs.items():
            click.echo(f"📡 {provider_name}")
            
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
@click.pass_context
def models(ctx):
    """List all available models.
    
    Shows all available models with their supporting providers.
    """
    textcase = ctx.obj['textcase']
    
    try:
        provider_configs = _get_provider_configs(textcase)
        available_models = _get_available_models(provider_configs)
        
        if not available_models:
            click.echo("No models configured.")
            click.echo("\nModels are defined in provider configuration files.")
            return
        
        click.echo(f"Found {len(available_models)} model(s):\n")
        
        # Check if there's a default model
        default_model = None
        agent_configs = _get_agent_configs(textcase)
        if 'default' in agent_configs and 'model' in agent_configs['default']:
            default_model = agent_configs['default']['model']
        
        for model_name, supporting_providers in sorted(available_models.items()):
            is_default = model_name == default_model
            default_marker = " (default)" if is_default else ""
            
            click.echo(f"🤖 {model_name}{default_marker}")
            click.echo(f"   Providers: {', '.join(supporting_providers)}")
            
            # Show model-specific config if available
            for provider_name in supporting_providers:
                config = provider_configs.get(provider_name, {})
                if 'models' in config and isinstance(config['models'], dict):
                    model_config = config['models'].get(model_name, {})
                    if model_config:
                        if 'max_tokens' in model_config:
                            click.echo(f"   Max Tokens: {model_config['max_tokens']} ({provider_name})")
                        if 'context_window' in model_config:
                            click.echo(f"   Context Window: {model_config['context_window']} ({provider_name})")
                        break
            
            click.echo()
            
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
        available_models = _get_available_models(provider_configs)
        
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