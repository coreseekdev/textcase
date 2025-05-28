"""
Humbug-based LLM provider implementation.
"""
import asyncio
from typing import Dict, List, Optional, Any, AsyncGenerator
import yaml
from pathlib import Path

from humbug.ai.ai_provider import AIProvider
from humbug.ai.ai_backend_settings import AIBackendSettings
from humbug.ai.ai_conversation_settings import AIConversationSettings
from humbug.ai.ai_message import AIMessage, AIMessageSource

from textcase.core.llm.provider import LLMProvider, LLMResponse


class HumbugProvider(LLMProvider):
    """Humbug-based LLM provider implementation."""
    
    def __init__(self, provider_name: str, backend_settings: Dict[str, AIBackendSettings]):
        """
        Initialize HumbugProvider.
        
        Args:
            provider_name: Name of the provider (e.g., 'openai', 'anthropic')
            backend_settings: Dictionary of backend settings
        """
        self.provider_name = provider_name
        self.backend_settings = backend_settings
        self.backends = AIProvider.create_backends(backend_settings)
        
        if not self.backends:
            raise ValueError(f"No backends were created. Check your configuration.")
            
        if provider_name not in self.backends:
            available = list(self.backends.keys())
            raise ValueError(f"Provider '{provider_name}' not found in available backends: {available}")
            
        self.backend = self.backends[provider_name]
    
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
        temperature = kwargs.get('temperature', 0.7)
        
        # Print debug info
        print(f"[DEBUG] Using provider: {self.provider_name}")
        print(f"[DEBUG] Model: {model}")
        print(f"[DEBUG] Temperature: {temperature}")
        
        # Create conversation settings
        conversation_settings = AIConversationSettings(
            model=model,
            temperature=temperature
        )
        
        # Create message history
        messages = [
            {"role": "user", "content": prompt}
        ]
        
        # Print request info
        print(f"[DEBUG] Sending request to model: {model}")
        print(f"[DEBUG] Messages: {messages}")
        
        # Collect the full response
        full_response = ""
        usage = {}
        
        try:
            # Stream the response and collect it
            async for response in self.backend.stream_message(messages, conversation_settings):
                if response.error:
                    print(f"[DEBUG] Error from LLM: {response.error}")
                    print(f"[DEBUG] Error details: {vars(response)}")
                    raise Exception(f"Error from LLM: {response.error}")
                
                if response.content:
                    full_response += response.content
                    
                if response.usage:
                    usage = response.usage
                    
        except Exception as e:
            print(f"[DEBUG] Exception during LLM request: {str(e)}")
            print(f"[DEBUG] Exception type: {type(e).__name__}")
            import traceback
            traceback.print_exc()
            raise
                
            if response.content:
                full_response += response.content
                
            if response.usage:
                usage = response.usage
        
        return LLMResponse(full_response, usage)
    
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
        temperature = kwargs.get('temperature', 0.7)
        
        # Create conversation settings
        conversation_settings = AIConversationSettings(
            model=model,
            temperature=temperature
        )
        
        # Create message history
        messages = [
            {"role": "user", "content": prompt}
        ]
        
        # Track the full response to identify new content
        full_response = ""
        
        # Stream the response
        async for response in self.backend.stream_message(messages, conversation_settings):
            if response.error:
                raise Exception(f"Error from LLM: {response.error}")
                
            if response.content:
                # Get the complete current response
                current_response = response.content
                
                # Only yield the new part that hasn't been sent before
                if current_response.startswith(full_response) and current_response != full_response:
                    new_content = current_response[len(full_response):]
                    full_response = current_response
                    yield new_content
                elif not current_response.startswith(full_response):
                    # If there's an inconsistency, yield the whole chunk
                    # (this should be rare but handles edge cases)
                    full_response = current_response
                    yield current_response
    
    @classmethod
    def from_config(cls, config: Dict[str, Any]) -> 'HumbugProvider':
        """
        Create a provider instance from a configuration dictionary.
        
        Args:
            config: Configuration dictionary
            
        Returns:
            HumbugProvider instance
        """
        provider_type = config.get('type')
        if not provider_type:
            raise ValueError("Provider type not specified in configuration")
            
        # Create backend settings
        # Ensure the API URL includes the complete path to the chat completions endpoint
        api_base = config.get('api_base', '')
        
        # If the URL doesn't end with /chat/completions, append it
        if api_base and not api_base.endswith('/chat/completions'):
            # Remove trailing slash if present
            if api_base.endswith('/'):
                api_base = api_base[:-1]
            # Add the chat completions endpoint
            api_url = f"{api_base}/chat/completions"
        else:
            api_url = api_base
            
        print(f"[DEBUG] Using API URL: {api_url}")
            
        backend_settings = {
            provider_type: AIBackendSettings(
                enabled=True,
                api_key=config.get('api_key', ''),
                url=api_url
            )
        }
        
        return cls(provider_type, backend_settings)
