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
"""LLM response protocol.

This module defines the protocol for LLM response objects.
"""

from typing import Protocol, Dict, Any


class LLMResponseProtocol(Protocol):
    """Protocol for LLM response objects.
    
    Defines the interface that LLM response objects should implement.
    """
    
    @property
    def content(self) -> str:
        """Get the response content.
        
        Returns:
            The generated text content
        """
        ...
    
    @property
    def model(self) -> str:
        """Get the model used for generation.
        
        Returns:
            The model name
        """
        ...
    
    @property
    def provider(self) -> str:
        """Get the provider used for generation.
        
        Returns:
            The provider name
        """
        ...
    
    @property
    def metadata(self) -> Dict[str, Any]:
        """Get response metadata.
        
        Returns:
            Dictionary containing metadata like token counts, timing, etc.
        """
        ...