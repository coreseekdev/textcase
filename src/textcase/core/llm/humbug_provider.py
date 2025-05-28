"""
Humbug-based LLM provider implementation.
"""
import asyncio
import json
import logging
from typing import Dict, List, Optional, Any, AsyncGenerator
import yaml
from pathlib import Path

from humbug.ai.ai_provider import AIProvider
from humbug.ai.ai_backend_settings import AIBackendSettings
from humbug.ai.ai_message import AIMessage, AIMessageSource

# 使用自定义的会话设置类代替原始的 AIConversationSettings
from textcase.core.llm.conversation_settings import TextcaseConversationSettings

from textcase.core.llm.provider import LLMProvider, LLMResponse
from textcase.core.logging import get_logger

# Get logger for this module
logger = get_logger(__name__)


class HumbugProvider(LLMProvider):
    """Humbug-based LLM provider implementation."""
    
    def __init__(self, provider_name: str, backend_settings: Dict[str, AIBackendSettings]):
        """
        Initialize HumbugProvider.
        
        Args:
            provider_name: Name of the provider (e.g., 'openai', 'anthropic')
            backend_settings: Dictionary of backend settings
        """
        logger.info(f"Initializing HumbugProvider for provider: {provider_name}")
        logger.debug(f"Backend settings: {backend_settings}")
        
        self.provider_name = provider_name
        self.backend_settings = backend_settings
        
        try:
            logger.debug("Creating backends using AIProvider.create_backends")
            self.backends = AIProvider.create_backends(backend_settings)
            
            if not self.backends:
                logger.error("No backends were created from the provided configuration")
                raise ValueError(f"No backends were created. Check your configuration.")
                
            logger.debug(f"Available backends: {list(self.backends.keys())}")
            
            if provider_name not in self.backends:
                available = list(self.backends.keys())
                logger.error(f"Provider '{provider_name}' not found in available backends: {available}")
                raise ValueError(f"Provider '{provider_name}' not found in available backends: {available}")
                
            self.backend = self.backends[provider_name]
            logger.info(f"Successfully initialized backend for provider: {provider_name}")
        except Exception as e:
            logger.exception(f"Error initializing HumbugProvider: {str(e)}")
            raise
    
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
        request_id = f"{model}-{str(id(prompt))[:8]}"
        logger.info(f"[{request_id}] Starting LLM request with model: {model}")
        
        temperature = kwargs.get('temperature', 0.7)
        max_tokens = kwargs.get('max_tokens', None)
        top_p = kwargs.get('top_p', None)
        
        # Log request parameters
        logger.info(f"[{request_id}] Using provider: {self.provider_name}")
        logger.info(f"[{request_id}] Model: {model}")
        logger.debug(f"[{request_id}] Temperature: {temperature}")
        if max_tokens:
            logger.debug(f"[{request_id}] Max tokens: {max_tokens}")
        if top_p:
            logger.debug(f"[{request_id}] Top P: {top_p}")
            
        # For console output (will be removed once logging is fully integrated)
        print(f"[DEBUG] Using provider: {self.provider_name}")
        print(f"[DEBUG] Model: {model}")
        print(f"[DEBUG] Temperature: {temperature}")
        
        # Create conversation settings
        logger.debug(f"[{request_id}] Creating conversation settings")
        conversation_settings = TextcaseConversationSettings(
            model=model,
            temperature=temperature
        )
        
        # Create message history
        messages = [
            {"role": "user", "content": prompt}
        ]
        
        # Log truncated prompt for debugging (avoid logging entire large prompts)
        truncated_prompt = prompt[:100] + "..." if len(prompt) > 100 else prompt
        logger.debug(f"[{request_id}] Prompt (truncated): {truncated_prompt}")
        logger.debug(f"[{request_id}] Prompt length: {len(prompt)} chars")
        
        # Print request info for console
        print(f"[DEBUG] Sending request to model: {model}")
        print(f"[DEBUG] Messages: {messages}")
        
        # Collect the full response
        full_response = ""
        usage = {}
        chunk_count = 0
        
        logger.info(f"[{request_id}] Sending request to LLM API")
        start_time = asyncio.get_event_loop().time()
        
        try:
            # Stream the response and collect it
            async for response in self.backend.stream_message(messages, conversation_settings):
                chunk_count += 1
                
                if chunk_count == 1:
                    logger.debug(f"[{request_id}] Received first chunk from API")
                
                if response.error:
                    logger.error(f"[{request_id}] Error from LLM: {response.error}")
                    logger.error(f"[{request_id}] Error details: {vars(response)}")
                    print(f"[DEBUG] Error from LLM: {response.error}")
                    print(f"[DEBUG] Error details: {vars(response)}")
                    raise Exception(f"Error from LLM: {response.error}")
                
                # Log response attributes for debugging
                if chunk_count == 1 or chunk_count % 10 == 0:  # Log first chunk and every 10th chunk
                    logger.debug(f"[{request_id}] Chunk #{chunk_count} attributes: {dir(response)}")
                
                # Process content
                if response.content:
                    # Only log content length to avoid filling logs with response text
                    content_len = len(response.content)
                    
                    # In non-streaming mode, we need to handle the full content differently
                    # Each chunk from the API contains the complete response up to that point
                    if chunk_count == 1:
                        # First chunk - just store it
                        full_response = response.content
                        logger.debug(f"[{request_id}] Chunk #{chunk_count}: received initial content of {content_len} chars")
                    else:
                        # For subsequent chunks, only keep the latest complete response
                        # Don't append to avoid duplication
                        prev_len = len(full_response)
                        
                        # Check if this is a new, longer response
                        if content_len > prev_len:
                            new_content_len = content_len - prev_len
                            logger.debug(f"[{request_id}] Chunk #{chunk_count}: received {new_content_len} new chars")
                            full_response = response.content
                        else:
                            logger.debug(f"[{request_id}] Chunk #{chunk_count}: no new content (current: {content_len}, previous: {prev_len})")

                else:
                    logger.debug(f"[{request_id}] Chunk #{chunk_count}: empty content")
                    
                # Process usage info
                if response.usage:
                    usage = response.usage
                    logger.debug(f"[{request_id}] Updated usage info: {usage}")
                    
            # Log completion statistics
            end_time = asyncio.get_event_loop().time()
            duration = end_time - start_time
            logger.info(f"[{request_id}] Request completed in {duration:.2f}s, received {chunk_count} chunks")
            logger.info(f"[{request_id}] Total response length: {len(full_response)} chars")
            if usage:
                logger.info(f"[{request_id}] Final usage: {usage}")
                    
        except Exception as e:
            end_time = asyncio.get_event_loop().time()
            duration = end_time - start_time
            logger.exception(f"[{request_id}] Exception during LLM request after {duration:.2f}s: {str(e)}")
            logger.error(f"[{request_id}] Exception type: {type(e).__name__}")
            
            # Console output
            print(f"[DEBUG] Exception during LLM request: {str(e)}")
            print(f"[DEBUG] Exception type: {type(e).__name__}")
            import traceback
            traceback.print_exc()
            raise
        
        # Check if we got an empty response
        if not full_response:
            logger.warning(f"[{request_id}] Received empty response from LLM")
            
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
        request_id = f"{model}-stream-{str(id(prompt))[:8]}"
        logger.info(f"[{request_id}] Starting streaming LLM request with model: {model}")
        
        temperature = kwargs.get('temperature', 0.7)
        max_tokens = kwargs.get('max_tokens', None)
        
        # Log request parameters
        logger.info(f"[{request_id}] Using provider: {self.provider_name}")
        logger.info(f"[{request_id}] Model: {model}")
        logger.debug(f"[{request_id}] Temperature: {temperature}")
        if max_tokens:
            logger.debug(f"[{request_id}] Max tokens: {max_tokens}")
        
        # Create conversation settings
        logger.debug(f"[{request_id}] Creating conversation settings")
        conversation_settings = TextcaseConversationSettings(
            model=model,
            temperature=temperature
        )
        
        # Create message history
        messages = [
            {"role": "user", "content": prompt}
        ]
        
        # Log truncated prompt for debugging
        truncated_prompt = prompt[:100] + "..." if len(prompt) > 100 else prompt
        logger.debug(f"[{request_id}] Prompt (truncated): {truncated_prompt}")
        logger.debug(f"[{request_id}] Prompt length: {len(prompt)} chars")
        
        # Track the full response to identify new content
        full_response = ""
        chunk_count = 0
        total_yielded_chars = 0
        
        logger.info(f"[{request_id}] Starting streaming request to LLM API")
        start_time = asyncio.get_event_loop().time()
        
        try:
            # Stream the response
            async for response in self.backend.stream_message(messages, conversation_settings):
                chunk_count += 1
                
                if chunk_count == 1:
                    logger.debug(f"[{request_id}] Received first chunk from API")
                    
                if response.error:
                    logger.error(f"[{request_id}] Error from LLM: {response.error}")
                    logger.error(f"[{request_id}] Response details: {vars(response)}")
                    raise Exception(f"Error from LLM: {response.error}")
                
                # Log response details periodically
                if chunk_count == 1 or chunk_count % 10 == 0:
                    logger.debug(f"[{request_id}] Chunk #{chunk_count} attributes: {dir(response)}")
                    if hasattr(response, 'content'):
                        content_exists = response.content is not None
                        content_len = len(response.content) if content_exists else 0
                        logger.debug(f"[{request_id}] Content exists: {content_exists}, length: {content_len}")
                    else:
                        logger.debug(f"[{request_id}] Response has no 'content' attribute")
                
                if response.content:
                    # Get the complete current response
                    current_response = response.content
                    current_len = len(current_response)
                    logger.debug(f"[{request_id}] Chunk #{chunk_count}: received content of length {current_len}")
                    
                    # Handle the first chunk specially
                    if chunk_count == 1:
                        logger.debug(f"[{request_id}] First chunk, yielding entire content")
                        full_response = current_response
                        total_yielded_chars += current_len
                        yield current_response
                    else:
                        # For subsequent chunks, only yield the new content
                        prev_len = len(full_response)
                        
                        # Check if this response is longer than what we've seen before
                        if current_len > prev_len and current_response.startswith(full_response):
                            # Extract only the new content
                            new_content = current_response[prev_len:]
                            new_content_len = len(new_content)
                            
                            if new_content_len > 0:
                                logger.debug(f"[{request_id}] Yielding new content: {new_content_len} chars")
                                full_response = current_response
                                total_yielded_chars += new_content_len
                                yield new_content
                            else:
                                logger.debug(f"[{request_id}] No new content to yield")
                        elif current_response != full_response:
                            # Handle inconsistency (rare case)
                            logger.warning(f"[{request_id}] Content inconsistency detected")
                            logger.debug(f"[{request_id}] Previous content: '{full_response[:50]}...'")
                            logger.debug(f"[{request_id}] Current content: '{current_response[:50]}...'")
                            
                            # Try to find where they diverge and only yield the new part
                            # Find the common prefix
                            common_len = 0
                            min_len = min(prev_len, current_len)
                            
                            for i in range(min_len):
                                if full_response[i] != current_response[i]:
                                    break
                                common_len += 1
                            
                            if common_len > 0 and common_len < current_len:
                                # Yield only the new part after the common prefix
                                new_content = current_response[common_len:]
                                logger.debug(f"[{request_id}] Yielding divergent content from position {common_len}: {len(new_content)} chars")
                                full_response = current_response
                                total_yielded_chars += len(new_content)
                                yield new_content
                            else:
                                # Fallback: yield the whole new response
                                logger.debug(f"[{request_id}] Yielding entire new content due to major divergence")
                                full_response = current_response
                                total_yielded_chars += current_len
                                yield current_response
                        else:
                            logger.debug(f"[{request_id}] No new content in this chunk")

                else:
                    logger.debug(f"[{request_id}] Chunk #{chunk_count}: empty content")
            
            # Log completion statistics
            end_time = asyncio.get_event_loop().time()
            duration = end_time - start_time
            logger.info(f"[{request_id}] Streaming completed in {duration:.2f}s")
            logger.info(f"[{request_id}] Received {chunk_count} chunks, yielded {total_yielded_chars} chars")
            
        except Exception as e:
            end_time = asyncio.get_event_loop().time()
            duration = end_time - start_time
            logger.exception(f"[{request_id}] Exception during streaming after {duration:.2f}s: {str(e)}")
            logger.error(f"[{request_id}] Exception type: {type(e).__name__}")
            raise
    
    @classmethod
    def from_config(cls, config: Dict[str, Any]) -> 'HumbugProvider':
        """
        Create a provider instance from a configuration dictionary.
        
        Args:
            config: Configuration dictionary
            
        Returns:
            HumbugProvider instance
        """
        logger.info(f"Creating HumbugProvider from config: {config.get('type')}")
        
        try:
            provider_type = config.get('type')
            if not provider_type:
                logger.error("Provider type not specified in configuration")
                raise ValueError("Provider type not specified in configuration")
                
            logger.debug(f"Provider type: {provider_type}")
            
            # Get available models from config
            models = config.get('model', [])
            if models:
                logger.info(f"Available models for provider {provider_type}: {models}")
            else:
                logger.warning(f"No models specified for provider {provider_type}")
                
            # Create backend settings
            # Ensure the API URL includes the complete path to the chat completions endpoint
            api_base = config.get('api_base', '')
            logger.debug(f"API base URL: {api_base}")
            
            # If the URL doesn't end with /chat/completions, append it
            if api_base and not api_base.endswith('/chat/completions'):
                # Remove trailing slash if present
                if api_base.endswith('/'):
                    api_base = api_base[:-1]
                # Add the chat completions endpoint
                api_url = f"{api_base}/chat/completions"
            else:
                api_url = api_base
                
            logger.info(f"Using API URL: {api_url}")
            print(f"[DEBUG] Using API URL: {api_url}")  # Keep console output for now
                
            # Check if API key is provided
            api_key = config.get('api_key', '')
            if not api_key:
                logger.warning(f"No API key provided for {provider_type}")
            else:
                # Log a masked version of the API key for debugging
                masked_key = api_key[:4] + "*" * (len(api_key) - 8) + api_key[-4:] if len(api_key) > 8 else "****"
                logger.debug(f"Using API key: {masked_key}")
                
            # Create backend settings
            backend_settings = {
                provider_type: AIBackendSettings(
                    enabled=True,
                    api_key=api_key,
                    url=api_url
                )
            }
            
            logger.debug(f"Created backend settings for {provider_type}")
            
            # Create and return the provider instance
            logger.info(f"Initializing HumbugProvider for {provider_type}")
            return cls(provider_type, backend_settings)
            
        except Exception as e:
            logger.exception(f"Error creating HumbugProvider from config: {str(e)}")
            raise
