# SPDX-License-Identifier: MIT
# Copyright (c) 2025 Resourcely Inc.

"""
Workflows Module

This module automatically loads and registers all available workflows.
When imported, it discovers and registers all workflow modules.
"""

# Import workflow registry
from . import registry as WorkflowRegistry
from .api_interface_discovery import workflow as api_interface_discovery_workflow
from .api_vulnerability import workflow as api_vulnerability_workflow

# Import all workflows to trigger their registration
from .code import workflow as code_workflow
from .iac import workflow as iac_workflow
from .infrastructure_discovery import workflow as infrastructure_discovery_workflow
from .system_analysis import workflow as system_analysis_workflow

__all__ = [
    "WorkflowRegistry",
    "code_workflow",
    "iac_workflow",
    "infrastructure_discovery_workflow",
    "api_interface_discovery_workflow",
    "api_vulnerability_workflow",
    "system_analysis_workflow",
]
