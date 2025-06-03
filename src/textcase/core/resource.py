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
"""Resource implementation for textcase."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Union, cast

from textcase.protocol.resource import (
    Resource, ResourceMetadata, ResourceContent, ResourceReference, ResourceRegistry
)
from textcase.protocol.uri import URI, ResourceType, URIResolver
from textcase.core.uri import URIImpl, ResourceTypeImpl, get_default_uri_resolver


class ResourceMetadataImpl:
    """Implementation of ResourceMetadata protocol."""
    
    def __init__(self, 
                title: str, 
                description: Optional[str] = None,
                tags: Optional[List[str]] = None,
                created_at: Optional[str] = None,
                updated_at: Optional[str] = None,
                attributes: Optional[Dict[str, Any]] = None):
        """Initialize resource metadata.
        
        Args:
            title: The resource title.
            description: Optional resource description.
            tags: Optional resource tags.
            created_at: Optional resource creation time.
            updated_at: Optional resource last update time.
            attributes: Optional resource attributes.
        """
        self._title = title
        self._description = description
        self._tags = tags or []
        self._created_at = created_at or datetime.now().isoformat()
        self._updated_at = updated_at or self._created_at
        self._attributes = attributes or {}
    
    @property
    def title(self) -> str:
        """Get the resource title."""
        return self._title
    
    @property
    def description(self) -> Optional[str]:
        """Get the resource description."""
        return self._description
    
    @property
    def tags(self) -> List[str]:
        """Get the resource tags."""
        return self._tags.copy()
    
    @property
    def created_at(self) -> Optional[str]:
        """Get the resource creation time."""
        return self._created_at
    
    @property
    def updated_at(self) -> Optional[str]:
        """Get the resource last update time."""
        return self._updated_at
    
    @property
    def attributes(self) -> Dict[str, Any]:
        """Get all resource attributes."""
        return self._attributes.copy()
    
    def get_attribute(self, name: str, default: Any = None) -> Any:
        """Get a resource attribute."""
        return self._attributes.get(name, default)
    
    def set_attribute(self, name: str, value: Any) -> None:
        """Set a resource attribute."""
        self._attributes[name] = value
        self._updated_at = datetime.now().isoformat()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert the metadata to a dictionary."""
        return {
            "title": self._title,
            "description": self._description,
            "tags": self._tags,
            "created_at": self._created_at,
            "updated_at": self._updated_at,
            "attributes": self._attributes
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> ResourceMetadataImpl:
        """Create metadata from a dictionary."""
        return cls(
            title=data.get("title", ""),
            description=data.get("description"),
            tags=data.get("tags", []),
            created_at=data.get("created_at"),
            updated_at=data.get("updated_at"),
            attributes=data.get("attributes", {})
        )


class ResourceContentImpl:
    """Implementation of ResourceContent protocol."""
    
    def __init__(self, 
                content: Union[str, bytes, Dict[str, Any]],
                content_type: str = "text/plain",
                encoding: Optional[str] = "utf-8"):
        """Initialize resource content.
        
        Args:
            content: The content data.
            content_type: The content type.
            encoding: The content encoding.
        """
        self._content_type = content_type
        self._encoding = encoding
        
        # Store content based on its type
        if isinstance(content, bytes):
            self._bytes_content = content
            self._text_content = None
            self._json_content = None
        elif isinstance(content, str):
            self._bytes_content = None
            self._text_content = content
            self._json_content = None
        elif isinstance(content, dict):
            self._bytes_content = None
            self._text_content = None
            self._json_content = content
        else:
            raise ValueError(f"Unsupported content type: {type(content)}")
    
    @property
    def content_type(self) -> str:
        """Get the content type."""
        return self._content_type
    
    @property
    def encoding(self) -> Optional[str]:
        """Get the content encoding."""
        return self._encoding
    
    def as_text(self) -> str:
        """Get the content as text."""
        if self._text_content is not None:
            return self._text_content
        
        if self._bytes_content is not None:
            if self._encoding:
                return self._bytes_content.decode(self._encoding)
            else:
                return self._bytes_content.decode("utf-8")
        
        if self._json_content is not None:
            return json.dumps(self._json_content, ensure_ascii=False)
        
        raise ValueError("Cannot convert content to text")
    
    def as_bytes(self) -> bytes:
        """Get the content as bytes."""
        if self._bytes_content is not None:
            return self._bytes_content
        
        if self._text_content is not None:
            if self._encoding:
                return self._text_content.encode(self._encoding)
            else:
                return self._text_content.encode("utf-8")
        
        if self._json_content is not None:
            text = json.dumps(self._json_content, ensure_ascii=False)
            if self._encoding:
                return text.encode(self._encoding)
            else:
                return text.encode("utf-8")
        
        raise ValueError("Cannot convert content to bytes")
    
    def as_json(self) -> Dict[str, Any]:
        """Get the content as JSON."""
        if self._json_content is not None:
            return self._json_content
        
        if self._text_content is not None:
            try:
                return json.loads(self._text_content)
            except json.JSONDecodeError:
                raise ValueError("Content is not valid JSON")
        
        if self._bytes_content is not None:
            try:
                if self._encoding:
                    text = self._bytes_content.decode(self._encoding)
                else:
                    text = self._bytes_content.decode("utf-8")
                return json.loads(text)
            except (UnicodeDecodeError, json.JSONDecodeError):
                raise ValueError("Content is not valid JSON")
        
        raise ValueError("Cannot convert content to JSON")


class ResourceImpl:
    """Implementation of Resource protocol."""
    
    def __init__(self, 
                uri: URI,
                type: ResourceType,
                metadata: ResourceMetadata,
                content: ResourceContent):
        """Initialize a resource.
        
        Args:
            uri: The resource URI.
            type: The resource type.
            metadata: The resource metadata.
            content: The resource content.
        """
        self._uri = uri
        self._type = type
        self._metadata = metadata
        self._content = content
    
    @property
    def uri(self) -> URI:
        """Get the resource URI."""
        return self._uri
    
    @property
    def type(self) -> ResourceType:
        """Get the resource type."""
        return self._type
    
    @property
    def metadata(self) -> ResourceMetadata:
        """Get the resource metadata."""
        return self._metadata
    
    @property
    def content(self) -> ResourceContent:
        """Get the resource content."""
        return self._content
    
    def update_content(self, content: Union[str, bytes, Dict[str, Any]]) -> None:
        """Update the resource content."""
        self._content = ResourceContentImpl(
            content=content,
            content_type=self._content.content_type,
            encoding=self._content.encoding
        )
    
    def update_metadata(self, metadata: Dict[str, Any]) -> None:
        """Update the resource metadata."""
        if isinstance(self._metadata, ResourceMetadataImpl):
            for key, value in metadata.items():
                self._metadata.set_attribute(key, value)
        else:
            # If the metadata is not a ResourceMetadataImpl, create a new one
            self._metadata = ResourceMetadataImpl.from_dict(metadata)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert the resource to a dictionary."""
        return {
            "uri": str(self._uri),
            "type": self._type.name,
            "metadata": self._metadata.to_dict() if hasattr(self._metadata, "to_dict") else {},
            "content": self._content.as_text()
        }


class ResourceReferenceImpl:
    """Implementation of ResourceReference protocol."""
    
    def __init__(self, 
                source_uri: URI,
                target_uri: URI,
                reference_type: str,
                label: Optional[str] = None,
                attributes: Optional[Dict[str, Any]] = None):
        """Initialize a resource reference.
        
        Args:
            source_uri: The source URI.
            target_uri: The target URI.
            reference_type: The reference type.
            label: Optional reference label.
            attributes: Optional reference attributes.
        """
        self._source_uri = source_uri
        self._target_uri = target_uri
        self._reference_type = reference_type
        self._label = label
        self._attributes = attributes or {}
    
    @property
    def source_uri(self) -> URI:
        """Get the source URI."""
        return self._source_uri
    
    @property
    def target_uri(self) -> URI:
        """Get the target URI."""
        return self._target_uri
    
    @property
    def reference_type(self) -> str:
        """Get the reference type."""
        return self._reference_type
    
    @property
    def label(self) -> Optional[str]:
        """Get the reference label."""
        return self._label
    
    @property
    def attributes(self) -> Dict[str, Any]:
        """Get all reference attributes."""
        return self._attributes.copy()
    
    def get_attribute(self, name: str, default: Any = None) -> Any:
        """Get a reference attribute."""
        return self._attributes.get(name, default)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert the reference to a dictionary."""
        return {
            "source_uri": str(self._source_uri),
            "target_uri": str(self._target_uri),
            "reference_type": self._reference_type,
            "label": self._label,
            "attributes": self._attributes
        }


class ResourceRegistryImpl:
    """Implementation of ResourceRegistry protocol."""
    
    def __init__(self, uri_resolver: Optional[URIResolver] = None):
        """Initialize a resource registry.
        
        Args:
            uri_resolver: Optional URI resolver to use.
        """
        self._resources: Dict[str, Resource] = {}
        self._outgoing_references: Dict[str, List[ResourceReference]] = {}
        self._incoming_references: Dict[str, List[ResourceReference]] = {}
        self._uri_resolver = uri_resolver or get_default_uri_resolver()
    
    def register(self, resource: Resource) -> None:
        """Register a resource."""
        uri_str = str(resource.uri)
        
        if uri_str in self._resources:
            raise ValueError(f"Resource with URI '{uri_str}' already exists")
        
        self._resources[uri_str] = resource
        
        # Initialize reference lists
        if uri_str not in self._outgoing_references:
            self._outgoing_references[uri_str] = []
        
        if uri_str not in self._incoming_references:
            self._incoming_references[uri_str] = []
    
    def unregister(self, uri: Union[str, URI]) -> None:
        """Unregister a resource."""
        uri_str = str(uri)
        
        if uri_str not in self._resources:
            raise ValueError(f"Resource with URI '{uri_str}' does not exist")
        
        # Remove the resource
        del self._resources[uri_str]
        
        # Remove outgoing references
        if uri_str in self._outgoing_references:
            for ref in self._outgoing_references[uri_str]:
                target_uri_str = str(ref.target_uri)
                if target_uri_str in self._incoming_references:
                    self._incoming_references[target_uri_str] = [
                        r for r in self._incoming_references[target_uri_str]
                        if str(r.source_uri) != uri_str
                    ]
            
            del self._outgoing_references[uri_str]
        
        # Remove incoming references
        if uri_str in self._incoming_references:
            for ref in self._incoming_references[uri_str]:
                source_uri_str = str(ref.source_uri)
                if source_uri_str in self._outgoing_references:
                    self._outgoing_references[source_uri_str] = [
                        r for r in self._outgoing_references[source_uri_str]
                        if str(r.target_uri) != uri_str
                    ]
            
            del self._incoming_references[uri_str]
    
    def get(self, uri: Union[str, URI]) -> Resource:
        """Get a resource by URI."""
        uri_str = str(uri)
        
        if uri_str not in self._resources:
            raise ValueError(f"Resource with URI '{uri_str}' does not exist")
        
        return self._resources[uri_str]
    
    def find(self, query: str) -> List[Resource]:
        """Find resources by query."""
        # This is a simple implementation that just checks if the query
        # is a substring of the resource URI or title
        results = []
        
        for resource in self._resources.values():
            uri_str = str(resource.uri)
            title = resource.metadata.title
            
            if query.lower() in uri_str.lower() or query.lower() in title.lower():
                results.append(resource)
        
        return results
    
    def add_reference(self, reference: ResourceReference) -> None:
        """Add a resource reference."""
        source_uri_str = str(reference.source_uri)
        target_uri_str = str(reference.target_uri)
        
        # Ensure the source and target resources exist
        if source_uri_str not in self._resources:
            raise ValueError(f"Source resource with URI '{source_uri_str}' does not exist")
        
        if target_uri_str not in self._resources:
            raise ValueError(f"Target resource with URI '{target_uri_str}' does not exist")
        
        # Initialize reference lists if needed
        if source_uri_str not in self._outgoing_references:
            self._outgoing_references[source_uri_str] = []
        
        if target_uri_str not in self._incoming_references:
            self._incoming_references[target_uri_str] = []
        
        # Add the reference
        self._outgoing_references[source_uri_str].append(reference)
        self._incoming_references[target_uri_str].append(reference)
    
    def remove_reference(self, source_uri: Union[str, URI], target_uri: Union[str, URI]) -> None:
        """Remove a resource reference."""
        source_uri_str = str(source_uri)
        target_uri_str = str(target_uri)
        
        # Check if the reference exists
        if source_uri_str not in self._outgoing_references:
            raise ValueError(f"No outgoing references from '{source_uri_str}'")
        
        if target_uri_str not in self._incoming_references:
            raise ValueError(f"No incoming references to '{target_uri_str}'")
        
        # Find and remove the reference
        found = False
        
        # Remove from outgoing references
        self._outgoing_references[source_uri_str] = [
            ref for ref in self._outgoing_references[source_uri_str]
            if str(ref.target_uri) != target_uri_str or found or (found := True, False)[1]
        ]
        
        # Reset found flag
        found = False
        
        # Remove from incoming references
        self._incoming_references[target_uri_str] = [
            ref for ref in self._incoming_references[target_uri_str]
            if str(ref.source_uri) != source_uri_str or found or (found := True, False)[1]
        ]
        
        if not found:
            raise ValueError(f"No reference from '{source_uri_str}' to '{target_uri_str}'")
    
    def get_references(self, uri: Union[str, URI], direction: str = "outgoing") -> List[ResourceReference]:
        """Get references for a resource."""
        uri_str = str(uri)
        
        if direction == "outgoing":
            return self._outgoing_references.get(uri_str, [])
        elif direction == "incoming":
            return self._incoming_references.get(uri_str, [])
        else:
            raise ValueError(f"Invalid direction: {direction}")


# Create a singleton instance of the resource registry
default_resource_registry = ResourceRegistryImpl()


def get_default_resource_registry() -> ResourceRegistry:
    """Get the default resource registry."""
    return default_resource_registry


def create_resource(uri: Union[str, URI],
                   type_name: str,
                   title: str,
                   content: Union[str, bytes, Dict[str, Any]],
                   description: Optional[str] = None,
                   tags: Optional[List[str]] = None,
                   content_type: str = "text/plain",
                   encoding: Optional[str] = "utf-8") -> Resource:
    """Create a new resource.
    
    Args:
        uri: The resource URI.
        type_name: The resource type name.
        title: The resource title.
        content: The resource content.
        description: Optional resource description.
        tags: Optional resource tags.
        content_type: The content type.
        encoding: The content encoding.
        
    Returns:
        A new Resource instance.
        
    Raises:
        ValueError: If the resource type does not exist.
    """
    uri_resolver = get_default_uri_resolver()
    
    # Parse the URI if it's a string
    if isinstance(uri, str):
        uri = uri_resolver.parse(uri)
    
    # Get the resource type
    resource_types = uri_resolver.get_resource_types()
    if type_name not in resource_types:
        raise ValueError(f"Resource type '{type_name}' does not exist")
    
    resource_type = resource_types[type_name]
    
    # Create the resource
    return ResourceImpl(
        uri=uri,
        type=resource_type,
        metadata=ResourceMetadataImpl(
            title=title,
            description=description,
            tags=tags
        ),
        content=ResourceContentImpl(
            content=content,
            content_type=content_type,
            encoding=encoding
        )
    )


def create_reference(source_uri: Union[str, URI],
                    target_uri: Union[str, URI],
                    reference_type: str,
                    label: Optional[str] = None,
                    attributes: Optional[Dict[str, Any]] = None) -> ResourceReference:
    """Create a new resource reference.
    
    Args:
        source_uri: The source URI.
        target_uri: The target URI.
        reference_type: The reference type.
        label: Optional reference label.
        attributes: Optional reference attributes.
        
    Returns:
        A new ResourceReference instance.
    """
    uri_resolver = get_default_uri_resolver()
    
    # Parse the URIs if they're strings
    if isinstance(source_uri, str):
        source_uri = uri_resolver.parse(source_uri)
    
    if isinstance(target_uri, str):
        target_uri = uri_resolver.parse(target_uri)
    
    return ResourceReferenceImpl(
        source_uri=source_uri,
        target_uri=target_uri,
        reference_type=reference_type,
        label=label,
        attributes=attributes
    )
