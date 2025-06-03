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
"""Resource protocols and related types for textcase.

This module is deprecated and will be removed in a future version.
Please use textcase.protocol.uri.resource instead.
"""

from __future__ import annotations

# Re-export from new location
from .uri.resource import (
    Resource,
    ResourceMetadata,
    ResourceContent,
    ResourceReference,
    ResourceRegistry
)

__all__ = [
    'Resource',
    'ResourceMetadata',
    'ResourceContent',
    'ResourceReference',
    'ResourceRegistry',
]


class ResourceMetadata(Protocol):
    """Protocol for resource metadata."""
    
    @property
    @abstractmethod
    def title(self) -> str:
        """Get the resource title."""
        ...
    
    @property
    @abstractmethod
    def description(self) -> Optional[str]:
        """Get the resource description."""
        ...
    
    @property
    @abstractmethod
    def tags(self) -> List[str]:
        """Get the resource tags."""
        ...
    
    @property
    @abstractmethod
    def created_at(self) -> Optional[str]:
        """Get the resource creation time."""
        ...
    
    @property
    @abstractmethod
    def updated_at(self) -> Optional[str]:
        """Get the resource last update time."""
        ...
    
    @property
    @abstractmethod
    def attributes(self) -> Dict[str, Any]:
        """Get all resource attributes."""
        ...
    
    @abstractmethod
    def get_attribute(self, name: str, default: Any = None) -> Any:
        """Get a resource attribute.
        
        Args:
            name: The attribute name.
            default: The default value to return if the attribute does not exist.
            
        Returns:
            The attribute value, or the default value if the attribute does not exist.
        """
        ...
    
    @abstractmethod
    def set_attribute(self, name: str, value: Any) -> None:
        """Set a resource attribute.
        
        Args:
            name: The attribute name.
            value: The attribute value.
        """
        ...


class ResourceContent(Protocol):
    """Protocol for resource content."""
    
    @property
    @abstractmethod
    def content_type(self) -> str:
        """Get the content type."""
        ...
    
    @property
    @abstractmethod
    def encoding(self) -> Optional[str]:
        """Get the content encoding."""
        ...
    
    @abstractmethod
    def as_text(self) -> str:
        """Get the content as text.
        
        Returns:
            The content as text.
            
        Raises:
            ValueError: If the content cannot be converted to text.
        """
        ...
    
    @abstractmethod
    def as_bytes(self) -> bytes:
        """Get the content as bytes.
        
        Returns:
            The content as bytes.
        """
        ...
    
    @abstractmethod
    def as_json(self) -> Dict[str, Any]:
        """Get the content as JSON.
        
        Returns:
            The content as a JSON object.
            
        Raises:
            ValueError: If the content is not valid JSON.
        """
        ...


class Resource(Protocol):
    """Protocol for resources."""
    
    @property
    @abstractmethod
    def uri(self) -> URI:
        """Get the resource URI."""
        ...
    
    @property
    @abstractmethod
    def type(self) -> ResourceType:
        """Get the resource type."""
        ...
    
    @property
    @abstractmethod
    def metadata(self) -> ResourceMetadata:
        """Get the resource metadata."""
        ...
    
    @property
    @abstractmethod
    def content(self) -> ResourceContent:
        """Get the resource content."""
        ...
    
    @abstractmethod
    def update_content(self, content: Union[str, bytes, Dict[str, Any]]) -> None:
        """Update the resource content.
        
        Args:
            content: The new content.
            
        Raises:
            ValueError: If the content is invalid.
        """
        ...
    
    @abstractmethod
    def update_metadata(self, metadata: Dict[str, Any]) -> None:
        """Update the resource metadata.
        
        Args:
            metadata: The new metadata.
        """
        ...


class ResourceReference(Protocol):
    """Protocol for resource references."""
    
    @property
    @abstractmethod
    def source_uri(self) -> URI:
        """Get the source URI."""
        ...
    
    @property
    @abstractmethod
    def target_uri(self) -> URI:
        """Get the target URI."""
        ...
    
    @property
    @abstractmethod
    def reference_type(self) -> str:
        """Get the reference type."""
        ...
    
    @property
    @abstractmethod
    def label(self) -> Optional[str]:
        """Get the reference label."""
        ...
    
    @property
    @abstractmethod
    def attributes(self) -> Dict[str, Any]:
        """Get all reference attributes."""
        ...
    
    @abstractmethod
    def get_attribute(self, name: str, default: Any = None) -> Any:
        """Get a reference attribute.
        
        Args:
            name: The attribute name.
            default: The default value to return if the attribute does not exist.
            
        Returns:
            The attribute value, or the default value if the attribute does not exist.
        """
        ...


class ResourceRegistry(Protocol):
    """Protocol for resource registries."""
    
    @abstractmethod
    def register(self, resource: Resource) -> None:
        """Register a resource.
        
        Args:
            resource: The resource to register.
            
        Raises:
            ValueError: If a resource with the same URI already exists.
        """
        ...
    
    @abstractmethod
    def unregister(self, uri: Union[str, URI]) -> None:
        """Unregister a resource.
        
        Args:
            uri: The URI of the resource to unregister.
            
        Raises:
            ValueError: If the resource does not exist.
        """
        ...
    
    @abstractmethod
    def get(self, uri: Union[str, URI]) -> Resource:
        """Get a resource by URI.
        
        Args:
            uri: The URI of the resource to get.
            
        Returns:
            The resource.
            
        Raises:
            ValueError: If the resource does not exist.
        """
        ...
    
    @abstractmethod
    def find(self, query: str) -> List[Resource]:
        """Find resources by query.
        
        Args:
            query: The query to search for.
            
        Returns:
            A list of matching resources.
        """
        ...
    
    @abstractmethod
    def add_reference(self, reference: ResourceReference) -> None:
        """Add a resource reference.
        
        Args:
            reference: The reference to add.
        """
        ...
    
    @abstractmethod
    def remove_reference(self, source_uri: Union[str, URI], target_uri: Union[str, URI]) -> None:
        """Remove a resource reference.
        
        Args:
            source_uri: The source URI.
            target_uri: The target URI.
            
        Raises:
            ValueError: If the reference does not exist.
        """
        ...
    
    @abstractmethod
    def get_references(self, uri: Union[str, URI], direction: str = "outgoing") -> List[ResourceReference]:
        """Get references for a resource.
        
        Args:
            uri: The URI of the resource.
            direction: The reference direction, either "outgoing" or "incoming".
            
        Returns:
            A list of references.
            
        Raises:
            ValueError: If the direction is invalid.
        """
        ...
