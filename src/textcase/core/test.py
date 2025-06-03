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
"""Test case implementation for textcase."""

from __future__ import annotations

import enum
import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Set, Union, cast

from textcase.protocol.task import (
    TestCase, TestStep, TestVerification, TestResult, TestRunner
)
from textcase.protocol.uri import URI
from textcase.core.uri import URIImpl, get_default_uri_resolver
from textcase.core.task import TaskImpl


class TestStepImpl:
    """Implementation of TestStep protocol."""
    
    def __init__(self, 
                id: str,
                name: str,
                description: str,
                order: int = 0,
                expected_result: Optional[str] = None,
                attributes: Optional[Dict[str, Any]] = None):
        """Initialize a test step.
        
        Args:
            id: The step ID.
            name: The step name.
            description: The step description.
            order: The step order.
            expected_result: Optional expected result.
            attributes: Optional step attributes.
        """
        self._id = id
        self._name = name
        self._description = description
        self._order = order
        self._expected_result = expected_result
        self._attributes = attributes or {}
        self._verifications: List[TestVerification] = []
    
    @property
    def id(self) -> str:
        """Get the step ID."""
        return self._id
    
    @property
    def name(self) -> str:
        """Get the step name."""
        return self._name
    
    @property
    def description(self) -> str:
        """Get the step description."""
        return self._description
    
    @property
    def order(self) -> int:
        """Get the step order."""
        return self._order
    
    @property
    def expected_result(self) -> Optional[str]:
        """Get the expected result."""
        return self._expected_result
    
    @property
    def attributes(self) -> Dict[str, Any]:
        """Get all step attributes."""
        return self._attributes.copy()
    
    @property
    def verifications(self) -> List[TestVerification]:
        """Get all verifications."""
        return self._verifications.copy()
    
    def add_verification(self, verification: TestVerification) -> None:
        """Add a verification."""
        self._verifications.append(verification)
    
    def remove_verification(self, verification_id: str) -> None:
        """Remove a verification."""
        self._verifications = [v for v in self._verifications if v.id != verification_id]
    
    def set_name(self, name: str) -> None:
        """Set the step name."""
        self._name = name
    
    def set_description(self, description: str) -> None:
        """Set the step description."""
        self._description = description
    
    def set_order(self, order: int) -> None:
        """Set the step order."""
        self._order = order
    
    def set_expected_result(self, expected_result: str) -> None:
        """Set the expected result."""
        self._expected_result = expected_result
    
    def set_attribute(self, name: str, value: Any) -> None:
        """Set a step attribute."""
        self._attributes[name] = value
    
    def get_attribute(self, name: str, default: Any = None) -> Any:
        """Get a step attribute."""
        return self._attributes.get(name, default)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert the step to a dictionary."""
        return {
            "id": self._id,
            "name": self._name,
            "description": self._description,
            "order": self._order,
            "expected_result": self._expected_result,
            "attributes": self._attributes,
            "verifications": [v.to_dict() if hasattr(v, "to_dict") else {"id": v.id} for v in self._verifications]
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> TestStepImpl:
        """Create a step from a dictionary."""
        step = cls(
            id=data.get("id", str(uuid.uuid4())),
            name=data.get("name", ""),
            description=data.get("description", ""),
            order=data.get("order", 0),
            expected_result=data.get("expected_result"),
            attributes=data.get("attributes", {})
        )
        
        # Add verifications
        verifications = data.get("verifications", [])
        for verification_data in verifications:
            if isinstance(verification_data, dict):
                verification = TestVerificationImpl.from_dict(verification_data)
                step.add_verification(verification)
        
        return step


class TestVerificationImpl:
    """Implementation of TestVerification protocol."""
    
    def __init__(self, 
                id: str,
                name: str,
                condition: str,
                order: int = 0,
                attributes: Optional[Dict[str, Any]] = None):
        """Initialize a test verification.
        
        Args:
            id: The verification ID.
            name: The verification name.
            condition: The verification condition.
            order: The verification order.
            attributes: Optional verification attributes.
        """
        self._id = id
        self._name = name
        self._condition = condition
        self._order = order
        self._attributes = attributes or {}
    
    @property
    def id(self) -> str:
        """Get the verification ID."""
        return self._id
    
    @property
    def name(self) -> str:
        """Get the verification name."""
        return self._name
    
    @property
    def condition(self) -> str:
        """Get the verification condition."""
        return self._condition
    
    @property
    def order(self) -> int:
        """Get the verification order."""
        return self._order
    
    @property
    def attributes(self) -> Dict[str, Any]:
        """Get all verification attributes."""
        return self._attributes.copy()
    
    def set_name(self, name: str) -> None:
        """Set the verification name."""
        self._name = name
    
    def set_condition(self, condition: str) -> None:
        """Set the verification condition."""
        self._condition = condition
    
    def set_order(self, order: int) -> None:
        """Set the verification order."""
        self._order = order
    
    def set_attribute(self, name: str, value: Any) -> None:
        """Set a verification attribute."""
        self._attributes[name] = value
    
    def get_attribute(self, name: str, default: Any = None) -> Any:
        """Get a verification attribute."""
        return self._attributes.get(name, default)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert the verification to a dictionary."""
        return {
            "id": self._id,
            "name": self._name,
            "condition": self._condition,
            "order": self._order,
            "attributes": self._attributes
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> TestVerificationImpl:
        """Create a verification from a dictionary."""
        return cls(
            id=data.get("id", str(uuid.uuid4())),
            name=data.get("name", ""),
            condition=data.get("condition", ""),
            order=data.get("order", 0),
            attributes=data.get("attributes", {})
        )


class TestResultImpl:
    """Implementation of TestResult protocol."""
    
    def __init__(self, 
                id: str,
                test_case_id: str,
                success: bool,
                message: Optional[str] = None,
                created_at: Optional[str] = None,
                step_results: Optional[Dict[str, bool]] = None,
                verification_results: Optional[Dict[str, bool]] = None,
                attributes: Optional[Dict[str, Any]] = None):
        """Initialize a test result.
        
        Args:
            id: The result ID.
            test_case_id: The test case ID.
            success: Whether the test was successful.
            message: Optional result message.
            created_at: Optional creation time.
            step_results: Optional step results.
            verification_results: Optional verification results.
            attributes: Optional result attributes.
        """
        self._id = id
        self._test_case_id = test_case_id
        self._success = success
        self._message = message
        self._created_at = created_at or datetime.now().isoformat()
        self._step_results = step_results or {}
        self._verification_results = verification_results or {}
        self._attributes = attributes or {}
    
    @property
    def id(self) -> str:
        """Get the result ID."""
        return self._id
    
    @property
    def test_case_id(self) -> str:
        """Get the test case ID."""
        return self._test_case_id
    
    @property
    def success(self) -> bool:
        """Check if the test was successful."""
        return self._success
    
    @property
    def message(self) -> Optional[str]:
        """Get the result message."""
        return self._message
    
    @property
    def created_at(self) -> str:
        """Get the result creation time."""
        return self._created_at
    
    @property
    def step_results(self) -> Dict[str, bool]:
        """Get all step results."""
        return self._step_results.copy()
    
    @property
    def verification_results(self) -> Dict[str, bool]:
        """Get all verification results."""
        return self._verification_results.copy()
    
    @property
    def attributes(self) -> Dict[str, Any]:
        """Get all result attributes."""
        return self._attributes.copy()
    
    def set_step_result(self, step_id: str, success: bool) -> None:
        """Set a step result."""
        self._step_results[step_id] = success
    
    def set_verification_result(self, verification_id: str, success: bool) -> None:
        """Set a verification result."""
        self._verification_results[verification_id] = success
    
    def set_attribute(self, name: str, value: Any) -> None:
        """Set a result attribute."""
        self._attributes[name] = value
    
    def get_attribute(self, name: str, default: Any = None) -> Any:
        """Get a result attribute."""
        return self._attributes.get(name, default)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert the result to a dictionary."""
        return {
            "id": self._id,
            "test_case_id": self._test_case_id,
            "success": self._success,
            "message": self._message,
            "created_at": self._created_at,
            "step_results": self._step_results,
            "verification_results": self._verification_results,
            "attributes": self._attributes
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> TestResultImpl:
        """Create a result from a dictionary."""
        return cls(
            id=data.get("id", str(uuid.uuid4())),
            test_case_id=data.get("test_case_id", ""),
            success=data.get("success", False),
            message=data.get("message"),
            created_at=data.get("created_at"),
            step_results=data.get("step_results", {}),
            verification_results=data.get("verification_results", {}),
            attributes=data.get("attributes", {})
        )


class TestCaseImpl(TaskImpl):
    """Implementation of TestCase protocol."""
    
    def __init__(self, 
                id: str,
                title: str,
                description: Optional[str] = None,
                status: Any = None,  # Use TaskStatusImpl.TODO
                tags: Optional[List[str]] = None,
                due_date: Optional[str] = None,
                created_at: Optional[str] = None,
                updated_at: Optional[str] = None,
                parent_id: Optional[str] = None,
                assignee: Optional[str] = None,
                priority: int = 0,
                attributes: Optional[Dict[str, Any]] = None,
                uri: Optional[URI] = None,
                preconditions: Optional[str] = None,
                postconditions: Optional[str] = None):
        """Initialize a test case.
        
        Args:
            id: The test case ID.
            title: The test case title.
            description: Optional test case description.
            status: The test case status.
            tags: Optional test case tags.
            due_date: Optional due date.
            created_at: Optional creation time.
            updated_at: Optional last update time.
            parent_id: Optional parent test case ID.
            assignee: Optional assignee.
            priority: Test case priority.
            attributes: Optional test case attributes.
            uri: Optional URI associated with this test case.
            preconditions: Optional preconditions.
            postconditions: Optional postconditions.
        """
        from textcase.core.task import TaskStatusImpl
        
        super().__init__(
            id=id,
            title=title,
            description=description,
            status=status or TaskStatusImpl.TODO,
            tags=tags,
            due_date=due_date,
            created_at=created_at,
            updated_at=updated_at,
            parent_id=parent_id,
            assignee=assignee,
            priority=priority,
            attributes=attributes,
            uri=uri
        )
        
        self._preconditions = preconditions
        self._postconditions = postconditions
        self._steps: List[TestStep] = []
        self._results: List[TestResult] = []
    
    @property
    def preconditions(self) -> Optional[str]:
        """Get the test case preconditions."""
        return self._preconditions
    
    @property
    def postconditions(self) -> Optional[str]:
        """Get the test case postconditions."""
        return self._postconditions
    
    @property
    def steps(self) -> List[TestStep]:
        """Get all test steps."""
        return self._steps.copy()
    
    @property
    def results(self) -> List[TestResult]:
        """Get all test results."""
        return self._results.copy()
    
    def set_preconditions(self, preconditions: str) -> None:
        """Set the test case preconditions."""
        self._preconditions = preconditions
        self._updated_at = datetime.now().isoformat()
    
    def set_postconditions(self, postconditions: str) -> None:
        """Set the test case postconditions."""
        self._postconditions = postconditions
        self._updated_at = datetime.now().isoformat()
    
    def add_step(self, step: TestStep) -> None:
        """Add a test step."""
        self._steps.append(step)
        self._updated_at = datetime.now().isoformat()
    
    def remove_step(self, step_id: str) -> None:
        """Remove a test step."""
        self._steps = [s for s in self._steps if s.id != step_id]
        self._updated_at = datetime.now().isoformat()
    
    def add_result(self, result: TestResult) -> None:
        """Add a test result."""
        self._results.append(result)
        self._updated_at = datetime.now().isoformat()
    
    def remove_result(self, result_id: str) -> None:
        """Remove a test result."""
        self._results = [r for r in self._results if r.id != result_id]
        self._updated_at = datetime.now().isoformat()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert the test case to a dictionary."""
        result = super().to_dict()
        
        result.update({
            "preconditions": self._preconditions,
            "postconditions": self._postconditions,
            "steps": [step.to_dict() if hasattr(step, "to_dict") else {"id": step.id} for step in self._steps],
            "results": [result.to_dict() if hasattr(result, "to_dict") else {"id": result.id} for result in self._results]
        })
        
        return result
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> TestCaseImpl:
        """Create a test case from a dictionary."""
        from textcase.core.task import TaskStatusImpl
        
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
        
        test_case = cls(
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
            uri=uri,
            preconditions=data.get("preconditions"),
            postconditions=data.get("postconditions")
        )
        
        # Add steps
        steps = data.get("steps", [])
        for step_data in steps:
            if isinstance(step_data, dict):
                step = TestStepImpl.from_dict(step_data)
                test_case.add_step(step)
        
        # Add results
        results = data.get("results", [])
        for result_data in results:
            if isinstance(result_data, dict):
                result = TestResultImpl.from_dict(result_data)
                test_case.add_result(result)
        
        # Add subtasks
        subtasks = data.get("subtasks", [])
        for subtask_data in subtasks:
            if isinstance(subtask_data, dict):
                subtask = TaskImpl.from_dict(subtask_data)
                test_case.add_subtask(subtask)
        
        return test_case


class TestRunnerImpl:
    """Implementation of TestRunner protocol."""
    
    def __init__(self, name: str):
        """Initialize a test runner.
        
        Args:
            name: The runner name.
        """
        self._name = name
        self._test_cases: Dict[str, TestCase] = {}
        self._results: Dict[str, List[TestResult]] = {}
    
    @property
    def name(self) -> str:
        """Get the runner name."""
        return self._name
    
    def add_test_case(self, test_case: TestCase) -> None:
        """Add a test case."""
        self._test_cases[test_case.id] = test_case
    
    def remove_test_case(self, test_case_id: str) -> None:
        """Remove a test case."""
        if test_case_id in self._test_cases:
            del self._test_cases[test_case_id]
    
    def get_test_case(self, test_case_id: str) -> Optional[TestCase]:
        """Get a test case by ID."""
        return self._test_cases.get(test_case_id)
    
    def get_test_cases(self) -> List[TestCase]:
        """Get all test cases."""
        return list(self._test_cases.values())
    
    def get_results(self, test_case_id: str) -> List[TestResult]:
        """Get all results for a test case."""
        return self._results.get(test_case_id, [])
    
    def run_test(self, test_case_id: str) -> TestResult:
        """Run a test case.
        
        This is a placeholder implementation that always returns a successful result.
        In a real implementation, this would execute the test steps and verify the conditions.
        """
        test_case = self.get_test_case(test_case_id)
        if not test_case:
            raise ValueError(f"Test case with ID '{test_case_id}' not found")
        
        # Create a new result
        result = TestResultImpl(
            id=str(uuid.uuid4()),
            test_case_id=test_case_id,
            success=True,
            message="Test executed successfully",
        )
        
        # Add the result to the test case
        test_case.add_result(result)
        
        # Add the result to the runner
        if test_case_id not in self._results:
            self._results[test_case_id] = []
        self._results[test_case_id].append(result)
        
        return result
    
    def run_all_tests(self) -> Dict[str, TestResult]:
        """Run all test cases.
        
        Returns:
            A dictionary mapping test case IDs to their results.
        """
        results = {}
        for test_case_id in self._test_cases:
            results[test_case_id] = self.run_test(test_case_id)
        return results


def create_test_case(title: str,
                    description: Optional[str] = None,
                    tags: Optional[List[str]] = None,
                    preconditions: Optional[str] = None,
                    postconditions: Optional[str] = None) -> TestCase:
    """Create a new test case.
    
    Args:
        title: The test case title.
        description: Optional test case description.
        tags: Optional test case tags.
        preconditions: Optional preconditions.
        postconditions: Optional postconditions.
        
    Returns:
        A new TestCase instance.
    """
    from textcase.core.task import TaskStatusImpl
    
    return TestCaseImpl(
        id=str(uuid.uuid4()),
        title=title,
        description=description,
        status=TaskStatusImpl.TODO,
        tags=tags,
        preconditions=preconditions,
        postconditions=postconditions
    )


def create_test_step(name: str,
                    description: str,
                    expected_result: Optional[str] = None,
                    order: int = 0) -> TestStep:
    """Create a new test step.
    
    Args:
        name: The step name.
        description: The step description.
        expected_result: Optional expected result.
        order: The step order.
        
    Returns:
        A new TestStep instance.
    """
    return TestStepImpl(
        id=str(uuid.uuid4()),
        name=name,
        description=description,
        expected_result=expected_result,
        order=order
    )


def create_test_verification(name: str,
                           condition: str,
                           order: int = 0) -> TestVerification:
    """Create a new test verification.
    
    Args:
        name: The verification name.
        condition: The verification condition.
        order: The verification order.
        
    Returns:
        A new TestVerification instance.
    """
    return TestVerificationImpl(
        id=str(uuid.uuid4()),
        name=name,
        condition=condition,
        order=order
    )


def create_test_result(test_case_id: str,
                      success: bool,
                      message: Optional[str] = None) -> TestResult:
    """Create a new test result.
    
    Args:
        test_case_id: The test case ID.
        success: Whether the test was successful.
        message: Optional result message.
        
    Returns:
        A new TestResult instance.
    """
    return TestResultImpl(
        id=str(uuid.uuid4()),
        test_case_id=test_case_id,
        success=success,
        message=message
    )


def create_test_runner(name: str) -> TestRunner:
    """Create a new test runner.
    
    Args:
        name: The runner name.
        
    Returns:
        A new TestRunner instance.
    """
    return TestRunnerImpl(name=name)
