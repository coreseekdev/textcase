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
"""Task and test case implementation for textcase."""

from __future__ import annotations

import enum
import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Set, Union, cast

from textcase.protocol.task import (
    Task, TaskList, TaskStatus, TestCase, TestStep, TestVerification, TestResult, TestRunner
)
from textcase.protocol.uri import URI
from textcase.core.uri import URIImpl, get_default_uri_resolver


class TaskStatusImpl(enum.Enum):
    """Implementation of TaskStatus protocol."""
    
    TODO = "todo"
    IN_PROGRESS = "in_progress"
    DONE = "done"
    BLOCKED = "blocked"
    CANCELLED = "cancelled"
    
    @property
    def name(self) -> str:
        """Get the name of the status."""
        return self.value
    
    @property
    def is_completed(self) -> bool:
        """Check if the status is completed."""
        return self in (TaskStatusImpl.DONE, TaskStatusImpl.CANCELLED)
    
    @property
    def is_active(self) -> bool:
        """Check if the status is active."""
        return self in (TaskStatusImpl.TODO, TaskStatusImpl.IN_PROGRESS)
    
    @property
    def is_blocked(self) -> bool:
        """Check if the status is blocked."""
        return self == TaskStatusImpl.BLOCKED


class TaskImpl:
    """Implementation of Task protocol."""
    
    def __init__(self, 
                id: str,
                title: str,
                description: Optional[str] = None,
                status: TaskStatus = TaskStatusImpl.TODO,
                tags: Optional[List[str]] = None,
                due_date: Optional[str] = None,
                created_at: Optional[str] = None,
                updated_at: Optional[str] = None,
                parent_id: Optional[str] = None,
                assignee: Optional[str] = None,
                priority: int = 0,
                attributes: Optional[Dict[str, Any]] = None,
                uri: Optional[URI] = None):
        """Initialize a task.
        
        Args:
            id: The task ID.
            title: The task title.
            description: Optional task description.
            status: The task status.
            tags: Optional task tags.
            due_date: Optional due date.
            created_at: Optional creation time.
            updated_at: Optional last update time.
            parent_id: Optional parent task ID.
            assignee: Optional assignee.
            priority: Task priority.
            attributes: Optional task attributes.
            uri: Optional URI associated with this task.
        """
        self._id = id
        self._title = title
        self._description = description
        self._status = status
        self._tags = tags or []
        self._due_date = due_date
        self._created_at = created_at or datetime.now().isoformat()
        self._updated_at = updated_at or self._created_at
        self._parent_id = parent_id
        self._assignee = assignee
        self._priority = priority
        self._attributes = attributes or {}
        self._subtasks: List[Task] = []
        self._uri = uri
    
    @property
    def id(self) -> str:
        """Get the task ID."""
        return self._id
    
    @property
    def title(self) -> str:
        """Get the task title."""
        return self._title
    
    @property
    def description(self) -> Optional[str]:
        """Get the task description."""
        return self._description
    
    @property
    def status(self) -> TaskStatus:
        """Get the task status."""
        return self._status
    
    @property
    def tags(self) -> List[str]:
        """Get the task tags."""
        return self._tags.copy()
    
    @property
    def due_date(self) -> Optional[str]:
        """Get the task due date."""
        return self._due_date
    
    @property
    def created_at(self) -> str:
        """Get the task creation time."""
        return self._created_at
    
    @property
    def updated_at(self) -> str:
        """Get the task last update time."""
        return self._updated_at
    
    @property
    def parent_id(self) -> Optional[str]:
        """Get the parent task ID."""
        return self._parent_id
    
    @property
    def assignee(self) -> Optional[str]:
        """Get the task assignee."""
        return self._assignee
    
    @property
    def priority(self) -> int:
        """Get the task priority."""
        return self._priority
    
    @property
    def attributes(self) -> Dict[str, Any]:
        """Get all task attributes."""
        return self._attributes.copy()
    
    @property
    def subtasks(self) -> List[Task]:
        """Get all subtasks."""
        return self._subtasks.copy()
    
    @property
    def uri(self) -> Optional[URI]:
        """Get the task URI."""
        return self._uri
    
    def set_status(self, status: TaskStatus) -> None:
        """Set the task status."""
        self._status = status
        self._updated_at = datetime.now().isoformat()
    
    def set_title(self, title: str) -> None:
        """Set the task title."""
        self._title = title
        self._updated_at = datetime.now().isoformat()
    
    def set_description(self, description: str) -> None:
        """Set the task description."""
        self._description = description
        self._updated_at = datetime.now().isoformat()
    
    def set_due_date(self, due_date: Optional[str]) -> None:
        """Set the task due date."""
        self._due_date = due_date
        self._updated_at = datetime.now().isoformat()
    
    def set_assignee(self, assignee: Optional[str]) -> None:
        """Set the task assignee."""
        self._assignee = assignee
        self._updated_at = datetime.now().isoformat()
    
    def set_priority(self, priority: int) -> None:
        """Set the task priority."""
        self._priority = priority
        self._updated_at = datetime.now().isoformat()
    
    def add_tag(self, tag: str) -> None:
        """Add a tag to the task."""
        if tag not in self._tags:
            self._tags.append(tag)
            self._updated_at = datetime.now().isoformat()
    
    def remove_tag(self, tag: str) -> None:
        """Remove a tag from the task."""
        if tag in self._tags:
            self._tags.remove(tag)
            self._updated_at = datetime.now().isoformat()
    
    def set_attribute(self, name: str, value: Any) -> None:
        """Set a task attribute."""
        self._attributes[name] = value
        self._updated_at = datetime.now().isoformat()
    
    def get_attribute(self, name: str, default: Any = None) -> Any:
        """Get a task attribute."""
        return self._attributes.get(name, default)
    
    def add_subtask(self, subtask: Task) -> None:
        """Add a subtask."""
        if subtask not in self._subtasks:
            self._subtasks.append(subtask)
            self._updated_at = datetime.now().isoformat()
    
    def remove_subtask(self, subtask_id: str) -> None:
        """Remove a subtask."""
        for i, subtask in enumerate(self._subtasks):
            if subtask.id == subtask_id:
                del self._subtasks[i]
                self._updated_at = datetime.now().isoformat()
                break
    
    def set_uri(self, uri: URI) -> None:
        """Set the task URI."""
        self._uri = uri
        self._updated_at = datetime.now().isoformat()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert the task to a dictionary."""
        result = {
            "id": self._id,
            "title": self._title,
            "description": self._description,
            "status": self._status.name if hasattr(self._status, "name") else str(self._status),
            "tags": self._tags,
            "due_date": self._due_date,
            "created_at": self._created_at,
            "updated_at": self._updated_at,
            "parent_id": self._parent_id,
            "assignee": self._assignee,
            "priority": self._priority,
            "attributes": self._attributes,
            "subtasks": [subtask.to_dict() if hasattr(subtask, "to_dict") else {"id": subtask.id} for subtask in self._subtasks]
        }
        
        if self._uri:
            result["uri"] = str(self._uri)
            
        return result
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> TaskImpl:
        """Create a task from a dictionary."""
        # Parse status
        status_str = data.get("status", "todo")
        try:
            status = TaskStatusImpl(status_str)
        except ValueError:
            status = TaskStatusImpl.TODO
        
        # Parse URI if present
        uri = None
        uri_str = data.get("uri")
        if uri_str:
            try:
                uri_resolver = get_default_uri_resolver()
                uri = uri_resolver.parse(uri_str)
            except ValueError:
                # Invalid URI, ignore it
                pass
        
        task = cls(
            id=data.get("id", str(uuid.uuid4())),
            title=data.get("title", ""),
            description=data.get("description"),
            status=status,
            tags=data.get("tags", []),
            due_date=data.get("due_date"),
            created_at=data.get("created_at"),
            updated_at=data.get("updated_at"),
            parent_id=data.get("parent_id"),
            assignee=data.get("assignee"),
            priority=data.get("priority", 0),
            attributes=data.get("attributes", {}),
            uri=uri
        )
        
        # Add subtasks
        subtasks = data.get("subtasks", [])
        for subtask_data in subtasks:
            if isinstance(subtask_data, dict):
                subtask = cls.from_dict(subtask_data)
                task.add_subtask(subtask)
        
        return task


class TaskListImpl:
    """Implementation of TaskList protocol."""
    
    def __init__(self, 
                name: str,
                description: Optional[str] = None,
                tags: Optional[List[str]] = None,
                created_at: Optional[str] = None,
                updated_at: Optional[str] = None,
                attributes: Optional[Dict[str, Any]] = None):
        """Initialize a task list.
        
        Args:
            name: The task list name.
            description: Optional task list description.
            tags: Optional task list tags.
            created_at: Optional creation time.
            updated_at: Optional last update time.
            attributes: Optional task list attributes.
        """
        self._name = name
        self._description = description
        self._tags = tags or []
        self._created_at = created_at or datetime.now().isoformat()
        self._updated_at = updated_at or self._created_at
        self._attributes = attributes or {}
        self._tasks: Dict[str, Task] = {}
    
    @property
    def name(self) -> str:
        """Get the task list name."""
        return self._name
    
    @property
    def description(self) -> Optional[str]:
        """Get the task list description."""
        return self._description
    
    @property
    def tags(self) -> List[str]:
        """Get the task list tags."""
        return self._tags.copy()
    
    @property
    def created_at(self) -> str:
        """Get the task list creation time."""
        return self._created_at
    
    @property
    def updated_at(self) -> str:
        """Get the task list last update time."""
        return self._updated_at
    
    @property
    def attributes(self) -> Dict[str, Any]:
        """Get all task list attributes."""
        return self._attributes.copy()
    
    @property
    def tasks(self) -> List[Task]:
        """Get all tasks in the list."""
        return list(self._tasks.values())
    
    def add_task(self, task: Task) -> None:
        """Add a task to the list."""
        self._tasks[task.id] = task
        self._updated_at = datetime.now().isoformat()
    
    def remove_task(self, task_id: str) -> None:
        """Remove a task from the list."""
        if task_id in self._tasks:
            del self._tasks[task_id]
            self._updated_at = datetime.now().isoformat()
    
    def get_task(self, task_id: str) -> Optional[Task]:
        """Get a task by ID."""
        return self._tasks.get(task_id)
    
    def get_tasks_by_status(self, status: TaskStatus) -> List[Task]:
        """Get tasks by status."""
        return [task for task in self._tasks.values() if task.status == status]
    
    def get_tasks_by_tag(self, tag: str) -> List[Task]:
        """Get tasks by tag."""
        return [task for task in self._tasks.values() if tag in task.tags]
    
    def get_tasks_by_assignee(self, assignee: str) -> List[Task]:
        """Get tasks by assignee."""
        return [task for task in self._tasks.values() if task.assignee == assignee]
    
    def set_name(self, name: str) -> None:
        """Set the task list name."""
        self._name = name
        self._updated_at = datetime.now().isoformat()
    
    def set_description(self, description: str) -> None:
        """Set the task list description."""
        self._description = description
        self._updated_at = datetime.now().isoformat()
    
    def add_tag(self, tag: str) -> None:
        """Add a tag to the task list."""
        if tag not in self._tags:
            self._tags.append(tag)
            self._updated_at = datetime.now().isoformat()
    
    def remove_tag(self, tag: str) -> None:
        """Remove a tag from the task list."""
        if tag in self._tags:
            self._tags.remove(tag)
            self._updated_at = datetime.now().isoformat()
    
    def set_attribute(self, name: str, value: Any) -> None:
        """Set a task list attribute."""
        self._attributes[name] = value
        self._updated_at = datetime.now().isoformat()
    
    def get_attribute(self, name: str, default: Any = None) -> Any:
        """Get a task list attribute."""
        return self._attributes.get(name, default)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert the task list to a dictionary."""
        return {
            "name": self._name,
            "description": self._description,
            "tags": self._tags,
            "created_at": self._created_at,
            "updated_at": self._updated_at,
            "attributes": self._attributes,
            "tasks": [task.to_dict() for task in self._tasks.values()]
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> TaskListImpl:
        """Create a task list from a dictionary."""
        task_list = cls(
            name=data.get("name", ""),
            description=data.get("description"),
            tags=data.get("tags", []),
            created_at=data.get("created_at"),
            updated_at=data.get("updated_at"),
            attributes=data.get("attributes", {})
        )
        
        # Add tasks
        tasks_data = data.get("tasks", [])
        for task_data in tasks_data:
            if isinstance(task_data, dict):
                task = TaskImpl.from_dict(task_data)
                task_list.add_task(task)
        
        return task_list
