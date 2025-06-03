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
"""URI implementation for resource location."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Union, cast

from textcase.protocol.uri import URI, URIResolver, ResourceType


@dataclass
class ResourceTypeImpl:
    """Implementation of ResourceType protocol."""
    
    _name: str
    _fragment: str
    _description: str
    
    @property
    def name(self) -> str:
        """Get the name of the resource type."""
        return self._name
    
    @property
    def fragment(self) -> str:
        """Get the fragment identifier for this resource type."""
        return self._fragment
    
    @property
    def description(self) -> str:
        """Get the description of this resource type."""
        return self._description


class URIImpl:
    """Implementation of URI protocol."""
    
    def __init__(self, 
                prefix: str, 
                id: str, 
                heading_path: str = "", 
                resource_type: Optional[str] = None,
                original: Optional[str] = None):
        """Initialize a URI.
        
        Args:
            prefix: The module prefix part of the URI.
            id: The ID part of the URI.
            heading_path: The heading path part of the URI.
            resource_type: The resource type fragment of the URI.
            original: The original URI string.
        """
        self._prefix = prefix
        self._id = id
        self._heading_path = heading_path
        self._resource_type = resource_type
        self._original = original or self._build_uri()
    
    @property
    def original(self) -> str:
        """Get the original URI string."""
        return self._original
    
    @property
    def prefix(self) -> str:
        """Get the module prefix part of the URI."""
        return self._prefix
    
    @property
    def id(self) -> str:
        """Get the ID part of the URI."""
        return self._id
    
    @property
    def heading_path(self) -> str:
        """Get the heading path part of the URI."""
        return self._heading_path
    
    @property
    def resource_type(self) -> Optional[str]:
        """Get the resource type fragment of the URI."""
        return self._resource_type
    
    @property
    def normalized(self) -> str:
        """Get the normalized form of the URI."""
        return self._build_uri()
    
    @property
    def is_source_uri(self) -> bool:
        """Check if this is a source code URI."""
        return self._prefix.upper() == "SRC"
    
    @property
    def is_file_uri(self) -> bool:
        """Check if this is a file URI."""
        # A file URI is a source URI that points to a file, not a code element
        return self.is_source_uri and "/" not in self._id
    
    @property
    def is_document_uri(self) -> bool:
        """Check if this is a document URI."""
        return not self.is_source_uri
    
    def with_resource_type(self, resource_type: str) -> URI:
        """Create a new URI with the specified resource type."""
        return URIImpl(
            prefix=self._prefix,
            id=self._id,
            heading_path=self._heading_path,
            resource_type=resource_type
        )
    
    def with_heading_path(self, heading_path: str) -> URI:
        """Create a new URI with the specified heading path."""
        return URIImpl(
            prefix=self._prefix,
            id=self._id,
            heading_path=heading_path,
            resource_type=self._resource_type
        )
    
    def with_id(self, id: str) -> URI:
        """Create a new URI with the specified ID."""
        return URIImpl(
            prefix=self._prefix,
            id=id,
            heading_path=self._heading_path,
            resource_type=self._resource_type
        )
    
    def with_prefix(self, prefix: str) -> URI:
        """Create a new URI with the specified prefix."""
        return URIImpl(
            prefix=prefix,
            id=self._id,
            heading_path=self._heading_path,
            resource_type=self._resource_type
        )
    
    def _build_uri(self) -> str:
        """Build the URI string from components."""
        uri = f"{self._prefix}{self._id}"
        
        if self._heading_path:
            uri += f"/{self._heading_path}"
        
        if self._resource_type:
            uri += f"#{self._resource_type}"
        
        return uri
    
    def __str__(self) -> str:
        """Convert the URI to a string."""
        return self.normalized
    
    def __eq__(self, other: object) -> bool:
        """Check if this URI is equal to another URI."""
        if not isinstance(other, URIImpl):
            return False
        
        return (
            self._prefix == other._prefix and
            self._id == other._id and
            self._heading_path == other._heading_path and
            self._resource_type == other._resource_type
        )
    
    def __hash__(self) -> int:
        """Get the hash of this URI."""
        return hash((self._prefix, self._id, self._heading_path, self._resource_type))


class URIResolverImpl:
    """Implementation of URIResolver protocol."""
    
    # Regular expression for parsing URIs
    # Format: {prefix}{id}/{heading_path}#{resource_type}
    _URI_REGEX = re.compile(
        r"^(?P<prefix>[A-Za-z]+)(?P<id>[0-9]+)(?:/(?P<heading_path>[^#]*))?(?:#(?P<resource_type>[^/]*))?$"
    )
    
    # Regular expression for parsing source URIs
    # Format: SRC/{path/to/file.py}/{element}
    _SOURCE_URI_REGEX = re.compile(
        r"^(?P<prefix>SRC)(?:/(?P<path>[^#]*))?(?:#(?P<resource_type>[^/]*))?$"
    )
    
    def __init__(self):
        """Initialize a URI resolver."""
        self._resource_types: Dict[str, ResourceType] = {}
        
        # Register default resource types
        self._register_default_resource_types()
    
    def _register_default_resource_types(self) -> None:
        """Register default resource types."""
        default_types = [
            ResourceTypeImpl("item", "item", "Document item"),
            ResourceTypeImpl("meta", "meta", "Document metadata"),
            ResourceTypeImpl("link", "link", "Document link"),
            ResourceTypeImpl("code", "code", "Source code"),
            ResourceTypeImpl("file", "file", "File"),
            ResourceTypeImpl("line", "L", "Line in a file"),
        ]
        
        for resource_type in default_types:
            self.register_resource_type(resource_type)
    
    def parse(self, uri_string: str) -> URI:
        """Parse a URI string into a URI object."""
        # Check if this is a source URI
        if uri_string.startswith("SRC/"):
            return self._parse_source_uri(uri_string)
        
        # Otherwise, parse as a document URI
        match = self._URI_REGEX.match(uri_string)
        if not match:
            raise ValueError(f"Invalid URI: {uri_string}")
        
        prefix = match.group("prefix")
        id = match.group("id")
        heading_path = match.group("heading_path") or ""
        resource_type = match.group("resource_type")
        
        return URIImpl(
            prefix=prefix,
            id=id,
            heading_path=heading_path,
            resource_type=resource_type,
            original=uri_string
        )
    
    def _parse_source_uri(self, uri_string: str) -> URI:
        """Parse a source URI string into a URI object."""
        match = self._SOURCE_URI_REGEX.match(uri_string)
        if not match:
            raise ValueError(f"Invalid source URI: {uri_string}")
        
        prefix = match.group("prefix")
        path = match.group("path") or ""
        resource_type = match.group("resource_type")
        
        return URIImpl(
            prefix=prefix,
            id=path,
            heading_path="",
            resource_type=resource_type,
            original=uri_string
        )
    
    def resolve(self, uri: Union[str, URI]) -> Any:
        """Resolve a URI to a resource."""
        if isinstance(uri, str):
            uri = self.parse(uri)
        
        # This is a placeholder implementation
        # In a real implementation, this would resolve the URI to a resource
        # For now, we just return the URI itself
        return uri
    
    def get_resource_types(self) -> Dict[str, ResourceType]:
        """Get all registered resource types."""
        return self._resource_types.copy()
    
    def register_resource_type(self, resource_type: ResourceType) -> None:
        """Register a new resource type."""
        name = resource_type.name
        fragment = resource_type.fragment
        
        # Check if a resource type with the same name already exists
        if name in self._resource_types:
            raise ValueError(f"Resource type with name '{name}' already exists")
        
        # Check if a resource type with the same fragment already exists
        for rt in self._resource_types.values():
            if rt.fragment == fragment:
                raise ValueError(f"Resource type with fragment '{fragment}' already exists")
        
        self._resource_types[name] = resource_type
    
    def create_uri(self, 
                  prefix: str, 
                  id: str, 
                  heading_path: Optional[str] = None, 
                  resource_type: Optional[str] = None) -> URI:
        """Create a new URI with the specified components."""
        return URIImpl(
            prefix=prefix,
            id=id,
            heading_path=heading_path or "",
            resource_type=resource_type
        )


# Create a singleton instance of the URI resolver
default_uri_resolver = URIResolverImpl()


def get_default_uri_resolver() -> URIResolver:
    """Get the default URI resolver."""
    return default_uri_resolver


def parse_uri(uri_string: str) -> URI:
    """Parse a URI string into a URI object.
    
    Args:
        uri_string: The URI string to parse.
        
    Returns:
        A URI object.
        
    Raises:
        ValueError: If the URI string is invalid.
    """
    return default_uri_resolver.parse(uri_string)


def create_uri(prefix: str, 
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
    return default_uri_resolver.create_uri(
        prefix=prefix,
        id=id,
        heading_path=heading_path,
        resource_type=resource_type
    )
