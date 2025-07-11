# SPDX-License-Identifier: MIT
# Copyright (c) 2025 Resourcely Inc.

import asyncio
from dataclasses import dataclass
from typing import List, Optional

from fraim.config.config import Config
from fraim.observability.manager import ObservabilityManager
from fraim.workflows.registry import get_workflow_class, get_workflow_input_class


@dataclass
class ScanArgs:
    """Typed dataclass for all fetch arguments with defaults."""

    workflow: str
    workflow_args: Optional[dict] = None


def scan(args: ScanArgs, config: Config, observability_backends: Optional[List[str]] = None) -> None:
    workflow_to_run = args.workflow

    if observability_backends:
        try:
            manager = ObservabilityManager(observability_backends, logger=config.logger)
            manager.setup()
        except Exception as e:
            config.logger.warning(f"Failed to setup observability in worker process: {str(e)}")

    #######################################
    # Run LLM Workflows
    #######################################
    config.logger.info(f"Running workflow: {workflow_to_run}")

    try:
        workflow_class = get_workflow_class(workflow_to_run)
        input_class = get_workflow_input_class(workflow_to_run)

        # Create input object with workflow-specific arguments
        input_kwargs = {"config": config, **(args.workflow_args or {})}

        workflow_input = input_class(**input_kwargs)
        workflow_instance = workflow_class(config)
        asyncio.run(workflow_instance.workflow(workflow_input))
    except Exception as e:
        config.logger.error(f"Error running {workflow_to_run}: {str(e)}")
