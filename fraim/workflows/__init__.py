# SPDX-License-Identifier: MIT
# Copyright (c) 2025 Resourcely Inc.

"""
Workflows Module

This module automatically loads and registers all available workflows.
When imported, it discovers and registers all workflow modules.
"""

# Import workflow registry
from . import registry as WorkflowRegistry

# Import all workflows to trigger their registration
from .code import workflow as code_workflow
from .iac import workflow as iac_workflow

__all__ = [
    "WorkflowRegistry",
]
