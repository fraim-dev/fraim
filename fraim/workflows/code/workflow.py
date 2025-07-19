# SPDX-License-Identifier: MIT
# Copyright (c) 2025 Resourcely Inc.

"""
Code Security Analysis Workflow

Analyzes source code for security vulnerabilities using AI-powered scanning.
"""

import asyncio
import os
from dataclasses import dataclass, field
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
from fraim.tools.tree_sitter import TreeSitterTools
from fraim.util.pydantic import merge_models
from fraim.workflows.registry import workflow
from fraim.workflows.utils import filter_results_by_confidence, write_sarif_and_html_report

from . import triage_sarif_overlay

FILE_PATTERNS = [
    "*.tf",
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

SCANNER_PROMPTS = PromptTemplate.from_yaml(os.path.join(os.path.dirname(__file__), "scanner_prompts.yaml"))
TRIAGER_PROMPTS = PromptTemplate.from_yaml(os.path.join(os.path.dirname(__file__), "triager_prompts.yaml"))

triage_sarif = merge_models(sarif, triage_sarif_overlay)


@dataclass
class CodeInput:
    """Input for the Code workflow."""

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
class SASTInput:
    """Input for the SAST workflow."""

    code: CodeChunk
    config: Config


@dataclass
class TriagerInput:
    """Input for the triage step of the SAST workflow."""

    vulnerability: str
    code: CodeChunk
    config: Config


type SASTOutput = List[sarif.Result]


@workflow("code")
class SASTWorkflow(Workflow[CodeInput, SASTOutput]):
    """Analyzes source code for security vulnerabilities"""

    def __init__(self, config: Config, *args: Any, **kwargs: Any) -> None:
        self.config = config

        # Only store what we need for lazy initialization
        self._llm: Optional[LiteLLM] = None
        self._scanner_step: Optional[LLMStep[SASTInput, sarif.RunResults]] = None
        self._triager_step: Optional[LLMStep[TriagerInput, sarif.Result]] = None

    @property
    def llm(self) -> LiteLLM:
        """Lazily initialize the LLM instance."""
        if self._llm is None:
            self._llm = LiteLLM.from_config(self.config)
        return self._llm

    @property
    def scanner_step(self) -> LLMStep[SASTInput, sarif.RunResults]:
        """Lazily initialize the scanner step."""
        if self._scanner_step is None:
            scanner_parser = PydanticOutputParser(sarif.RunResults)
            self._scanner_step = LLMStep(self.llm, SCANNER_PROMPTS["system"], SCANNER_PROMPTS["user"], scanner_parser)
        return self._scanner_step

    @property
    def triager_step(self) -> LLMStep[TriagerInput, sarif.Result]:
        """Lazily initialize the triager step."""
        if self._triager_step is None:
            if not self.project or not hasattr(self.project, "project_path") or self.project.project_path is None:
                raise ValueError("project_path must be set before accessing triager_step")

            triager_tools = TreeSitterTools(self.project.project_path).tools
            triager_llm = self.llm.with_tools(triager_tools)
            triager_parser = PydanticOutputParser(triage_sarif.Result)
            self._triager_step = LLMStep(
                triager_llm, TRIAGER_PROMPTS["system"], TRIAGER_PROMPTS["user"], triager_parser
            )
        return self._triager_step

    async def process_chunk(self, chunk: CodeChunk, config: Config, max_concurrent_triagers: int) -> List[sarif.Result]:
        """Process a single chunk and return its results."""

        try:
            # 1. Scan the code for potential vulnerabilities.
            self.config.logger.debug("Scanning the code for potential vulnerabilities")
            potential_vulns = await self.scanner_step.run(SASTInput(code=chunk, config=config))

            # 2. Filter vulnerabilities by confidence.
            self.config.logger.debug("Filtering vulnerabilities by confidence")
            high_confidence_vulns = filter_results_by_confidence(potential_vulns.results, config.confidence)

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

    async def workflow(self, input: CodeInput) -> SASTOutput:
        config = self.config
        results: List[sarif.Result] = []

        try:
            kwargs = SimpleNamespace(
                location=input.location, globs=input.globs, limit=input.limit, chunk_size=input.chunk_size
            )
            self.project = ProjectInput(config=config, kwargs=kwargs)

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
