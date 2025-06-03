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
"""API server implementation for textcase."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Union, cast

from textcase.protocol.api import (
    APIServer, APIRoute, APIHandler, APIRequest, APIResponse, APIConfig
)

# Setup logging
logger = logging.getLogger(__name__)


@dataclass
class APIConfigImpl:
    """Implementation of APIConfig protocol."""
    
    host: str = "127.0.0.1"
    port: int = 8000
    debug: bool = False
    static_dir: Optional[Path] = None
    static_url_path: str = "/static"
    api_prefix: str = "/api"
    enable_docs: bool = True
    cors_origins: List[str] = field(default_factory=lambda: ["*"])
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert the configuration to a dictionary."""
        return {
            "host": self.host,
            "port": self.port,
            "debug": self.debug,
            "static_dir": str(self.static_dir) if self.static_dir else None,
            "static_url_path": self.static_url_path,
            "api_prefix": self.api_prefix,
            "enable_docs": self.enable_docs,
            "cors_origins": self.cors_origins
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> APIConfigImpl:
        """Create a configuration from a dictionary."""
        static_dir = data.get("static_dir")
        if static_dir and isinstance(static_dir, str):
            static_dir = Path(static_dir)
        
        return cls(
            host=data.get("host", "127.0.0.1"),
            port=data.get("port", 8000),
            debug=data.get("debug", False),
            static_dir=static_dir,
            static_url_path=data.get("static_url_path", "/static"),
            api_prefix=data.get("api_prefix", "/api"),
            enable_docs=data.get("enable_docs", True),
            cors_origins=data.get("cors_origins", ["*"])
        )


@dataclass
class APIRequestImpl:
    """Implementation of APIRequest protocol."""
    
    path: str
    method: str
    headers: Dict[str, str] = field(default_factory=dict)
    query_params: Dict[str, str] = field(default_factory=dict)
    _body: Optional[Union[str, bytes, Dict[str, Any]]] = None
    
    async def json(self) -> Dict[str, Any]:
        """Get the request body as JSON."""
        if isinstance(self._body, dict):
            return self._body
        
        if isinstance(self._body, str):
            return json.loads(self._body)
        
        if isinstance(self._body, bytes):
            return json.loads(self._body.decode("utf-8"))
        
        return {}
    
    async def text(self) -> str:
        """Get the request body as text."""
        if isinstance(self._body, str):
            return self._body
        
        if isinstance(self._body, bytes):
            return self._body.decode("utf-8")
        
        if isinstance(self._body, dict):
            return json.dumps(self._body)
        
        return ""
    
    async def form(self) -> Dict[str, str]:
        """Get the request body as form data."""
        if isinstance(self._body, dict):
            return {k: str(v) for k, v in self._body.items()}
        
        if isinstance(self._body, str):
            # Simple form parsing
            result = {}
            for item in self._body.split("&"):
                if "=" in item:
                    key, value = item.split("=", 1)
                    result[key] = value
            return result
        
        if isinstance(self._body, bytes):
            # Simple form parsing
            text = self._body.decode("utf-8")
            result = {}
            for item in text.split("&"):
                if "=" in item:
                    key, value = item.split("=", 1)
                    result[key] = value
            return result
        
        return {}


@dataclass
class APIResponseImpl:
    """Implementation of APIResponse protocol."""
    
    status_code: int = 200
    headers: Dict[str, str] = field(default_factory=dict)
    body: Union[str, bytes, Dict[str, Any], List[Any]] = ""
    
    def set_status_code(self, status_code: int) -> None:
        """Set the HTTP status code."""
        self.status_code = status_code
    
    def set_header(self, name: str, value: str) -> None:
        """Set a response header."""
        self.headers[name] = value
    
    def set_body(self, body: Union[str, bytes, Dict[str, Any], List[Any]]) -> None:
        """Set the response body."""
        self.body = body
    
    @classmethod
    def json(cls, data: Union[Dict[str, Any], List[Any]], status_code: int = 200) -> APIResponseImpl:
        """Create a JSON response."""
        response = cls(status_code=status_code, body=data)
        response.set_header("Content-Type", "application/json")
        return response
    
    @classmethod
    def text(cls, text: str, status_code: int = 200) -> APIResponseImpl:
        """Create a text response."""
        response = cls(status_code=status_code, body=text)
        response.set_header("Content-Type", "text/plain")
        return response
    
    @classmethod
    def error(cls, message: str, status_code: int = 400) -> APIResponseImpl:
        """Create an error response."""
        response = cls(status_code=status_code, body={"error": message})
        response.set_header("Content-Type", "application/json")
        return response


@dataclass
class APIRouteImpl:
    """Implementation of APIRoute protocol."""
    
    path: str
    method: str
    handler: APIHandler
    name: str = ""
    description: str = ""


class APIServerImpl:
    """Implementation of APIServer protocol."""
    
    def __init__(self, config: Optional[APIConfig] = None):
        """Initialize an API server.
        
        Args:
            config: Optional server configuration.
        """
        self._config = config or APIConfigImpl()
        self._routes: List[APIRoute] = []
        self._app = None  # Will be set when start() is called
    
    @property
    def config(self) -> APIConfig:
        """Get the server configuration."""
        return self._config
    
    @property
    def routes(self) -> List[APIRoute]:
        """Get all registered routes."""
        return self._routes.copy()
    
    def add_route(self, 
                 path: str, 
                 handler: APIHandler, 
                 methods: Union[str, List[str]] = "GET",
                 name: Optional[str] = None,
                 description: Optional[str] = None) -> None:
        """Add a route to the server."""
        if isinstance(methods, str):
            methods = [methods]
        
        for method in methods:
            route = APIRouteImpl(
                path=path,
                method=method,
                handler=handler,
                name=name or "",
                description=description or ""
            )
            self._routes.append(route)
    
    def mount_static(self, path: str, directory: Union[str, Path]) -> None:
        """Mount a static directory."""
        if isinstance(directory, str):
            directory = Path(directory)
        
        # Store the static directory in the config
        if isinstance(self._config, APIConfigImpl):
            self._config.static_dir = directory
            self._config.static_url_path = path
    
    async def start(self) -> None:
        """Start the server."""
        try:
            # Try to import FastAPI
            from fastapi import FastAPI, Request, Response
            from fastapi.middleware.cors import CORSMiddleware
            from fastapi.staticfiles import StaticFiles
            import uvicorn
        except ImportError:
            logger.error("FastAPI or uvicorn not installed. Please install them with: pip install fastapi uvicorn")
            return
        
        # Create the FastAPI app
        app = FastAPI(
            title="TextCase API",
            description="API for TextCase document management system",
            version="1.0.0",
            docs_url="/docs" if self._config.enable_docs else None,
            redoc_url="/redoc" if self._config.enable_docs else None,
        )
        
        # Add CORS middleware
        app.add_middleware(
            CORSMiddleware,
            allow_origins=self._config.cors_origins,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
        
        # Mount static directory if configured
        if self._config.static_dir and self._config.static_dir.exists():
            app.mount(
                self._config.static_url_path,
                StaticFiles(directory=str(self._config.static_dir)),
                name="static"
            )
        
        # Register routes
        for route in self._routes:
            # Create a FastAPI compatible handler
            async def create_handler(route: APIRoute):
                async def handler(request: Request):
                    # Convert FastAPI request to our APIRequest
                    api_request = APIRequestImpl(
                        path=str(request.url.path),
                        method=request.method,
                        headers=dict(request.headers),
                        query_params=dict(request.query_params),
                        _body=await request.body()
                    )
                    
                    # Call the route handler
                    result = route.handler(api_request)
                    
                    # Handle async result
                    if hasattr(result, "__await__"):
                        result = await result
                    
                    # Convert the result to APIResponse if needed
                    if not isinstance(result, APIResponse):
                        if isinstance(result, dict) or isinstance(result, list):
                            result = APIResponseImpl.json(result)
                        elif isinstance(result, str):
                            result = APIResponseImpl.text(result)
                        elif result is None:
                            result = APIResponseImpl.json({})
                        else:
                            result = APIResponseImpl.json({"data": str(result)})
                    
                    # Convert APIResponse to FastAPI Response
                    return Response(
                        content=result.body if isinstance(result.body, (str, bytes)) else json.dumps(result.body),
                        status_code=result.status_code,
                        headers=result.headers,
                        media_type=result.headers.get("Content-Type", "application/json")
                    )
                
                return handler
            
            # Add the route to the FastAPI app
            app.add_api_route(
                path=f"{self._config.api_prefix}{route.path}",
                endpoint=await create_handler(route),
                methods=[route.method],
                name=route.name or None,
                description=route.description or None,
            )
        
        # Store the app
        self._app = app
        
        # Start the server
        uvicorn.run(
            app,
            host=self._config.host,
            port=self._config.port,
            log_level="debug" if self._config.debug else "info"
        )
    
    async def stop(self) -> None:
        """Stop the server."""
        # This is a no-op for now, as uvicorn.run is blocking
        pass


def create_api_server(config: Optional[Dict[str, Any]] = None) -> APIServer:
    """Create a new API server.
    
    Args:
        config: Optional server configuration as a dictionary.
        
    Returns:
        A new APIServer instance.
    """
    if config:
        api_config = APIConfigImpl.from_dict(config)
    else:
        api_config = APIConfigImpl()
    
    return APIServerImpl(config=api_config)


def create_api_response(data: Any, status_code: int = 200) -> APIResponse:
    """Create a new API response.
    
    Args:
        data: The response data.
        status_code: The HTTP status code.
        
    Returns:
        A new APIResponse instance.
    """
    if isinstance(data, dict) or isinstance(data, list):
        return APIResponseImpl.json(data, status_code)
    elif isinstance(data, str):
        return APIResponseImpl.text(data, status_code)
    elif data is None:
        return APIResponseImpl.json({}, status_code)
    else:
        return APIResponseImpl.json({"data": str(data)}, status_code)


def create_error_response(message: str, status_code: int = 400) -> APIResponse:
    """Create a new error response.
    
    Args:
        message: The error message.
        status_code: The HTTP status code.
        
    Returns:
        A new APIResponse instance.
    """
    return APIResponseImpl.error(message, status_code)
