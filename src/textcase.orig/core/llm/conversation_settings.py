"""
Custom conversation settings for Textcase LLM integrations.
"""
from typing import Optional, Dict, Any

from humbug.ai.ai_conversation_settings import AIConversationSettings
from humbug.ai.ai_model import AIModel, ReasoningCapability

from textcase.core.logging import get_logger

logger = get_logger(__name__)


class TextcaseConversationSettings(AIConversationSettings):
    """
    Extended conversation settings for Textcase.
    
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
        """
        Initialize conversation settings with model preservation and custom parameters.
        
        Args:
            model: The model name to use
            temperature: Temperature for response generation (None means model doesn't support temperature)
            max_tokens: Maximum tokens to generate (alias for max_output_tokens)
            context_window: Context window size for the model
            max_output_tokens: Maximum output tokens for the model
            reasoning: Reasoning capabilities for the model
        """
        # Store the original model name for direct API access
        self.original_model_name = model
        logger.debug(f"Initializing TextcaseConversationSettings with model: {model}")
        
        # Determine if we need to create a dynamic model definition
        is_predefined_model = model in self.MODELS
        
        # For predefined models, we'll use their configuration but can override some parameters
        if not is_predefined_model:
            logger.info(f"Model '{model}' not found in predefined models, creating dynamic model definition")
            
            # Use provided values or defaults
            _context_window = context_window or self.DEFAULT_CONTEXT_WINDOW
            _max_output_tokens = max_output_tokens or max_tokens or self.DEFAULT_MAX_OUTPUT_TOKENS
            _supports_temperature = temperature is not None
            _reasoning_capabilities = reasoning or self.DEFAULT_REASONING_CAPABILITY
            
            # Create a dynamic model definition to avoid the "unknown" conversion
            self.MODELS[model] = AIModel(
                name=model,  # Use the original name
                provider="auto",  # Let the backend determine the provider
                context_window=_context_window,
                max_output_tokens=_max_output_tokens,
                supports_temperature=_supports_temperature,
                reasoning_capabilities=_reasoning_capabilities
            )
            logger.debug(f"Added dynamic model definition for '{model}' with: "
                         f"context_window={_context_window}, "
                         f"max_output_tokens={_max_output_tokens}, "
                         f"supports_temperature={_supports_temperature}, "
                         f"reasoning_capabilities={_reasoning_capabilities}")
        
        # Call the parent constructor with our potentially modified MODELS dictionary
        # For temperature, use None if the model doesn't support it
        if is_predefined_model and not self.supports_temperature(model):
            # For predefined models that don't support temperature, force it to None
            super().__init__(model=model, temperature=None, reasoning=reasoning or self.get_reasoning_capability(model))
        else:
            # Otherwise use the provided temperature
            super().__init__(model=model, temperature=temperature, reasoning=reasoning or self.get_reasoning_capability(model))
        
        # Override max_tokens/max_output_tokens if provided for any model (even predefined ones)
        if max_tokens is not None:
            self.max_tokens = max_tokens
            logger.debug(f"Set max_tokens to {max_tokens}")
            
        # Override max_output_tokens if explicitly provided (takes precedence over max_tokens)
        if max_output_tokens is not None:
            self.max_output_tokens = max_output_tokens
            logger.debug(f"Set max_output_tokens to {max_output_tokens}")
            
        # Override context_window if provided
        if context_window is not None:
            self.context_window = context_window
            logger.debug(f"Set context_window to {context_window}")
    
    @classmethod
    def get_name(cls, model: str) -> str:
        """
        Get the name for a given model.
        
        Args:
            model: Name of the model
            
        Returns:
            Model name (always returns the original model name, never "unknown")
        """
        model_config = cls.MODELS.get(model)
        if model_config:
            return model_config.name
        
        # Return the original model name instead of "unknown"
        return model
    
    @classmethod
    def get_provider(cls, model: str) -> str:
        """
        Get the provider for a given model.
        
        Args:
            model: Name of the model
            
        Returns:
            Provider name or "auto" if model not found
        """
        model_config = cls.MODELS.get(model)
        if model_config:
            return model_config.provider
        
        # Return "auto" instead of "unknown" to let the backend determine the provider
        return "auto"
    
    @classmethod
    def supports_temperature(cls, model: str) -> bool:
        """
        Check if model supports temperature setting.
        
        Args:
            model: Name of the model
            
        Returns:
            True if the model supports temperature, False otherwise
        """
        model_config = cls.MODELS.get(model)
        if model_config:
            return model_config.supports_temperature
        
        # Default to True for unknown models
        return True
    
    @classmethod
    def get_model_limits(cls, model: str) -> Dict[str, int]:
        """
        Get the context window and max output tokens for a model.
        
        Args:
            model: Name of the model
            
        Returns:
            Dictionary with context_window and max_output_tokens keys
        """
        model_config = cls.MODELS.get(model)
        if model_config:
            return {
                "context_window": model_config.context_window,
                "max_output_tokens": model_config.max_output_tokens
            }
        
        # Return default values for unknown models
        return {
            "context_window": cls.DEFAULT_CONTEXT_WINDOW,
            "max_output_tokens": cls.DEFAULT_MAX_OUTPUT_TOKENS
        }
    
    @classmethod
    def get_reasoning_capability(cls, model: str) -> ReasoningCapability:
        """
        Get the reasoning capabilities supported by a model.
        
        Args:
            model: Name of the model
            
        Returns:
            ReasoningCapability bitmap of supported reasoning capabilities
        """
        model_config = cls.MODELS.get(model)
        if model_config:
            return model_config.reasoning_capabilities
        
        # Return default reasoning capability for unknown models
        return cls.DEFAULT_REASONING_CAPABILITY
