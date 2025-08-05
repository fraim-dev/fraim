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
from .threat_assessment import workflow as threat_assessment_workflow
from .infrastructure_discovery import workflow as infrastructure_discovery_workflow
from .system_analysis import workflow as system_analysis_workflow

__all__ = [
    "WorkflowRegistry",
    "code_workflow",
    "iac_workflow",
    "infrastructure_discovery_workflow",
    "system_analysis_workflow",
]
