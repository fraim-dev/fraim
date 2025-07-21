# SPDX-License-Identifier: MIT
# Copyright (c) 2025 Resourcely Inc.

"""
Infrastructure as Code (IaC) Security Analysis Workflow

Analyzes IaC files (Terraform, CloudFormation, Kubernetes, Docker, etc.)
for security misconfigurations and compliance issues.
"""

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Annotated, Any, List, Optional

from fraim.config import Config
from fraim.core.contextuals import CodeChunk
from fraim.core.llms.litellm import LiteLLM
from fraim.core.parsers import PydanticOutputParser
from fraim.core.prompts.template import PromptTemplate
from fraim.core.steps.llm import LLMStep
from fraim.core.workflows import ChunkProcessingMixin, ChunkWorkflowInput, Workflow
from fraim.outputs import sarif
from fraim.workflows.registry import workflow
from fraim.workflows.utils import filter_results_by_confidence, write_sarif_and_html_report

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
class IaCInput(ChunkWorkflowInput):
    """Input for the IaC workflow."""

    pass


@dataclass
class IaCCodeChunkInput:
    """Input for processing a single IaC chunk."""

    code: CodeChunk
    config: Config


@workflow("iac")
class IaCWorkflow(ChunkProcessingMixin, Workflow[IaCInput, List[sarif.Result]]):
    """Analyzes IaC files for security vulnerabilities, compliance issues, and best practice deviations."""

    def __init__(self, config: Config, *args: Any, **kwargs: Any) -> None:
        super().__init__(config, *args, **kwargs)

        # Construct an LLM instance
        llm = LiteLLM.from_config(config)

        # Construct the Scanner Step
        scanner_parser = PydanticOutputParser(sarif.RunResults)
        self.scanner_step: LLMStep[IaCCodeChunkInput, sarif.RunResults] = LLMStep(
            llm, SCANNER_PROMPTS["system"], SCANNER_PROMPTS["user"], scanner_parser
        )

    @property
    def file_patterns(self) -> List[str]:
        """IaC file patterns."""
        return FILE_PATTERNS

    async def _process_single_chunk(self, chunk: CodeChunk) -> List[sarif.Result]:
        """Process a single chunk with error handling."""
        try:
            # 1. Scan the code for vulnerabilities.
            self.config.logger.info(f"Scanning code for vulnerabilities: {Path(chunk.file_path)}")
            iac_input = IaCCodeChunkInput(code=chunk, config=self.config)
            vulns = await self.scanner_step.run(iac_input)

            # 2. Filter the vulnerability by confidence.
            self.config.logger.info("Filtering vulnerabilities by confidence")
            high_confidence_vulns = filter_results_by_confidence(vulns.results, self.config.confidence)

            return high_confidence_vulns
        except Exception as e:
            self.config.logger.error(
                f"Failed to process chunk {chunk.file_path}:{chunk.line_number_start_inclusive}-{chunk.line_number_end_inclusive}: {str(e)}. "
                "Skipping this chunk and continuing with scan."
            )
            return []

    async def workflow(self, input: IaCInput) -> List[sarif.Result]:
        """Main IaC workflow - full control over execution."""
        try:
            # 1. Setup project input using utility
            project = self.setup_project_input(input)

            # 2. Process chunks concurrently using utility
            results = await self.process_chunks_concurrently(
                project=project,
                chunk_processor=self._process_single_chunk,
                max_concurrent_chunks=input.max_concurrent_chunks,
            )

            # 3. Generate reports (IaC workflow chooses to do this)
            write_sarif_and_html_report(
                results=results,
                repo_name=project.repo_name,
                output_dir=self.config.output_dir,
                logger=self.config.logger,
            )

            return results

        except Exception as e:
            self.config.logger.error(f"Error during IaC scan: {str(e)}")
            raise e
