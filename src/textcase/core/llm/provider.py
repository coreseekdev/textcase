"""
LLM Provider abstraction for textcase.
"""
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any, AsyncGenerator
import os
import yaml
import jinja2
import jinja2.meta
from pathlib import Path


class LLMResponse:
    """Response from an LLM."""
    
    def __init__(self, content: str, usage: Optional[Dict[str, Any]] = None):
        """Initialize LLMResponse."""
        self.content = content
        self.usage = usage or {}


class LLMProvider(ABC):
    """Abstract base class for LLM providers."""
    
    @abstractmethod
    async def generate(self, prompt: str, model: str, **kwargs) -> LLMResponse:
        """
        Generate a response from the LLM.
        
        Args:
            prompt: The prompt to send to the LLM
            model: The model to use
            **kwargs: Additional provider-specific parameters
            
        Returns:
            LLMResponse object containing the generated content
        """
        pass
    
    @abstractmethod
    async def generate_stream(self, prompt: str, model: str, **kwargs) -> AsyncGenerator[str, None]:
        """
        Generate a streaming response from the LLM.
        
        Args:
            prompt: The prompt to send to the LLM
            model: The model to use
            **kwargs: Additional provider-specific parameters
            
        Returns:
            AsyncGenerator yielding content chunks as they are generated
        """
        pass
    
    @classmethod
    @abstractmethod
    def from_config(cls, config: Dict[str, Any]) -> 'LLMProvider':
        """
        Create a provider instance from a configuration dictionary.
        
        Args:
            config: Configuration dictionary
            
        Returns:
            LLMProvider instance
        """
        pass
    
    @classmethod
    def _parse_template_variables(cls, template_content: str) -> set[str]:
        """Parse and return all template variables from the content.
        
        Args:
            template_content: The template content to parse
            
        Returns:
            Set of variable names found in the template
        """
        env = jinja2.Environment()
        ast = env.parse(template_content)
        return jinja2.meta.find_undeclared_variables(ast)

    @classmethod
    def _get_env_var(cls, var_name: str, provider_name: str = '') -> Optional[str]:
        """Get environment variable with fallback to provider-prefixed variable."""        
        # Try direct variable first (case-insensitive)
        for key, value in os.environ.items():
            if key.upper() == var_name.upper():
                return value
        
        # Try provider-prefixed variable (case-insensitive)
        if provider_name:
            target_prefix = f"{provider_name.upper()}_{var_name.upper()}"
            for key, value in os.environ.items():
                if key.upper() == target_prefix:
                    return value
        
        return None

    @classmethod
    def load_config(cls, config_path: Path) -> Dict[str, Any]:
        """
        Load configuration from a YAML file with environment variable substitution.
        
        The YAML file can include Jinja2 template syntax. Environment variables can be referenced as:
        - {{ env.VAR_NAME }} - Access any environment variable
        - {{ VAR_NAME }} - Access provider-specific environment variables (prefixed with provider name)
        
        Example:
            api_key: "{{ XTY_API_KEY }}"  # Will use XTY_API_KEY from environment
            base_url: "{{ env.XTY_BASE_URL or 'https://api.example.com' }}"
            
        Args:
            config_path: Path to the configuration file
            
        Returns:
            Configuration dictionary with environment variables substituted
            
        Raises:
            FileNotFoundError: If the config file doesn't exist
            ValueError: If a required environment variable is missing
            yaml.YAMLError: If there's an error parsing the YAML
        """
        if not config_path.exists():
            raise FileNotFoundError(f"Config file not found: {config_path}")
        
        try:
            # Read the YAML content
            with open(config_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Get provider name from config path
            provider_name = config_path.stem.split('.')[0].upper()
            
            # Create Jinja2 environment with custom undefined handler
            env = jinja2.Environment(
                undefined=jinja2.StrictUndefined,  # Raise error for undefined variables
                variable_start_string='{{',
                variable_end_string='}}',
            )
            
            # Parse the template to find all variables
            ast = env.parse(content)
            template_vars = jinja2.meta.find_undeclared_variables(ast)
            
            # Prepare context with environment variables
            context = {}
            for var in template_vars:
                # Handle environment variables (e.g., {{ env.VAR_NAME }})
                if var.startswith('env.') and len(var) > 4:
                    env_key = var[4:]
                    if env_key in os.environ:
                        context[var] = os.environ[env_key]
                # Handle direct variables (e.g., {{ VAR_NAME }})
                else:
                    # First try direct variable, then provider-prefixed variable
                    value = cls._get_env_var(var, provider_name)
                    if value is not None:
                        context[var] = value
            
            # Add built-in variables
            context.update({
                'cwd': str(Path.cwd()),
                'home': str(Path.home()),
                'config_dir': str(config_path.parent),
                'provider_name': provider_name,
            })
            
            # Render the template
            template = env.from_string(content)
            rendered = template.render(**context)
            
            # Parse the rendered YAML
            return yaml.safe_load(rendered)
            
        except jinja2.exceptions.UndefinedError as e:
            # Extract provider name from config path
            provider_name = config_path.stem.split('.')[0].upper()
            
            # Extract the variable name from the error message
            # e.args[0] is like "'api_key' is undefined"
            try:
                var_name = e.args[0].split("'")[1]  # Get the part between single quotes
                env_var_name = f"{provider_name}_{var_name.upper()}"
                error_msg = f"Missing required variable: {e}, try define environment variable: {env_var_name}"
            except (IndexError, AttributeError):
                # Fallback to original error if parsing fails
                error_msg = f"Missing required variable: {e}"
                
            raise ValueError(error_msg)
        except yaml.YAMLError as e:
            raise yaml.YAMLError(f"Error parsing YAML in {config_path}: {e}")
        except Exception as e:
            raise ValueError(f"Error processing config file {config_path}: {e}")
