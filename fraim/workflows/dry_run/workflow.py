# SPDX-License-Identifier: MIT
# Copyright (c) 2025 Resourcely Inc.

"""
Dry Run Workflow

Dummy workflow for testing purposes. It processes code chunks without performing any actual analysis.
"""

from dataclasses import dataclass
from typing import List

from fraim.core.workflows import ChunkProcessingMixin, Workflow, ChunkWorkflowInput
from fraim.outputs import sarif
from fraim.workflows.registry import workflow

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
class DryRunInput(ChunkWorkflowInput):
    """Input for the DryRun workflow."""
    pass


@workflow("dry_run")
class DryRunWorkflow(ChunkProcessingMixin, Workflow[DryRunInput, List[sarif.Result]]):
    """Dry Run workflow for testing purposes."""

    @property
    def file_patterns(self) -> List[str]:
        """Code file patterns."""
        return FILE_PATTERNS

    async def workflow(self, input: DryRunInput) -> List[sarif.Result]:
        """Main Code workflow - full control over execution with multi-step processing."""
        project = self.setup_project_input(input)

        for chunk in project:
            self.config.logger.debug("DryRun workflow received chunk: %s", chunk)

        return []
