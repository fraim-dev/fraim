# SPDX-License-Identifier: MIT
# Copyright (c) 2025 Resourcely Inc.

import asyncio
from dataclasses import dataclass
from typing import List, Optional

from fraim.config.config import Config
from fraim.workflows.registry import get_workflow_class


@dataclass
class ScanArgs:
    """Typed dataclass for all fetch arguments with defaults."""

    workflows: List[str]
    repo: Optional[str] = None
    path: Optional[str] = None
    globs: Optional[List[str]] = None
    limit: Optional[int] = None


def scan(args: ScanArgs, config: Config, observability_backends: Optional[List[str]] = None) -> None:
    # TODO: Update this arg to be a single workflow for the time being
    workflow_to_run = args.workflows[0]

    #######################################
    # Run LLM Workflows
    #######################################
    config.logger.info(f"Running workflow: {workflow_to_run}")

    try:
        workflow_class = get_workflow_class(workflow_to_run)

        # Instantiate the workflow with any required dependencies from kwargs
        workflow_instance = workflow_class(
            config, observability_backends=observability_backends)
        asyncio.run(workflow_instance.workflow(input=args))
    except Exception as e:
        config.logger.error(
            f"Error running {workflow_to_run}: {str(e)}")
