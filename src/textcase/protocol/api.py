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
"""Web API protocol and related types."""

from __future__ import annotations

from abc import abstractmethod
from pathlib import Path
from typing import Any, Dict, List, Optional, Protocol, TypeVar, Union, Callable

__all__ = [
    'APIServer',
    'APIRoute',
    'APIHandler',
    'APIResponse',
    'APIRequest',
    'APIConfig',
]


class APIRequest(Protocol):
    """Protocol for API requests."""
    
    @property
    @abstractmethod
    def path(self) -> str:
        """Get the request path."""
        ...
    
    @property
    @abstractmethod
    def method(self) -> str:
        """Get the HTTP method."""
        ...
    
    @property
    @abstractmethod
    def headers(self) -> Dict[str, str]:
        """Get the request headers."""
        ...
    
    @property
    @abstractmethod
    def query_params(self) -> Dict[str, str]:
        """Get the query parameters."""
        ...
    
    @abstractmethod
    async def json(self) -> Dict[str, Any]:
        """Get the request body as JSON."""
        ...
    
    @abstractmethod
    async def text(self) -> str:
        """Get the request body as text."""
        ...
    
    @abstractmethod
    async def form(self) -> Dict[str, str]:
        """Get the request body as form data."""
        ...


class APIResponse(Protocol):
    """Protocol for API responses."""
    
    @property
    @abstractmethod
    def status_code(self) -> int:
        """Get the HTTP status code."""
        ...
    
    @property
    @abstractmethod
    def headers(self) -> Dict[str, str]:
        """Get the response headers."""
        ...
    
    @property
    @abstractmethod
    def body(self) -> Union[str, bytes, Dict[str, Any], List[Any]]:
        """Get the response body."""
        ...
    
    @abstractmethod
    def set_status_code(self, status_code: int) -> None:
        """Set the HTTP status code.
        
        Args:
            status_code: The HTTP status code to set.
        """
        ...
    
    @abstractmethod
    def set_header(self, name: str, value: str) -> None:
        """Set a response header.
        
        Args:
            name: The header name.
            value: The header value.
        """
        ...
    
    @abstractmethod
    def set_body(self, body: Union[str, bytes, Dict[str, Any], List[Any]]) -> None:
        """Set the response body.
        
        Args:
            body: The response body to set.
        """
        ...
    
    @classmethod
    @abstractmethod
    def json(cls, data: Union[Dict[str, Any], List[Any]], status_code: int = 200) -> APIResponse:
        """Create a JSON response.
        
        Args:
            data: The JSON data to return.
            status_code: The HTTP status code.
            
        Returns:
            A new APIResponse with the JSON data.
        """
        ...
    
    @classmethod
    @abstractmethod
    def text(cls, text: str, status_code: int = 200) -> APIResponse:
        """Create a text response.
        
        Args:
            text: The text to return.
            status_code: The HTTP status code.
            
        Returns:
            A new APIResponse with the text.
        """
        ...
    
    @classmethod
    @abstractmethod
    def error(cls, message: str, status_code: int = 400) -> APIResponse:
        """Create an error response.
        
        Args:
            message: The error message.
            status_code: The HTTP status code.
            
        Returns:
            A new APIResponse with the error message.
        """
        ...


# Type alias for API handler functions
APIHandler = Callable[[APIRequest], Union[APIResponse, Dict[str, Any], str, bytes, None]]


class APIRoute(Protocol):
    """Protocol for API routes."""
    
    @property
    @abstractmethod
    def path(self) -> str:
        """Get the route path."""
        ...
    
    @property
    @abstractmethod
    def method(self) -> str:
        """Get the HTTP method."""
        ...
    
    @property
    @abstractmethod
    def handler(self) -> APIHandler:
        """Get the route handler."""
        ...
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Get the route name."""
        ...
    
    @property
    @abstractmethod
    def description(self) -> str:
        """Get the route description."""
        ...


class APIConfig(Protocol):
    """Protocol for API server configuration."""
    
    @property
    @abstractmethod
    def host(self) -> str:
        """Get the server host."""
        ...
    
    @property
    @abstractmethod
    def port(self) -> int:
        """Get the server port."""
        ...
    
    @property
    @abstractmethod
    def debug(self) -> bool:
        """Get the debug flag."""
        ...
    
    @property
    @abstractmethod
    def static_dir(self) -> Optional[Path]:
        """Get the static files directory."""
        ...
    
    @property
    @abstractmethod
    def static_url_path(self) -> str:
        """Get the static files URL path."""
        ...
    
    @property
    @abstractmethod
    def api_prefix(self) -> str:
        """Get the API URL prefix."""
        ...
    
    @property
    @abstractmethod
    def enable_docs(self) -> bool:
        """Get the enable docs flag."""
        ...
    
    @property
    @abstractmethod
    def cors_origins(self) -> List[str]:
        """Get the CORS allowed origins."""
        ...
    
    @abstractmethod
    def to_dict(self) -> Dict[str, Any]:
        """Convert the configuration to a dictionary.
        
        Returns:
            A dictionary representation of the configuration.
        """
        ...
    
    @classmethod
    @abstractmethod
    def from_dict(cls, data: Dict[str, Any]) -> APIConfig:
        """Create a configuration from a dictionary.
        
        Args:
            data: The dictionary to create the configuration from.
            
        Returns:
            A new APIConfig instance.
        """
        ...


class APIServer(Protocol):
    """Protocol for API servers."""
    
    @property
    @abstractmethod
    def config(self) -> APIConfig:
        """Get the server configuration."""
        ...
    
    @property
    @abstractmethod
    def routes(self) -> List[APIRoute]:
        """Get all registered routes."""
        ...
    
    @abstractmethod
    def add_route(self, 
                 path: str, 
                 handler: APIHandler, 
                 methods: Union[str, List[str]] = "GET",
                 name: Optional[str] = None,
                 description: Optional[str] = None) -> None:
        """Add a route to the server.
        
        Args:
            path: The route path.
            handler: The route handler.
            methods: The HTTP methods to handle.
            name: Optional route name.
            description: Optional route description.
        """
        ...
    
    @abstractmethod
    def mount_static(self, path: str, directory: Union[str, Path]) -> None:
        """Mount a static directory.
        
        Args:
            path: The URL path to mount the directory at.
            directory: The directory to mount.
        """
        ...
    
    @abstractmethod
    async def start(self) -> None:
        """Start the server."""
        ...
    
    @abstractmethod
    async def stop(self) -> None:
        """Stop the server."""
        ...
