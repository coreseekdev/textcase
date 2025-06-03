#
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
"""URI protocol and related types for resource location.

This module is deprecated and will be removed in a future version.
Please use textcase.protocol.uri.uri instead.
"""

from __future__ import annotations

# Re-export from new location
from .uri.uri import (
    URI,
    URIResolver,
    ResourceType
)

__all__ = [
    'URI',
    'URIResolver',
    'ResourceType',
]


class ResourceType(Protocol):
    """Protocol for resource type definitions."""
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Get the name of the resource type."""
        ...
    
    @property
    @abstractmethod
    def fragment(self) -> str:
        """Get the fragment identifier for this resource type."""
        ...
    
    @property
    @abstractmethod
    def description(self) -> str:
        """Get the description of this resource type."""
        ...


class URI(Protocol):
    """Protocol for Uniform Resource Identifiers in the textcase system."""
    
    @property
    @abstractmethod
    def original(self) -> str:
        """Get the original URI string."""
        ...
    
    @property
    @abstractmethod
    def prefix(self) -> str:
        """Get the module prefix part of the URI."""
        ...
    
    @property
    @abstractmethod
    def id(self) -> str:
        """Get the ID part of the URI."""
        ...
    
    @property
    @abstractmethod
    def heading_path(self) -> str:
        """Get the heading path part of the URI."""
        ...
    
    @property
    @abstractmethod
    def resource_type(self) -> Optional[str]:
        """Get the resource type fragment of the URI."""
        ...
    
    @property
    @abstractmethod
    def normalized(self) -> str:
        """Get the normalized form of the URI."""
        ...
    
    @property
    @abstractmethod
    def is_source_uri(self) -> bool:
        """Check if this is a source code URI."""
        ...
    
    @property
    @abstractmethod
    def is_file_uri(self) -> bool:
        """Check if this is a file URI."""
        ...
    
    @property
    @abstractmethod
    def is_document_uri(self) -> bool:
        """Check if this is a document URI."""
        ...
    
    @abstractmethod
    def with_resource_type(self, resource_type: str) -> URI:
        """Create a new URI with the specified resource type.
        
        Args:
            resource_type: The resource type to set.
            
        Returns:
            A new URI with the specified resource type.
        """
        ...
    
    @abstractmethod
    def with_heading_path(self, heading_path: str) -> URI:
        """Create a new URI with the specified heading path.
        
        Args:
            heading_path: The heading path to set.
            
        Returns:
            A new URI with the specified heading path.
        """
        ...
    
    @abstractmethod
    def with_id(self, id: str) -> URI:
        """Create a new URI with the specified ID.
        
        Args:
            id: The ID to set.
            
        Returns:
            A new URI with the specified ID.
        """
        ...
    
    @abstractmethod
    def with_prefix(self, prefix: str) -> URI:
        """Create a new URI with the specified prefix.
        
        Args:
            prefix: The prefix to set.
            
        Returns:
            A new URI with the specified prefix.
        """
        ...
    
    @abstractmethod
    def __str__(self) -> str:
        """Convert the URI to a string."""
        ...
    
    @abstractmethod
    def __eq__(self, other: object) -> bool:
        """Check if this URI is equal to another URI."""
        ...
    
    @abstractmethod
    def __hash__(self) -> int:
        """Get the hash of this URI."""
        ...


class URIResolver(Protocol):
    """Protocol for resolving URIs to resources."""
    
    @abstractmethod
    def parse(self, uri_string: str) -> URI:
        """Parse a URI string into a URI object.
        
        Args:
            uri_string: The URI string to parse.
            
        Returns:
            A URI object.
            
        Raises:
            ValueError: If the URI string is invalid.
        """
        ...
    
    @abstractmethod
    def resolve(self, uri: Union[str, URI]) -> Any:
        """Resolve a URI to a resource.
        
        Args:
            uri: The URI to resolve, either as a string or a URI object.
            
        Returns:
            The resolved resource, which could be a DocumentItem, SourceCodeItem, 
            FileItem, or other resource type depending on the URI.
            
        Raises:
            ValueError: If the URI is invalid or cannot be resolved.
            FileNotFoundError: If the resource does not exist.
        """
        ...
    
    @abstractmethod
    def get_resource_types(self) -> Dict[str, ResourceType]:
        """Get all registered resource types.
        
        Returns:
            A dictionary mapping resource type names to ResourceType objects.
        """
        ...
    
    @abstractmethod
    def register_resource_type(self, resource_type: ResourceType) -> None:
        """Register a new resource type.
        
        Args:
            resource_type: The resource type to register.
            
        Raises:
            ValueError: If a resource type with the same name or fragment already exists.
        """
        ...
    
    @abstractmethod
    def create_uri(self, 
                  prefix: str, 
                  id: str, 
                  heading_path: Optional[str] = None, 
                  resource_type: Optional[str] = None) -> URI:
        """Create a new URI with the specified components.
        
        Args:
            prefix: The module prefix.
            id: The resource ID.
            heading_path: Optional heading path.
            resource_type: Optional resource type fragment.
            
        Returns:
            A new URI object.
        """
        ...
