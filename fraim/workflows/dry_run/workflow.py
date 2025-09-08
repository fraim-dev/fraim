# SPDX-License-Identifier: MIT
# Copyright (c) 2025 Resourcely Inc.

"""
Dry Run Workflow

Dummy workflow for testing purposes. It processes code chunks without performing any actual analysis.
"""

import logging
from dataclasses import dataclass
from typing import List

from fraim.core.workflows import ChunkProcessingOptions, ChunkProcessor
from fraim.outputs import sarif

FILE_PATTERNS = [
    "*.py",
    "*.c",
    "*.cpp",
    "*.h",
    "*.go",
    "*.ts",
    "*.js",
    "*.java",
    "*.rb",
    "*.php",
    "*.swift",
    "*.rs",
    "*.kt",
    "*.scala",
    "*.tsx",
    "*.jsx",
]


@dataclass
class DryRunInput(ChunkProcessingOptions):
    """Input for the DryRun workflow."""

    pass


class DryRunWorkflow(DryRunInput, ChunkProcessor):
    """Dry Run workflow for testing purposes."""

    @property
    def file_patterns(self) -> List[str]:
        """Code file patterns."""
        return FILE_PATTERNS

    async def workflow(self, logger: logging.Logger, args: DryRunInput) -> List[sarif.Result]:
        """Main Code workflow - full control over execution with multi-step processing."""
        project = self.setup_project_input(logger, args)

        for chunk in project:
            logger.debug("DryRun workflow received chunk: %s", chunk)

        return []
