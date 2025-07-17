# SPDX-License-Identifier: MIT
# Copyright (c) 2025 Resourcely Inc.

"""
Infrastructure as Code (IaC) Security Analysis Workflow

Analyzes IaC files (Terraform, CloudFormation, Kubernetes, Docker, etc.)
for security misconfigurations and compliance issues.
"""

import asyncio
import os
from dataclasses import dataclass, field
from pathlib import Path
from types import SimpleNamespace
from typing import Annotated, Any, List, Optional

from fraim.config import Config
from fraim.core.contextuals import CodeChunk
from fraim.core.llms.litellm import LiteLLM
from fraim.core.parsers import PydanticOutputParser
from fraim.core.prompts.template import PromptTemplate
from fraim.core.steps.llm import LLMStep
from fraim.core.workflows import Workflow
from fraim.inputs.project import ProjectInput
from fraim.outputs import sarif
from fraim.workflows.registry import workflow
from fraim.workflows.utils import write_sarif_and_html_report

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
class IaCInput:
    """Input for the IaC workflow."""

    config: Config
    location: Annotated[str, {"help": "Repository URL or path to scan"}]
    # File processing
    chunk_size: Annotated[Optional[int], {"help": "Number of lines per chunk"}] = 500
    limit: Annotated[Optional[int], {"help": "Limit the number of files to scan"}] = None
    globs: Annotated[
        Optional[List[str]],
        {"help": "Globs to use for file scanning. If not provided, will use file_patterns defined in the workflow."},
    ] = field(default_factory=lambda: FILE_PATTERNS)
    max_concurrent_chunks: Annotated[int, {"help": "Maximum number of chunks to process concurrently"}] = 5


@dataclass
class IaCCodeChunkInput:
    """Input for the IaC workflow."""

    code: CodeChunk
    config: Config


type IaCOutput = List[sarif.Result]


@workflow("iac")
class IaCWorkflow(Workflow[IaCInput, IaCOutput]):
    """Analyzes IaC files for security vulnerabilities, compliance issues, and best practice deviations."""

    def __init__(self, config: Config, *args: Any, **kwargs: Any) -> None:
        self.config = config

        # Construct an LLM instance
        llm = LiteLLM.from_config(config)

        # Construct the Scanner Step
        scanner_llm = llm
        scanner_parser = PydanticOutputParser(sarif.RunResults)
        self.scanner_step: LLMStep[IaCCodeChunkInput, sarif.RunResults] = LLMStep(
            scanner_llm, SCANNER_PROMPTS["system"], SCANNER_PROMPTS["user"], scanner_parser
        )

    async def process_chunk(self, chunk: CodeChunk, config: Config) -> List[sarif.Result]:
        """Process a single chunk and return its results."""

        try:
            # 1. Scan the code for vulnerabilities.
            self.config.logger.info(f"Scanning code for vulnerabilities: {Path(chunk.file_path)}")
            iac_input = IaCCodeChunkInput(code=chunk, config=config)
            vulns = await self.scanner_step.run(iac_input)

            # 2. Filter the vulnerability by confidence.
            self.config.logger.info("Filtering vulnerabilities by confidence")
            high_confidence_vulns = filter_results_by_confidence(vulns.results, config.confidence)

            return high_confidence_vulns
        except Exception as e:
            self.config.logger.error(
                f"Failed to process chunk {chunk.file_path}:{chunk.line_number_start_inclusive}-{chunk.line_number_end_inclusive}: {str(e)}. "
                "Skipping this chunk and continuing with scan."
            )
            return []

    async def workflow(self, input: IaCInput) -> IaCOutput:
        config = self.config
        results: List[sarif.Result] = []

        try:
            kwargs = SimpleNamespace(
                location=input.location, globs=input.globs, limit=input.limit, chunk_size=input.chunk_size
            )
            project = ProjectInput(config=config, kwargs=kwargs)

            # Create semaphore to limit concurrent chunk processing
            max_concurrent_chunks = input.max_concurrent_chunks or 5
            semaphore = asyncio.Semaphore(max_concurrent_chunks)

            async def process_chunk_with_semaphore(chunk: CodeChunk) -> List[sarif.Result]:
                """Process a chunk with semaphore to limit concurrency."""
                async with semaphore:
                    return await self.process_chunk(chunk, config)

            # Process chunks as they stream in from the ProjectInput iterator
            active_tasks = set()

            for chunk in project:
                # Create task for this chunk and add to active tasks
                task = asyncio.create_task(process_chunk_with_semaphore(chunk))
                active_tasks.add(task)

                # If we've hit our concurrency limit, wait for some tasks to complete
                if len(active_tasks) >= max_concurrent_chunks:
                    done, active_tasks = await asyncio.wait(active_tasks, return_when=asyncio.FIRST_COMPLETED)
                    for completed_task in done:
                        chunk_results = await completed_task
                        results.extend(chunk_results)

            # Wait for any remaining tasks to complete
            if active_tasks:
                for future in asyncio.as_completed(active_tasks):
                    chunk_results = await future
                    results.extend(chunk_results)

        except Exception as e:
            config.logger.error(f"Error during scan: {str(e)}")
            raise e

        write_sarif_and_html_report(
            results=results, repo_name=project.repo_name, output_dir=config.output_dir, logger=config.logger
        )

        return results


def filter_results_by_confidence(results: List[sarif.Result], confidence_threshold: int) -> List[sarif.Result]:
    """Filter results by confidence."""
    return [result for result in results if result.properties.confidence > confidence_threshold]
