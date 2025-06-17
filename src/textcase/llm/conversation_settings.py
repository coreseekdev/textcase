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
"""Custom conversation settings for Textcase LLM integrations.

This module provides extended conversation settings that handle unknown models
by preserving the original model name and allowing manual specification of
model parameters.
"""

from typing import Optional, Dict, Any
import logging

try:
    from humbug.ai.ai_conversation_settings import AIConversationSettings
    from humbug.ai.ai_model import AIModel, ReasoningCapability
    HUMBUG_AVAILABLE = True
except ImportError:
    HUMBUG_AVAILABLE = False
    # Fallback classes for when humbug is not available
    class AIConversationSettings:
        def __init__(self, *args, **kwargs):
            pass
    
    class ReasoningCapability:
        pass

logger = logging.getLogger(__name__)


class TextcaseConversationSettings(AIConversationSettings):
    """Extended conversation settings for Textcase.
    
    This class extends the base AIConversationSettings to handle unknown models
    by preserving the original model name instead of converting to "unknown".
    It also allows manual specification of model parameters for unknown models.
    """
    
    def __init__(
        self, 
        model: str, 
        temperature: Optional[float] = 0.7, 
        max_tokens: Optional[int] = None,
        context_window: Optional[int] = None,
        max_output_tokens: Optional[int] = None,
        reasoning: Optional[ReasoningCapability] = None
    ):
        """Initialize conversation settings with model preservation and custom parameters.
        
        Args:
            model: The model name to use
            temperature: Temperature for response generation (None means model doesn't support temperature)
            max_tokens: Maximum tokens to generate (alias for max_output_tokens)
            max_output_tokens: Maximum output tokens for the model
            context_window: Context window size for the model
            reasoning: Reasoning capabilities for the model
        """
        # Store the original model name for direct API access
        self.original_model_name = model
        logger.debug(f"Initializing TextcaseConversationSettings with model: {model}")
        
        if not HUMBUG_AVAILABLE:
            logger.warning("Humbug not available, using fallback conversation settings")
            self.model = model
            self.temperature = temperature
            self.max_tokens = max_tokens or max_output_tokens
            self.context_window = context_window
            self.max_output_tokens = max_output_tokens
            self.reasoning = reasoning
            return
        
        # Determine if we need to create a dynamic model definition
        is_predefined_model = hasattr(self, 'MODELS') and model in self.MODELS
        
        # For predefined models, we'll use their configuration but can override some parameters
        if is_predefined_model:
            logger.debug(f"Using predefined model configuration for: {model}")
            # Initialize with the predefined model
            super().__init__(model=model)
            
            # Override specific parameters if provided
            if temperature is not None:
                self.temperature = temperature
            if max_tokens is not None:
                self.max_tokens = max_tokens
            if max_output_tokens is not None:
                self.max_output_tokens = max_output_tokens
            if context_window is not None:
                self.context_window = context_window
            if reasoning is not None:
                self.reasoning = reasoning
        else:
            # For unknown models, create a dynamic configuration
            logger.debug(f"Creating dynamic model configuration for: {model}")
            
            # Create a dynamic model definition
            dynamic_model = AIModel(
                name=model,
                context_window=context_window or 4096,  # Default context window
                max_output_tokens=max_output_tokens or max_tokens or 2048,  # Default max output
                reasoning=reasoning or ReasoningCapability.NONE,
                use_temperature=temperature is not None
            )
            
            # Add the dynamic model to the MODELS registry temporarily
            if hasattr(self, 'MODELS'):
                self.MODELS[model] = dynamic_model
            
            # Initialize with the dynamic model
            super().__init__(model=model)
            
            # Set the temperature if provided
            if temperature is not None:
                self.temperature = temperature
    
    def get_model_name_for_api(self) -> str:
        """Get the model name to use for API calls.
        
        This method returns the original model name, preserving it even
        if it's not in the predefined models list.
        
        Returns:
            The original model name
        """
        return self.original_model_name
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert settings to dictionary.
        
        Returns:
            Dictionary representation of the settings
        """
        result = {
            'model': self.original_model_name,
            'temperature': getattr(self, 'temperature', None),
            'max_tokens': getattr(self, 'max_tokens', None),
            'max_output_tokens': getattr(self, 'max_output_tokens', None),
            'context_window': getattr(self, 'context_window', None),
        }
        
        # Only include non-None values
        return {k: v for k, v in result.items() if v is not None}
    
    def __repr__(self) -> str:
        """String representation of the settings.
        
        Returns:
            String representation
        """
        return f"TextcaseConversationSettings(model='{self.original_model_name}', temperature={getattr(self, 'temperature', None)})"