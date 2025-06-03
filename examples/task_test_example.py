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
"""Example of using task and test case implementations."""

import sys
import os
from pathlib import Path

# Add the src directory to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from textcase.core.uri import create_uri
from textcase.core.task import TaskImpl, TaskListImpl, TaskStatusImpl
from textcase.core.test import (
    TestCaseImpl, TestStepImpl, TestVerificationImpl, TestResultImpl, TestRunnerImpl,
    create_test_case, create_test_step, create_test_verification
)


def demonstrate_task_usage():
    """Demonstrate task usage."""
    print("\n=== Task Usage ===")
    
    # Create a task
    task = TaskImpl(
        id="task-001",
        title="实现URI解析功能",
        description="实现URI解析器，支持文档和源码URI格式",
        status=TaskStatusImpl.IN_PROGRESS,
        tags=["URI", "解析器", "实现"],
        assignee="developer1",
        priority=1
    )
    
    print(f"Created task: {task.id}")
    print(f"Title: {task.title}")
    print(f"Description: {task.description}")
    print(f"Status: {task.status.name}")
    print(f"Tags: {task.tags}")
    print(f"Assignee: {task.assignee}")
    print(f"Priority: {task.priority}")
    
    # Create a subtask
    subtask = TaskImpl(
        id="task-001-1",
        title="实现源码URI解析",
        description="实现源码URI格式的解析功能",
        status=TaskStatusImpl.TODO,
        tags=["URI", "源码", "解析器"],
        parent_id="task-001",
        assignee="developer2",
        priority=2
    )
    
    # Add the subtask to the parent task
    task.add_subtask(subtask)
    
    # Create a task list
    task_list = TaskListImpl(
        name="URI实现任务列表",
        description="包含所有与URI实现相关的任务",
        tags=["URI", "实现"]
    )
    
    # Add tasks to the list
    task_list.add_task(task)
    
    # Create another task
    task2 = TaskImpl(
        id="task-002",
        title="实现资源管理功能",
        description="实现资源管理器，支持资源的创建、查询和引用",
        status=TaskStatusImpl.TODO,
        tags=["资源", "管理器", "实现"],
        assignee="developer1",
        priority=1
    )
    
    # Add the task to the list
    task_list.add_task(task2)
    
    # Get tasks by status
    todo_tasks = task_list.get_tasks_by_status(TaskStatusImpl.TODO)
    print("\nTODO tasks:")
    for t in todo_tasks:
        print(f"  {t.id}: {t.title}")
    
    # Get tasks by assignee
    dev1_tasks = task_list.get_tasks_by_assignee("developer1")
    print("\nTasks assigned to developer1:")
    for t in dev1_tasks:
        print(f"  {t.id}: {t.title}")
    
    # Convert to dictionary
    task_dict = task.to_dict()
    print("\nTask as dictionary:")
    print(f"  {task_dict}")
    
    # Create from dictionary
    new_task = TaskImpl.from_dict(task_dict)
    print(f"\nRecreated task: {new_task.id}")
    print(f"Title: {new_task.title}")
    print(f"Subtasks: {len(new_task.subtasks)}")


def demonstrate_test_case_usage():
    """Demonstrate test case usage."""
    print("\n=== Test Case Usage ===")
    
    # Create a test case
    test_case = create_test_case(
        title="测试URI解析功能",
        description="验证URI解析器能够正确解析各种格式的URI",
        tags=["URI", "解析器", "测试"],
        preconditions="URI解析器已实现",
        postconditions="所有测试步骤通过"
    )
    
    print(f"Created test case: {test_case.id}")
    print(f"Title: {test_case.title}")
    print(f"Description: {test_case.description}")
    print(f"Preconditions: {test_case.preconditions}")
    print(f"Postconditions: {test_case.postconditions}")
    
    # Create test steps
    step1 = create_test_step(
        name="解析文档URI",
        description="解析格式为'REQ001/背景/LLM支持#item'的URI",
        expected_result="URI被正确解析，各组件值正确",
        order=1
    )
    
    step2 = create_test_step(
        name="解析源码URI",
        description="解析格式为'SRC/textcase/core/vfs.py/get_default_vfs#code'的URI",
        expected_result="URI被正确解析，各组件值正确",
        order=2
    )
    
    # Add verifications to steps
    verification1 = create_test_verification(
        name="验证前缀",
        condition="uri.prefix == 'REQ'",
        order=1
    )
    
    verification2 = create_test_verification(
        name="验证ID",
        condition="uri.id == '001'",
        order=2
    )
    
    step1.add_verification(verification1)
    step1.add_verification(verification2)
    
    # Add steps to test case
    test_case.add_step(step1)
    test_case.add_step(step2)
    
    # Create a test runner
    runner = TestRunnerImpl(name="URI测试运行器")
    
    # Add test case to runner
    runner.add_test_case(test_case)
    
    # Run the test
    result = runner.run_test(test_case.id)
    print(f"\nTest result: {'成功' if result.success else '失败'}")
    print(f"Message: {result.message}")
    
    # Add a result to the test case
    test_case.add_result(result)
    
    # Convert to dictionary
    test_case_dict = test_case.to_dict()
    print("\nTest case as dictionary:")
    print(f"  ID: {test_case_dict['id']}")
    print(f"  Title: {test_case_dict['title']}")
    print(f"  Steps: {len(test_case_dict['steps'])}")
    print(f"  Results: {len(test_case_dict['results'])}")
    
    # Create from dictionary
    new_test_case = TestCaseImpl.from_dict(test_case_dict)
    print(f"\nRecreated test case: {new_test_case.id}")
    print(f"Title: {new_test_case.title}")
    print(f"Steps: {len(new_test_case.steps)}")
    print(f"Results: {len(new_test_case.results)}")


def demonstrate_markdown_task_integration():
    """Demonstrate integration with Markdown task lists."""
    print("\n=== Markdown Task Integration ===")
    
    # This is a simplified example of how tasks could be parsed from Markdown
    markdown_content = """
# 测试计划

## 测试任务

- [ ] 实现URI解析功能
  - [ ] 解析文档URI
  - [ ] 解析源码URI
- [ ] 实现资源管理功能
  - [ ] 创建资源
  - [ ] 查询资源
  - [ ] 引用资源

## 测试用例

### TST001: 测试URI解析功能

**前置条件**: URI解析器已实现

**测试步骤**:

1. 解析文档URI
   - [ ] 验证前缀
   - [ ] 验证ID
2. 解析源码URI
   - [ ] 验证前缀
   - [ ] 验证路径

**后置条件**: 所有测试步骤通过
"""
    
    print("Markdown content that could be parsed into tasks and test cases:")
    print(markdown_content)
    
    print("\nNote: In a real implementation, we would parse this Markdown content")
    print("and convert it to Task and TestCase objects using the implemented classes.")
    print("The task list items would be mapped to Task objects, and the test case")
    print("sections would be mapped to TestCase objects with steps and verifications.")


def main():
    """Main function."""
    print("Task and Test Case Example")
    print("=========================")
    
    demonstrate_task_usage()
    demonstrate_test_case_usage()
    demonstrate_markdown_task_integration()


if __name__ == "__main__":
    main()
