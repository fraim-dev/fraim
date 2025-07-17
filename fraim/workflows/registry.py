# SPDX-License-Identifier: MIT
# Copyright (c) 2025 Resourcely Inc.

"""
Workflow Registry System

This module provides a centralized registry for all workflows, allowing easy
addition of new workflows without modifying core routing logic.
"""

import asyncio
import dataclasses
import sys
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Type, Union, get_args, get_origin, get_type_hints

# Add this import for Python 3.9+ compatibility
if sys.version_info >= (3, 9):
    from typing import Annotated
else:
    from typing_extensions import Annotated

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


def is_workflow_available(workflow_name: str) -> bool:
    """Check if a workflow is available."""
    return workflow_name in _workflows


def execute_workflow(
    workflow_name: str, config: Config, workflow_args: Optional[Dict[str, Any]] = None
) -> List[sarif.Result]:
    """Execute a workflow with workflow-specific arguments."""
    workflow_class = get_workflow_class(workflow_name)
    input_class = get_workflow_input_class(workflow_name)

    # Create input object with workflow-specific arguments
    input_kwargs = {"config": config, **(workflow_args or {})}

    workflow_input = input_class(**input_kwargs)
    workflow_instance = workflow_class(config)

    return asyncio.run(workflow_instance.workflow(workflow_input))


def workflow(workflow_name: str, **metadata: Any) -> Callable[[Type[Workflow]], Type[Workflow]]:
    """
    Decorator to register a workflow class.

    Usage:
        @workflow('code')
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

        register(workflow_name, workflow_class, **metadata)
        return workflow_class

    return decorator


def get_workflow_input_class(workflow_name: str) -> Type:
    """Get the input dataclass for a workflow."""
    workflow_class = get_workflow_class(workflow_name)
    # Get the first type parameter from Workflow[InputType, OutputType]

    # Try to extract the input type from the generic base class
    orig_bases = getattr(workflow_class, "__orig_bases__", ())
    for base in orig_bases:
        origin = get_origin(base)
        if origin is not None:
            args = get_args(base)
            if args:
                input_type = args[0]
                if isinstance(input_type, type):
                    return input_type  # Return the InputType
    raise ValueError(f"No input dataclass found for workflow: {workflow_name}")


def infer_cli_args_from_dataclass(input_class: Type) -> List[Dict[str, Any]]:
    """Infer CLI arguments from a dataclass."""
    if not dataclasses.is_dataclass(input_class):
        return []

    cli_args = []
    type_hints = get_type_hints(input_class, include_extras=True)

    # Reserved fields that shouldn't become CLI arguments
    reserved_fields = {"config"}

    for field in dataclasses.fields(input_class):
        if field.name in reserved_fields:
            continue

        field_type = type_hints.get(field.name, str)
        arg_config: Dict[str, Any] = {
            "name": f"--{field.name.replace('_', '-')}",
            "help": f"{field.name.replace('_', ' ').title()}",
        }

        # Extract metadata from Annotated types
        annotation_metadata = {}
        actual_type = field_type

        # Check if this is an Annotated type
        if get_origin(field_type) is Annotated:
            args = get_args(field_type)
            if args:
                actual_type = args[0]  # The actual type is the first argument
                # The metadata is in the remaining arguments
                for metadata_item in args[1:]:
                    if isinstance(metadata_item, dict):
                        annotation_metadata.update(metadata_item)

        # Handle different field types (use actual_type instead of field_type)
        if actual_type == bool:
            if field.default is False:
                arg_config["action"] = "store_true"
            elif field.default is True:
                arg_config["action"] = "store_false"
        elif actual_type == int:
            arg_config["type"] = int
        elif actual_type == float:
            arg_config["type"] = float
        elif get_origin(actual_type) is list:
            arg_config["nargs"] = "+"
        elif get_origin(actual_type) is Union:
            # Handle Optional[T] which is Union[T, None]
            args = get_args(actual_type)
            if len(args) == 2 and type(None) in args:
                non_none_type = args[0] if args[1] is type(None) else args[1]
                if non_none_type == int:
                    arg_config["type"] = int
                elif non_none_type == float:
                    arg_config["type"] = float
                elif get_origin(non_none_type) is list:
                    # Handle Optional[List[T]] - e.g., Optional[List[str]]
                    arg_config["nargs"] = "+"

        # Set default value
        if field.default is not dataclasses.MISSING:
            arg_config["default"] = field.default
        elif field.default_factory is not dataclasses.MISSING:
            arg_config["default"] = field.default_factory()

        # Apply metadata from annotations (this takes precedence)
        if annotation_metadata:
            if "choices" in annotation_metadata:
                arg_config["choices"] = annotation_metadata["choices"]
            if "help" in annotation_metadata:
                arg_config["help"] = annotation_metadata["help"]

        # Fallback to dataclass field metadata
        if hasattr(field, "metadata"):
            if "choices" in field.metadata and "choices" not in arg_config:
                arg_config["choices"] = field.metadata["choices"]
            if "help" in field.metadata and "help" not in arg_config:
                arg_config["help"] = field.metadata["help"]

        cli_args.append(arg_config)

    return cli_args


def get_workflow_cli_args(workflow_name: str) -> List[Dict[str, Any]]:
    """Get CLI arguments for a specific workflow by introspecting its input dataclass."""
    input_class = get_workflow_input_class(workflow_name)
    if input_class:
        return infer_cli_args_from_dataclass(input_class)
    return []


def get_all_workflow_cli_args() -> Dict[str, List[Dict[str, Any]]]:
    """Get CLI arguments for all workflows."""
    return {workflow: get_workflow_cli_args(workflow) for workflow in get_available_workflows()}
