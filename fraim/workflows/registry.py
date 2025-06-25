# SPDX-License-Identifier: MIT
# Copyright (c) 2025 Resourcely Inc.

"""
Workflow Registry System

This module provides a centralized registry for all workflows, allowing easy
addition of new workflows without modifying core routing logic.
"""

import asyncio
import types
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Type

from fraim.config import Config
from fraim.core.contextuals import Contextual
from fraim.core.workflows import Workflow
from fraim.outputs import sarif


@dataclass
class RegisteredWorkflow:
    """A workflow that has been registered in the system."""

    workflow_class: Type[Workflow]
    metadata: Dict[str, Any] = field(default_factory=dict)


# Static storage for registered workflows
_workflows: Dict[str, RegisteredWorkflow] = {}


def register(workflow_name: str, workflow_class: Type[Workflow], **metadata: Any) -> None:
    """
    Register a workflow class for a specific workflow.

    Args:
        workflow_name: Name of the workflow (e.g., 'code', 'packages', 'iac')
        workflow_class: Class that extends Workflow
        **metadata: Additional metadata about the workflow
    """
    registration = RegisteredWorkflow(workflow_class=workflow_class, metadata=metadata)
    _workflows[workflow_name] = registration


def get_workflow_class(workflow_name: str) -> Type[Workflow]:
    """Get the workflow class for a workflow."""
    if workflow_name not in _workflows:
        raise ValueError(f"No workflow registered for workflow: {workflow_name}")
    return _workflows[workflow_name].workflow_class


def get_available_workflows() -> List[str]:
    """Get list of all available workflow names."""
    return list(_workflows.keys())


def get_workflow_descriptions() -> Dict[str, str]:
    """Get workflow names and their descriptions."""
    return {
        workflow: registration.metadata.get("description", "No description available")
        for workflow, registration in _workflows.items()
    }


def get_file_patterns_for_workflows(workflows: List[str]) -> List[str]:
    """Get combined file patterns for the specified workflows."""
    all_patterns = set()

    for workflow in workflows:
        if workflow in _workflows:
            patterns = _workflows[workflow].metadata.get("file_patterns", [])
            all_patterns.update(patterns)

    return list(all_patterns)


def is_workflow_available(workflow_name: str) -> bool:
    """Check if a workflow is available."""
    return workflow_name in _workflows


def execute_workflow(workflow_name: str, code: Contextual[str], config: Config) -> List[sarif.Result]:
    """
    Execute a workflow for the given workflow.

    Args:
        workflow_name: Name of the workflow to execute
        content: Content of the file/chunk
        project_path: Path to the project being analyzed
        **kwargs: Additional workflow-specific parameters (including confidence_threshold)

    Returns:
        List of SARIF Result objects
    """
    workflow_class = get_workflow_class(workflow_name)

    # Instantiate the workflow with any required dependencies from kwargs
    workflow_instance = workflow_class(config)

    # Execute the workflow asynchronously
    input = types.SimpleNamespace(code=code, config=config)
    return asyncio.run(workflow_instance.workflow(input))


def workflow(
    workflow_name: str, file_patterns: Optional[List[str]] = None, **metadata: Any
) -> Callable[[Type[Workflow]], Type[Workflow]]:
    """
    Decorator to register a workflow class.

    Usage:
        @workflow('code', file_patterns=['*.py', '*.js', '*.java'])
        class CodeWorkflow(Workflow[WorkflowInputData, List[sarif.Result]]):
            '''Analyzes source code for security vulnerabilities'''

            async def workflow(self, input: WorkflowInputData) -> List[sarif.Result]:
                # Implementation
                pass
    """

    def decorator(workflow_class: Type[Workflow]) -> Type[Workflow]:
        # Use class's docstring as description if not provided in metadata
        if "description" not in metadata and workflow_class.__doc__:
            metadata["description"] = workflow_class.__doc__.strip()

        if file_patterns:
            metadata["file_patterns"] = file_patterns

        register(workflow_name, workflow_class, **metadata)
        return workflow_class

    return decorator
