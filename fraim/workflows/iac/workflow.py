# SPDX-License-Identifier: MIT
# Copyright (c) 2025 Resourcely Inc.

"""
Infrastructure as Code (IaC) Security Analysis Workflow

Analyzes IaC files (Terraform, CloudFormation, Kubernetes, Docker, etc.)
for security misconfigurations and compliance issues.
"""

import logging
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Annotated

from fraim.core.contextuals import CodeChunk
from fraim.core.history import History
from fraim.core.parsers import PydanticOutputParser
from fraim.core.prompts.template import PromptTemplate
from fraim.core.steps.llm import LLMStep
from fraim.core.workflows import ChunkProcessingOptions, ChunkProcessor, Workflow
from fraim.core.workflows.llm_processing import LLMMixin, LLMOptions
from fraim.core.workflows.sarif import (
    ConfidenceFilterOptions,
    filter_results_by_confidence,
    write_sarif_and_html_report,
)
from fraim.outputs import sarif

logger = logging.getLogger(__name__)

FILE_PATTERNS = [
    "*.tf",
    "*.tfvars",
    "*.tfstate",
    "*.yaml",
    "*.yml",
    "*.json",
    "Dockerfile",
    ".dockerfile",
    "docker-compose.yml",
    "docker-compose.yaml",
    "*.k8s.yaml",
    "*.k8s.yml",
    "*.ansible.yaml",
    "*.ansible.yml",
    "*.helm.yaml",
    "*.helm.yml",
    "deployment.yaml",
    "deployment.yml",
    "service.yaml",
    "service.yml",
    "ingress.yaml",
    "ingress.yml",
    "configmap.yaml",
    "configmap.yml",
    "secret.yaml",
    "secret.yml",
]

SCANNER_PROMPTS = PromptTemplate.from_yaml(os.path.join(os.path.dirname(__file__), "scanner_prompts.yaml"))


@dataclass
class IaCWorkflowOptions(ChunkProcessingOptions, LLMOptions, ConfidenceFilterOptions):
    """Options for the IaC workflow."""

    output: Annotated[str, {"help": "Path to save the output HTML report"}] = "fraim_output"


@dataclass
class IaCCodeChunkOptions:
    """Options to process a single IaC chunk."""

    code: CodeChunk


class IaCWorkflow(ChunkProcessor[sarif.Result], LLMMixin, Workflow[IaCWorkflowOptions, list[sarif.Result]]):
    """Analyzes IaC files for security vulnerabilities, compliance issues, and best practice deviations."""

    name = "iac"

    def __init__(self, args: IaCWorkflowOptions) -> None:
        super().__init__(args)
        scanner_parser = PydanticOutputParser(sarif.RunResults)
        self.scanner_step: LLMStep[IaCCodeChunkOptions, sarif.RunResults] = LLMStep(
            self.llm, SCANNER_PROMPTS["system"], SCANNER_PROMPTS["user"], scanner_parser
        )

    @property
    def file_patterns(self) -> list[str]:
        """IaC file patterns."""
        return FILE_PATTERNS

    async def _process_single_chunk(self, history: History, chunk: CodeChunk) -> list[sarif.Result]:
        """Process a single chunk with error handling."""
        try:
            # 1. Scan the code for vulnerabilities.
            logger.info(f"Scanning code for vulnerabilities: {Path(chunk.file_path)}")
            iac_input = IaCCodeChunkOptions(code=chunk)
            vulns = await self.scanner_step.run(history, iac_input)

            # 2. Filter the vulnerability by confidence.
            logger.info("Filtering vulnerabilities by confidence")
            high_confidence_vulns = filter_results_by_confidence(vulns.results, self.args.confidence)

            return high_confidence_vulns
        except Exception as e:
            logger.error(
                f"Failed to process chunk {chunk.file_path}:{chunk.line_number_start_inclusive}-{chunk.line_number_end_inclusive}: {e!s}. "
                "Skipping this chunk and continuing with scan."
            )
            return []

    async def run(self) -> list[sarif.Result]:
        """Main IaC workflow - full control over execution."""
        # 1. Setup project input using utility
        project = self.setup_project_input(self.args)

        # 2. Process chunks concurrently using utility
        results = await self.process_chunks_concurrently(
            history=self.history,
            project=project,
            chunk_processor=self._process_single_chunk,
            max_concurrent_chunks=self.args.max_concurrent_chunks,
        )

        # 3. Generate reports (IaC workflow chooses to do this)
        report_paths = write_sarif_and_html_report(
            results=results,
            repo_name=project.repo_name,
            output_dir=self.args.output,
        )

        print(f"Found {len(results)} results.")
        print(f"Wrote SARIF report to {report_paths.sarif_path}")
        print(f"Wrote HTML report to {report_paths.html_path}")

        return results
