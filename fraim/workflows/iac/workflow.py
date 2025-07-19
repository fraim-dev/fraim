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
from fraim.workflows.utils import filter_results_by_confidence, write_sarif_and_html_report
from fraim.tools.tree_sitter import TreeSitterTools
from fraim.tools.terraform_tools import TerraformTools
from fraim.util.pydantic import merge_models

from . import triage_sarif_overlay

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
TRIAGER_PROMPTS = PromptTemplate.from_yaml(os.path.join(os.path.dirname(__file__), "triager_prompts.yaml"))

triage_sarif = merge_models(sarif, triage_sarif_overlay)

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
    max_concurrent_triagers: Annotated[
        int, {"help": "Maximum number of triager requests per chunk to run concurrently"}
    ] = 3

@dataclass
class IaCCodeChunkInput:
    """Input for the IaC workflow."""

    code: CodeChunk
    config: Config

@dataclass
class TriagerInput:
    """Input for the triage step of the SAST workflow."""

    vulnerability: str
    code: CodeChunk
    config: Config

type IaCOutput = List[sarif.Result]


@workflow("iac")
class IaCWorkflow(Workflow[IaCInput, IaCOutput]):
    """Analyzes IaC files for security vulnerabilities, compliance issues, and best practice deviations."""

    def __init__(self, config: Config, *args: Any, **kwargs: Any) -> None:
        self.config = config

        # Only store what we need for lazy initialization
        self._llm: Optional[LiteLLM] = None
        self._scanner_step: Optional[LLMStep[IaCCodeChunkInput, sarif.RunResults]] = None
        self._triager_step: Optional[LLMStep[TriagerInput, sarif.Result]] = None
    
    @property
    def llm(self) -> LiteLLM:
        """Lazily initialize the LLM instance."""
        if self._llm is None:
            self._llm = LiteLLM.from_config(self.config)
        return self._llm

    @property
    def scanner_step(self) -> LLMStep[IaCCodeChunkInput, sarif.RunResults]:
        """Lazily initialize the scanner step."""
        if self._scanner_step is None:
            if not self.project:
                raise ValueError("project must be set before accessing scanner_step")
            if not hasattr(self.project, "project_path"):
                raise ValueError("project must have project_path attribute before accessing scanner_step")
            if self.project.project_path is None or not self.project.project_path.strip():
                raise ValueError(f"project_path must be set to a non-empty value before accessing scanner_step. Current value: '{self.project.project_path}'")

            # Provide tools to scanner step for input tracing
            tree_sitter_tools = TreeSitterTools(self.project.project_path).tools
            terraform_tools = TerraformTools().tools
            all_tools = tree_sitter_tools + terraform_tools
            
            scanner_llm = self.llm.with_tools(all_tools)
            scanner_parser = PydanticOutputParser(sarif.RunResults)
            self._scanner_step = LLMStep(scanner_llm, SCANNER_PROMPTS["system"], SCANNER_PROMPTS["user"], scanner_parser)
        return self._scanner_step
    
    @property
    def triager_step(self) -> LLMStep[TriagerInput, sarif.Result]:
        """Lazily initialize the triager step."""
        if self._triager_step is None:
            if not self.project:
                raise ValueError("project must be set before accessing triager_step")
            if not hasattr(self.project, "project_path"):
                raise ValueError("project must have project_path attribute before accessing triager_step")
            if self.project.project_path is None or not self.project.project_path.strip():
                raise ValueError(f"project_path must be set to a non-empty value before accessing triager_step. Current value: '{self.project.project_path}'")

            # Combine TreeSitter tools with Terraform-specific tools
            tree_sitter_tools = TreeSitterTools(self.project.project_path).tools
            terraform_tools = TerraformTools().tools
            all_tools = tree_sitter_tools + terraform_tools
            
            triager_llm = self.llm.with_tools(all_tools)
            triager_parser = PydanticOutputParser(triage_sarif.Result)
            self._triager_step = LLMStep(
                triager_llm, TRIAGER_PROMPTS["system"], TRIAGER_PROMPTS["user"], triager_parser
            )
        return self._triager_step

    async def process_chunk(self, chunk: CodeChunk, config: Config, max_concurrent_triagers: int) -> List[sarif.Result]:
        """Process a single chunk and return its results."""

        try:
            # 1. Scan the code for vulnerabilities.
            self.config.logger.info(f"Scanning code for vulnerabilities: {Path(chunk.file_path)}")
            iac_input = IaCCodeChunkInput(code=chunk, config=config)
            vulns = await self.scanner_step.run(iac_input)

            # 2. Filter the vulnerability by confidence.
            self.config.logger.info("Filtering vulnerabilities by confidence")
            high_confidence_vulns = filter_results_by_confidence(vulns.results, config.confidence)

                        # 3. Triage the high-confidence vulns with limited concurrency.
            self.config.logger.debug("Triaging high-confidence vulns with limited concurrency")

            # Create semaphore to limit concurrent triager requests
            triager_semaphore = asyncio.Semaphore(max_concurrent_triagers)

            async def triage_with_semaphore(vuln: sarif.Result) -> Optional[sarif.Result]:
                """Triage a vulnerability with semaphore to limit concurrency."""
                async with triager_semaphore:
                    return await self.triager_step.run(TriagerInput(vulnerability=str(vuln), code=chunk, config=config))

            triaged_results = await asyncio.gather(*[triage_with_semaphore(vuln) for vuln in high_confidence_vulns])

            # Filter out None results from failed triaging attempts
            triaged_vulns = [result for result in triaged_results if result is not None]

            # 4. Filter the triaged vulnerabilities by confidence
            self.config.logger.debug("Filtering the triaged vulnerabilities by confidence")
            high_confidence_triaged_vulns = filter_results_by_confidence(triaged_vulns, config.confidence)

            return high_confidence_triaged_vulns
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
            # Debug logging to understand the input
            config.logger.debug(f"IaC workflow input location: '{input.location}'")
            config.logger.debug(f"IaC workflow kwargs location: '{kwargs.location}'")
            
            self.project = ProjectInput(config=config, kwargs=kwargs)
            
            # Debug logging to understand project_path
            config.logger.debug(f"ProjectInput project_path: '{self.project.project_path}'")
            config.logger.debug(f"ProjectInput repo_name: '{self.project.repo_name}'")

            # Create semaphore to limit concurrent chunk processing
            max_concurrent_chunks = input.max_concurrent_chunks or 5
            semaphore = asyncio.Semaphore(max_concurrent_chunks)

            async def process_chunk_with_semaphore(chunk: CodeChunk) -> List[sarif.Result]:
                """Process a chunk with semaphore to limit concurrency."""
                async with semaphore:
                    return await self.process_chunk(chunk, config, input.max_concurrent_triagers or 3)

            # Process chunks as they stream in from the ProjectInput iterator
            active_tasks = set()

            for chunk in self.project:
                # Skip files in .terraform/ directories (Terraform cache/plugin directories)
                if "/.terraform/" in chunk.file_path or chunk.file_path.startswith(".terraform/"):
                    self.config.logger.debug(f"Skipping file in .terraform/ directory: {chunk.file_path}")
                    continue
                
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
            results=results, repo_name=self.project.repo_name, output_dir=config.output_dir, logger=config.logger
        )

        return results
