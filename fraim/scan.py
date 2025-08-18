# SPDX-License-Identifier: MIT
# Copyright (c) 2025 Resourcely Inc.

from dataclasses import dataclass
from typing import List, Optional

from fraim.config.config import Config
from fraim.observability.manager import ObservabilityManager
from fraim.workflows.registry import execute_workflow


@dataclass
class ScanArgs:
    """Typed dataclass for all fetch arguments with defaults."""

    workflow: str
    workflow_args: Optional[dict] = None


def scan(args: ScanArgs, config: Config, observability_backends: Optional[List[str]] = None) -> None:
    workflow_to_run = args.workflow

    #######################################
    # Run Workflow
    #######################################
    config.logger.info(f"Running workflow: {workflow_to_run}")
    try:
        execute_workflow(workflow_to_run, config, args.workflow_args)
    except Exception as e:
        config.logger.exception(f"Error running {workflow_to_run}: {str(e)}")
