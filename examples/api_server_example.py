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
"""Example of using API server implementation."""

import sys
import os
import json
from pathlib import Path
from typing import Dict, Any, List

# Add the src directory to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from textcase.core.api import (
    APIConfigImpl, APIServerImpl, APIRouteImpl, 
    create_api_server, create_api_response
)
from textcase.core.uri import create_uri, get_default_uri_resolver
from textcase.core.resource import create_resource, get_default_resource_registry
from textcase.core.task import TaskImpl, TaskListImpl, TaskStatusImpl
from textcase.core.test import TestCaseImpl, create_test_case, create_test_step


# Sample data
tasks = {
    "task-001": TaskImpl(
        id="task-001",
        title="实现URI解析功能",
        description="实现URI解析器，支持文档和源码URI格式",
        status=TaskStatusImpl.IN_PROGRESS,
        tags=["URI", "解析器", "实现"],
        assignee="developer1",
        priority=1
    ),
    "task-002": TaskImpl(
        id="task-002",
        title="实现资源管理功能",
        description="实现资源管理器，支持资源的创建、查询和引用",
        status=TaskStatusImpl.TODO,
        tags=["资源", "管理器", "实现"],
        assignee="developer1",
        priority=1
    )
}

test_cases = {
    "test-001": create_test_case(
        title="测试URI解析功能",
        description="验证URI解析器能够正确解析各种格式的URI",
        tags=["URI", "解析器", "测试"],
        preconditions="URI解析器已实现",
        postconditions="所有测试步骤通过"
    )
}

# Initialize resource registry with some sample resources
registry = get_default_resource_registry()
uri1 = create_uri("REQ", "001", "背景/LLM支持", "item")
resource1 = create_resource(
    uri=uri1,
    type_name="item",
    title="LLM支持需求",
    content="系统应该支持与大型语言模型集成，提供智能文本处理功能。",
    description="LLM集成需求文档",
    tags=["LLM", "AI", "需求"]
)
registry.register(resource1)


# API route handlers
async def get_tasks(request):
    """Get all tasks."""
    return create_api_response(
        status_code=200,
        content=json.dumps([task.to_dict() for task in tasks.values()]),
        content_type="application/json"
    )


async def get_task(request):
    """Get a task by ID."""
    task_id = request.path_params.get("task_id")
    if task_id not in tasks:
        return create_api_response(
            status_code=404,
            content=json.dumps({"error": f"Task with ID {task_id} not found"}),
            content_type="application/json"
        )
    
    return create_api_response(
        status_code=200,
        content=json.dumps(tasks[task_id].to_dict()),
        content_type="application/json"
    )


async def create_task(request):
    """Create a new task."""
    try:
        data = await request.json()
        task = TaskImpl.from_dict(data)
        tasks[task.id] = task
        
        return create_api_response(
            status_code=201,
            content=json.dumps(task.to_dict()),
            content_type="application/json"
        )
    except Exception as e:
        return create_api_response(
            status_code=400,
            content=json.dumps({"error": str(e)}),
            content_type="application/json"
        )


async def get_test_cases(request):
    """Get all test cases."""
    return create_api_response(
        status_code=200,
        content=json.dumps([test.to_dict() for test in test_cases.values()]),
        content_type="application/json"
    )


async def get_resources(request):
    """Get all resources."""
    resources = registry.get_all()
    return create_api_response(
        status_code=200,
        content=json.dumps([{
            "uri": str(r.uri),
            "title": r.metadata.title,
            "description": r.metadata.description,
            "tags": r.metadata.tags
        } for r in resources]),
        content_type="application/json"
    )


async def search_resources(request):
    """Search for resources."""
    query = request.query_params.get("q", "")
    resources = registry.find(query)
    return create_api_response(
        status_code=200,
        content=json.dumps([{
            "uri": str(r.uri),
            "title": r.metadata.title,
            "description": r.metadata.description,
            "tags": r.metadata.tags
        } for r in resources]),
        content_type="application/json"
    )


def setup_api_server():
    """Set up and configure the API server."""
    # Create API server directly with default config
    server = APIServerImpl()
    
    # Register routes
    server.add_route(
        path="/api/tasks",
        handler=get_tasks,
        methods="GET",
        name="get_tasks",
        description="Returns a list of all tasks"
    )
    
    server.add_route(
        path="/api/tasks/{task_id}",
        handler=get_task,
        methods="GET",
        name="get_task",
        description="Returns a task with the specified ID"
    )
    
    server.add_route(
        path="/api/tasks",
        handler=create_task,
        methods="POST",
        name="create_task",
        description="Creates a new task with the provided data"
    )
    
    server.add_route(
        path="/api/tests",
        handler=get_test_cases,
        methods="GET",
        name="get_test_cases",
        description="Returns a list of all test cases"
    )
    
    server.add_route(
        path="/api/resources",
        handler=get_resources,
        methods="GET",
        name="get_resources",
        description="Returns a list of all resources"
    )
    
    server.add_route(
        path="/api/resources/search",
        handler=search_resources,
        methods="GET",
        name="search_resources",
        description="Searches for resources matching the query"
    )
    
    return server


def main():
    """Run the API server example."""
    print("API Server Example")
    print("=================")
    print()
    print("Starting API server on http://127.0.0.1:8000")
    print("API documentation available at http://127.0.0.1:8000/docs")
    print()
    print("Press Ctrl+C to stop the server")
    server = setup_api_server()
    
    # 由于 uvicorn.run() 是阻塞的，我们不能使用 await，而是直接调用
    # 这里我们创建一个非异步的包装函数来启动服务器
    try:
        # 导入必要的模块
        from fastapi import FastAPI
        import uvicorn
        
        # 获取 FastAPI 应用实例
        app = server._app
        if not app:
            # 如果应用还没有创建，我们需要手动创建它
            # 这部分通常在 start() 方法中完成，但我们需要分离出来
            print("Creating FastAPI application...")
            app = FastAPI(
                title="TextCase API",
                description="API for TextCase document management system",
                version="1.0.0"
            )
            # 注册路由...
        
        # 直接使用 uvicorn 运行应用
        uvicorn.run(
            app,
            host="127.0.0.1",
            port=8000,
            log_level="info"
        )
    except ImportError:
        print("FastAPI or uvicorn not installed. Please install them with: pip install fastapi uvicorn")
    except Exception as e:
        print(f"Error starting server: {e}")


if __name__ == "__main__":
    main()
