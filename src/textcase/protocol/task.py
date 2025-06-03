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
"""Task and test case protocol definitions."""

from __future__ import annotations

from abc import abstractmethod
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Protocol, TypeVar, Union

from .uri import URI

__all__ = [
    'Task',
    'TaskList',
    'TaskStatus',
    'TestCase',
    'TestStep',
    'TestVerification',
    'TestResult',
    'TestRunner',
]


class TaskStatus(Protocol):
    """Protocol for task status."""
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Get the status name."""
        ...
    
    @property
    @abstractmethod
    def is_completed(self) -> bool:
        """Check if the task is completed."""
        ...
    
    @property
    @abstractmethod
    def is_failed(self) -> bool:
        """Check if the task is failed."""
        ...
    
    @property
    @abstractmethod
    def is_pending(self) -> bool:
        """Check if the task is pending."""
        ...
    
    @property
    @abstractmethod
    def is_in_progress(self) -> bool:
        """Check if the task is in progress."""
        ...
    
    @property
    @abstractmethod
    def description(self) -> str:
        """Get the status description."""
        ...
    
    @abstractmethod
    def __str__(self) -> str:
        """Convert the status to a string."""
        ...


class Task(Protocol):
    """Protocol for tasks."""
    
    @property
    @abstractmethod
    def id(self) -> str:
        """Get the task ID."""
        ...
    
    @property
    @abstractmethod
    def title(self) -> str:
        """Get the task title."""
        ...
    
    @property
    @abstractmethod
    def description(self) -> Optional[str]:
        """Get the task description."""
        ...
    
    @property
    @abstractmethod
    def status(self) -> TaskStatus:
        """Get the task status."""
        ...
    
    @property
    @abstractmethod
    def created_at(self) -> datetime:
        """Get the task creation time."""
        ...
    
    @property
    @abstractmethod
    def updated_at(self) -> datetime:
        """Get the task last update time."""
        ...
    
    @property
    @abstractmethod
    def due_date(self) -> Optional[datetime]:
        """Get the task due date."""
        ...
    
    @property
    @abstractmethod
    def tags(self) -> List[str]:
        """Get the task tags."""
        ...
    
    @property
    @abstractmethod
    def parent(self) -> Optional[Task]:
        """Get the parent task."""
        ...
    
    @property
    @abstractmethod
    def children(self) -> List[Task]:
        """Get the child tasks."""
        ...
    
    @property
    @abstractmethod
    def uri(self) -> Optional[URI]:
        """Get the task URI."""
        ...
    
    @abstractmethod
    def set_status(self, status: Union[str, TaskStatus]) -> None:
        """Set the task status.
        
        Args:
            status: The status to set.
            
        Raises:
            ValueError: If the status is invalid.
        """
        ...
    
    @abstractmethod
    def set_description(self, description: str) -> None:
        """Set the task description.
        
        Args:
            description: The description to set.
        """
        ...
    
    @abstractmethod
    def set_due_date(self, due_date: Optional[Union[datetime, str]]) -> None:
        """Set the task due date.
        
        Args:
            due_date: The due date to set.
            
        Raises:
            ValueError: If the due date is invalid.
        """
        ...
    
    @abstractmethod
    def add_tag(self, tag: str) -> None:
        """Add a tag to the task.
        
        Args:
            tag: The tag to add.
        """
        ...
    
    @abstractmethod
    def remove_tag(self, tag: str) -> None:
        """Remove a tag from the task.
        
        Args:
            tag: The tag to remove.
            
        Raises:
            ValueError: If the tag does not exist.
        """
        ...
    
    @abstractmethod
    def add_child(self, task: Task) -> None:
        """Add a child task.
        
        Args:
            task: The task to add.
            
        Raises:
            ValueError: If the task is already a child.
        """
        ...
    
    @abstractmethod
    def remove_child(self, task_id: str) -> None:
        """Remove a child task.
        
        Args:
            task_id: The ID of the task to remove.
            
        Raises:
            ValueError: If the task is not a child.
        """
        ...
    
    @abstractmethod
    def set_uri(self, uri: Optional[Union[str, URI]]) -> None:
        """Set the task URI.
        
        Args:
            uri: The URI to set.
            
        Raises:
            ValueError: If the URI is invalid.
        """
        ...


class TaskList(Protocol):
    """Protocol for task lists."""
    
    @property
    @abstractmethod
    def tasks(self) -> List[Task]:
        """Get all tasks in the list."""
        ...
    
    @abstractmethod
    def add_task(self, title: str, description: Optional[str] = None,
                status: Optional[Union[str, TaskStatus]] = None,
                due_date: Optional[Union[datetime, str]] = None,
                tags: Optional[List[str]] = None,
                parent_id: Optional[str] = None,
                uri: Optional[Union[str, URI]] = None) -> Task:
        """Add a task to the list.
        
        Args:
            title: The task title.
            description: Optional task description.
            status: Optional task status.
            due_date: Optional task due date.
            tags: Optional task tags.
            parent_id: Optional parent task ID.
            uri: Optional task URI.
            
        Returns:
            The added task.
            
        Raises:
            ValueError: If the parent task does not exist.
        """
        ...
    
    @abstractmethod
    def get_task(self, task_id: str) -> Optional[Task]:
        """Get a task by ID.
        
        Args:
            task_id: The ID of the task to get.
            
        Returns:
            The task, or None if not found.
        """
        ...
    
    @abstractmethod
    def remove_task(self, task_id: str) -> None:
        """Remove a task from the list.
        
        Args:
            task_id: The ID of the task to remove.
            
        Raises:
            ValueError: If the task does not exist.
        """
        ...
    
    @abstractmethod
    def find_tasks(self, query: str) -> List[Task]:
        """Find tasks by query.
        
        Args:
            query: The query to search for.
            
        Returns:
            A list of matching tasks.
        """
        ...
    
    @abstractmethod
    def get_tasks_by_status(self, status: Union[str, TaskStatus]) -> List[Task]:
        """Get tasks by status.
        
        Args:
            status: The status to filter by.
            
        Returns:
            A list of tasks with the specified status.
        """
        ...
    
    @abstractmethod
    def get_tasks_by_tag(self, tag: str) -> List[Task]:
        """Get tasks by tag.
        
        Args:
            tag: The tag to filter by.
            
        Returns:
            A list of tasks with the specified tag.
        """
        ...
    
    @abstractmethod
    def get_tasks_by_due_date(self, start_date: Optional[Union[datetime, str]] = None,
                             end_date: Optional[Union[datetime, str]] = None) -> List[Task]:
        """Get tasks by due date.
        
        Args:
            start_date: Optional start date.
            end_date: Optional end date.
            
        Returns:
            A list of tasks with due dates in the specified range.
        """
        ...
    
    @abstractmethod
    def get_root_tasks(self) -> List[Task]:
        """Get all root tasks (tasks without parents).
        
        Returns:
            A list of root tasks.
        """
        ...


class TestStep(Protocol):
    """Protocol for test steps."""
    
    @property
    @abstractmethod
    def id(self) -> str:
        """Get the step ID."""
        ...
    
    @property
    @abstractmethod
    def description(self) -> str:
        """Get the step description."""
        ...
    
    @property
    @abstractmethod
    def code(self) -> Optional[str]:
        """Get the step code."""
        ...
    
    @property
    @abstractmethod
    def language(self) -> Optional[str]:
        """Get the programming language of the step code."""
        ...
    
    @property
    @abstractmethod
    def expected_output(self) -> Optional[str]:
        """Get the expected output of the step."""
        ...
    
    @property
    @abstractmethod
    def timeout(self) -> Optional[int]:
        """Get the step timeout in seconds."""
        ...
    
    @abstractmethod
    def set_code(self, code: str, language: Optional[str] = None) -> None:
        """Set the step code.
        
        Args:
            code: The code to set.
            language: Optional programming language.
        """
        ...
    
    @abstractmethod
    def set_expected_output(self, expected_output: str) -> None:
        """Set the expected output of the step.
        
        Args:
            expected_output: The expected output to set.
        """
        ...
    
    @abstractmethod
    def set_timeout(self, timeout: Optional[int]) -> None:
        """Set the step timeout.
        
        Args:
            timeout: The timeout to set in seconds.
        """
        ...


class TestVerification(Protocol):
    """Protocol for test verifications."""
    
    @property
    @abstractmethod
    def id(self) -> str:
        """Get the verification ID."""
        ...
    
    @property
    @abstractmethod
    def description(self) -> str:
        """Get the verification description."""
        ...
    
    @property
    @abstractmethod
    def is_completed(self) -> bool:
        """Check if the verification is completed."""
        ...
    
    @property
    @abstractmethod
    def is_automated(self) -> bool:
        """Check if the verification is automated."""
        ...
    
    @property
    @abstractmethod
    def code(self) -> Optional[str]:
        """Get the verification code."""
        ...
    
    @property
    @abstractmethod
    def language(self) -> Optional[str]:
        """Get the programming language of the verification code."""
        ...
    
    @abstractmethod
    def set_completed(self, completed: bool) -> None:
        """Set the verification completion status.
        
        Args:
            completed: The completion status to set.
        """
        ...
    
    @abstractmethod
    def set_code(self, code: str, language: Optional[str] = None) -> None:
        """Set the verification code.
        
        Args:
            code: The code to set.
            language: Optional programming language.
        """
        ...


class TestResult(Protocol):
    """Protocol for test results."""
    
    @property
    @abstractmethod
    def test_case_id(self) -> str:
        """Get the test case ID."""
        ...
    
    @property
    @abstractmethod
    def success(self) -> bool:
        """Check if the test was successful."""
        ...
    
    @property
    @abstractmethod
    def message(self) -> str:
        """Get the result message."""
        ...
    
    @property
    @abstractmethod
    def start_time(self) -> datetime:
        """Get the test start time."""
        ...
    
    @property
    @abstractmethod
    def end_time(self) -> datetime:
        """Get the test end time."""
        ...
    
    @property
    @abstractmethod
    def duration(self) -> float:
        """Get the test duration in seconds."""
        ...
    
    @property
    @abstractmethod
    def step_results(self) -> Dict[str, Dict[str, Any]]:
        """Get the step results."""
        ...
    
    @property
    @abstractmethod
    def verification_results(self) -> Dict[str, bool]:
        """Get the verification results."""
        ...
    
    @abstractmethod
    def add_step_result(self, step_id: str, success: bool, output: str, error: Optional[str] = None,
                       duration: Optional[float] = None) -> None:
        """Add a step result.
        
        Args:
            step_id: The ID of the step.
            success: Whether the step was successful.
            output: The step output.
            error: Optional error message.
            duration: Optional step duration in seconds.
        """
        ...
    
    @abstractmethod
    def add_verification_result(self, verification_id: str, success: bool) -> None:
        """Add a verification result.
        
        Args:
            verification_id: The ID of the verification.
            success: Whether the verification was successful.
        """
        ...


class TestCase(Protocol):
    """Protocol for test cases."""
    
    @property
    @abstractmethod
    def id(self) -> str:
        """Get the test case ID."""
        ...
    
    @property
    @abstractmethod
    def title(self) -> str:
        """Get the test case title."""
        ...
    
    @property
    @abstractmethod
    def description(self) -> Optional[str]:
        """Get the test case description."""
        ...
    
    @property
    @abstractmethod
    def steps(self) -> List[TestStep]:
        """Get the test steps."""
        ...
    
    @property
    @abstractmethod
    def verifications(self) -> List[TestVerification]:
        """Get the test verifications."""
        ...
    
    @property
    @abstractmethod
    def prerequisites(self) -> List[str]:
        """Get the test prerequisites."""
        ...
    
    @property
    @abstractmethod
    def tags(self) -> List[str]:
        """Get the test tags."""
        ...
    
    @property
    @abstractmethod
    def setup_code(self) -> Optional[str]:
        """Get the test setup code."""
        ...
    
    @property
    @abstractmethod
    def teardown_code(self) -> Optional[str]:
        """Get the test teardown code."""
        ...
    
    @property
    @abstractmethod
    def uri(self) -> Optional[URI]:
        """Get the test case URI."""
        ...
    
    @abstractmethod
    def add_step(self, description: str, code: Optional[str] = None,
               language: Optional[str] = None, expected_output: Optional[str] = None,
               timeout: Optional[int] = None) -> TestStep:
        """Add a test step.
        
        Args:
            description: The step description.
            code: Optional step code.
            language: Optional programming language.
            expected_output: Optional expected output.
            timeout: Optional timeout in seconds.
            
        Returns:
            The added test step.
        """
        ...
    
    @abstractmethod
    def add_verification(self, description: str, code: Optional[str] = None,
                       language: Optional[str] = None, is_completed: bool = False) -> TestVerification:
        """Add a test verification.
        
        Args:
            description: The verification description.
            code: Optional verification code.
            language: Optional programming language.
            is_completed: Whether the verification is completed.
            
        Returns:
            The added test verification.
        """
        ...
    
    @abstractmethod
    def add_prerequisite(self, prerequisite: str) -> None:
        """Add a test prerequisite.
        
        Args:
            prerequisite: The prerequisite to add.
        """
        ...
    
    @abstractmethod
    def add_tag(self, tag: str) -> None:
        """Add a tag to the test case.
        
        Args:
            tag: The tag to add.
        """
        ...
    
    @abstractmethod
    def remove_tag(self, tag: str) -> None:
        """Remove a tag from the test case.
        
        Args:
            tag: The tag to remove.
            
        Raises:
            ValueError: If the tag does not exist.
        """
        ...
    
    @abstractmethod
    def set_setup_code(self, code: str, language: Optional[str] = None) -> None:
        """Set the test setup code.
        
        Args:
            code: The code to set.
            language: Optional programming language.
        """
        ...
    
    @abstractmethod
    def set_teardown_code(self, code: str, language: Optional[str] = None) -> None:
        """Set the test teardown code.
        
        Args:
            code: The code to set.
            language: Optional programming language.
        """
        ...
    
    @abstractmethod
    def set_uri(self, uri: Optional[Union[str, URI]]) -> None:
        """Set the test case URI.
        
        Args:
            uri: The URI to set.
            
        Raises:
            ValueError: If the URI is invalid.
        """
        ...


class TestRunner(Protocol):
    """Protocol for test runners."""
    
    @abstractmethod
    def run_test(self, test_case: TestCase) -> TestResult:
        """Run a test case.
        
        Args:
            test_case: The test case to run.
            
        Returns:
            The test result.
        """
        ...
    
    @abstractmethod
    def run_test_by_id(self, test_id: str) -> TestResult:
        """Run a test case by ID.
        
        Args:
            test_id: The ID of the test case to run.
            
        Returns:
            The test result.
            
        Raises:
            ValueError: If the test case does not exist.
        """
        ...
    
    @abstractmethod
    def run_tests_by_tag(self, tag: str) -> List[TestResult]:
        """Run test cases by tag.
        
        Args:
            tag: The tag to filter by.
            
        Returns:
            A list of test results.
        """
        ...
    
    @abstractmethod
    def get_test_case(self, test_id: str) -> Optional[TestCase]:
        """Get a test case by ID.
        
        Args:
            test_id: The ID of the test case to get.
            
        Returns:
            The test case, or None if not found.
        """
        ...
    
    @abstractmethod
    def find_test_cases(self, query: str) -> List[TestCase]:
        """Find test cases by query.
        
        Args:
            query: The query to search for.
            
        Returns:
            A list of matching test cases.
        """
        ...
