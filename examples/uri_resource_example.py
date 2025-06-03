#!/usr/bin/env python3
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
"""Example of using URI and resource implementations."""

import sys
import os
from pathlib import Path

# Add the src directory to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from textcase.core.uri import (
    URIImpl, ResourceTypeImpl, URIResolverImpl, 
    get_default_uri_resolver, parse_uri, create_uri
)
from textcase.core.resource import (
    ResourceMetadataImpl, ResourceContentImpl, ResourceImpl, ResourceReferenceImpl,
    get_default_resource_registry, create_resource, create_reference
)


def demonstrate_uri_usage():
    """Demonstrate URI usage."""
    print("\n=== URI Usage ===")
    
    # Create a URI
    uri = create_uri("REQ", "001", "背景/LLM支持", "item")
    print(f"Created URI: {uri}")
    print(f"Prefix: {uri.prefix}")
    print(f"ID: {uri.id}")
    print(f"Heading path: {uri.heading_path}")
    print(f"Resource type: {uri.resource_type}")
    print(f"Normalized: {uri.normalized}")
    
    # Parse a URI string
    uri_string = "SRC/textcase/core/vfs.py/get_default_vfs#code"
    parsed_uri = parse_uri(uri_string)
    print(f"\nParsed URI: {parsed_uri}")
    print(f"Is source URI: {parsed_uri.is_source_uri}")
    print(f"Is file URI: {parsed_uri.is_file_uri}")
    print(f"Is document URI: {parsed_uri.is_document_uri}")
    
    # Create a new URI with a different resource type
    new_uri = parsed_uri.with_resource_type("line")
    print(f"\nNew URI with different resource type: {new_uri}")
    
    # Get available resource types
    uri_resolver = get_default_uri_resolver()
    resource_types = uri_resolver.get_resource_types()
    print("\nAvailable resource types:")
    for name, resource_type in resource_types.items():
        print(f"  {name}: {resource_type.fragment} - {resource_type.description}")


def demonstrate_resource_usage():
    """Demonstrate resource usage."""
    print("\n=== Resource Usage ===")
    
    # Create a resource
    uri = create_uri("REQ", "001", "背景/LLM支持", "item")
    resource = create_resource(
        uri=uri,
        type_name="item",
        title="LLM支持需求",
        content="系统应该支持与大型语言模型集成，提供智能文本处理功能。",
        description="LLM集成需求文档",
        tags=["LLM", "AI", "需求"]
    )
    
    print(f"Created resource: {resource.uri}")
    print(f"Title: {resource.metadata.title}")
    print(f"Description: {resource.metadata.description}")
    print(f"Tags: {resource.metadata.tags}")
    print(f"Content: {resource.content.as_text()}")
    
    # Create another resource
    uri2 = create_uri("SRC", "textcase/core/llm.py", "", "code")
    resource2 = create_resource(
        uri=uri2,
        type_name="code",
        title="LLM集成代码",
        content="def integrate_llm():\n    # LLM集成代码\n    pass",
        description="LLM集成的源代码实现",
        tags=["LLM", "源码", "实现"],
        content_type="text/x-python"
    )
    
    # Register resources
    registry = get_default_resource_registry()
    registry.register(resource)
    registry.register(resource2)
    
    # Create a reference between resources
    reference = create_reference(
        source_uri=uri,
        target_uri=uri2,
        reference_type="implements",
        label="实现"
    )
    
    registry.add_reference(reference)
    
    # Get references
    outgoing_refs = registry.get_references(uri, "outgoing")
    print("\nOutgoing references from REQ001:")
    for ref in outgoing_refs:
        print(f"  {ref.source_uri} -> {ref.target_uri} ({ref.reference_type})")
    
    # Find resources
    found_resources = registry.find("LLM")
    print("\nResources matching 'LLM':")
    for res in found_resources:
        print(f"  {res.uri}: {res.metadata.title}")


def main():
    """Main function."""
    print("URI and Resource Example")
    print("=======================")
    
    demonstrate_uri_usage()
    demonstrate_resource_usage()


if __name__ == "__main__":
    main()
