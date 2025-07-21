# SPDX-License-Identifier: MIT
# Copyright (c) 2025 Resourcely Inc.

"""
Code Security Analysis Workflow

Analyzes source code for security vulnerabilities using AI-powered scanning.
"""

import asyncio
import os
from dataclasses import dataclass, field
from typing import Annotated, Any, List, Optional

from fraim.config import Config
from fraim.core.contextuals import CodeChunk
from fraim.core.llms.litellm import LiteLLM
from fraim.core.parsers import PydanticOutputParser
from fraim.core.prompts.template import PromptTemplate
from fraim.core.steps.llm import LLMStep
from fraim.core.workflows import ChunkProcessingMixin, ChunkWorkflowInput, Workflow
from fraim.outputs import sarif
from fraim.tools.tree_sitter import TreeSitterTools
from fraim.util.pydantic import merge_models
from fraim.workflows.registry import workflow
from fraim.workflows.utils import filter_results_by_confidence, write_sarif_and_html_report

from . import triage_sarif_overlay

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

SCANNER_PROMPTS = PromptTemplate.from_yaml(os.path.join(os.path.dirname(__file__), "scanner_prompts.yaml"))
TRIAGER_PROMPTS = PromptTemplate.from_yaml(os.path.join(os.path.dirname(__file__), "triager_prompts.yaml"))

triage_sarif = merge_models(sarif, triage_sarif_overlay)


@dataclass
class CodeInput(ChunkWorkflowInput):
    """Input for the Code workflow."""

    # Code-specific parameter
    max_concurrent_triagers: Annotated[
        int, {"help": "Maximum number of triager requests per chunk to run concurrently"}
    ] = 3


@dataclass
class SASTInput:
    """Input for the SAST scanner step."""

    code: CodeChunk
    config: Config


@dataclass
class TriagerInput:
    """Input for the triage step."""

    vulnerability: str
    code: CodeChunk
    config: Config


@workflow("code")
class SASTWorkflow(ChunkProcessingMixin, Workflow[CodeInput, List[sarif.Result]]):
    """Analyzes source code for security vulnerabilities"""

    def __init__(self, config: Config, *args: Any, **kwargs: Any) -> None:
        super().__init__(config, *args, **kwargs)

        # Initialize LLM and scanner step immediately
        self.llm = LiteLLM.from_config(self.config)
        scanner_parser = PydanticOutputParser(sarif.RunResults)
        self.scanner_step: LLMStep[SASTInput, sarif.RunResults] = LLMStep(
            self.llm, SCANNER_PROMPTS["system"], SCANNER_PROMPTS["user"], scanner_parser
        )

        # Keep triager step as lazy since it depends on project setup
        self._triager_step: Optional[LLMStep[TriagerInput, sarif.Result]] = None

    @property
    def file_patterns(self) -> List[str]:
        """Code file patterns."""
        return FILE_PATTERNS

    @property
    def triager_step(self) -> LLMStep[TriagerInput, sarif.Result]:
        """Lazily initialize the triager step."""
        if self._triager_step is None:
            if (
                not hasattr(self, "project")
                or not self.project
                or not hasattr(self.project, "project_path")
                or self.project.project_path is None
            ):
                raise ValueError("project_path must be set before accessing triager_step")

            triager_tools = TreeSitterTools(self.project.project_path).tools
            triager_llm = self.llm.with_tools(triager_tools)
            triager_parser = PydanticOutputParser(triage_sarif.Result)
            self._triager_step = LLMStep(
                triager_llm, TRIAGER_PROMPTS["system"], TRIAGER_PROMPTS["user"], triager_parser
            )
        return self._triager_step

    async def _process_single_chunk(self, chunk: CodeChunk, max_concurrent_triagers: int) -> List[sarif.Result]:
        """Process a single chunk with multi-step processing and error handling."""
        try:
            # 1. Scan the code for potential vulnerabilities.
            self.config.logger.debug("Scanning the code for potential vulnerabilities")
            potential_vulns = await self.scanner_step.run(SASTInput(code=chunk, config=self.config))

            # 2. Filter vulnerabilities by confidence.
            self.config.logger.debug("Filtering vulnerabilities by confidence")
            high_confidence_vulns = filter_results_by_confidence(potential_vulns.results, self.config.confidence)

            # 3. Triage the high-confidence vulns with limited concurrency.
            self.config.logger.debug("Triaging high-confidence vulns with limited concurrency")

            # Create semaphore to limit concurrent triager requests
            triager_semaphore = asyncio.Semaphore(max_concurrent_triagers)

            async def triage_with_semaphore(vuln: sarif.Result) -> Optional[sarif.Result]:
                """Triage a vulnerability with semaphore to limit concurrency."""
                async with triager_semaphore:
                    return await self.triager_step.run(
                        TriagerInput(vulnerability=str(vuln), code=chunk, config=self.config)
                    )

            triaged_results = await asyncio.gather(*[triage_with_semaphore(vuln) for vuln in high_confidence_vulns])

            # Filter out None results from failed triaging attempts
            triaged_vulns = [result for result in triaged_results if result is not None]

            # 4. Filter the triaged vulnerabilities by confidence
            self.config.logger.debug("Filtering the triaged vulnerabilities by confidence")
            high_confidence_triaged_vulns = filter_results_by_confidence(triaged_vulns, self.config.confidence)

            return high_confidence_triaged_vulns

        except Exception as e:
            self.config.logger.error(
                f"Failed to process chunk {chunk.file_path}:{chunk.line_number_start_inclusive}-{chunk.line_number_end_inclusive}: {str(e)}. "
                "Skipping this chunk and continuing with scan."
            )
            return []

    async def workflow(self, input: CodeInput) -> List[sarif.Result]:
        """Main Code workflow - full control over execution with multi-step processing."""
        try:
            # 1. Setup project input using utility
            self.project = self.setup_project_input(input)

            # 2. Create a closure that captures max_concurrent_triagers
            async def chunk_processor(chunk: CodeChunk) -> List[sarif.Result]:
                return await self._process_single_chunk(chunk, input.max_concurrent_triagers)

            # 3. Process chunks concurrently using utility
            results = await self.process_chunks_concurrently(
                project=self.project, chunk_processor=chunk_processor, max_concurrent_chunks=input.max_concurrent_chunks
            )

            # 4. Generate reports
            write_sarif_and_html_report(
                results=results,
                repo_name=self.project.repo_name,
                output_dir=self.config.output_dir,
                logger=self.config.logger,
            )

            return results

        except Exception as e:
            self.config.logger.error(f"Error during code scan: {str(e)}")
            raise e
