"""
Custom conversation settings for Textcase LLM integrations.
"""
from typing import Optional

from humbug.ai.ai_conversation_settings import AIConversationSettings
from humbug.ai.ai_model import AIModel, ReasoningCapability

from textcase.core.logging import get_logger

logger = get_logger(__name__)


class TextcaseConversationSettings(AIConversationSettings):
    """
    Extended conversation settings for Textcase.
    
    This class extends the base AIConversationSettings to handle unknown models
    by preserving the original model name instead of converting to "unknown".
    """
    
    def __init__(self, model: str, temperature: float = 0.7, max_tokens: Optional[int] = None):
        """
        Initialize conversation settings with model preservation.
        
        Args:
            model: The model name to use
            temperature: Temperature for response generation
            max_tokens: Maximum tokens to generate
        """
        # Store the original model name for direct API access
        self.original_model_name = model
        logger.debug(f"Initializing TextcaseConversationSettings with model: {model}")
        
        # Check if model exists in the predefined models
        if model not in self.MODELS:
            logger.info(f"Model '{model}' not found in predefined models, creating dynamic model definition")
            # Create a dynamic model definition to avoid the "unknown" conversion
            self.MODELS[model] = AIModel(
                name=model,  # Use the original name
                provider="auto",  # Let the backend determine the provider
                context_window=200000,  # Use reasonable defaults
                max_output_tokens=8192,
                supports_temperature=True,
                reasoning_capabilities=ReasoningCapability.NO_REASONING
            )
            logger.debug(f"Added dynamic model definition for '{model}'")
        
        # Call the parent constructor with our potentially modified MODELS dictionary
        super().__init__(model=model, temperature=temperature)
        
        # Set max_tokens if provided
        if max_tokens is not None:
            self.max_tokens = max_tokens
            logger.debug(f"Set max_tokens to {max_tokens}")
