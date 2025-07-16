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
from fraim.workflows.utils import write_sarif_and_html_report

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

    async def process_chunk(self, chunk: CodeChunk, config: Config) -> List[sarif.Result]:
        """Process a single chunk and return its results."""

        # 1. Scan the code for potential vulnerabilities.
        self.config.logger.info("Scanning the code for potential vulnerabilities")
        potential_vulns = await self.scanner_step.run(SASTInput(code=chunk, config=config))

        # 2. Filter vulnerabilities by confidence.
        self.config.logger.info("Filtering vulnerabilities by confidence")
        high_confidence_vulns = filter_results_by_confidence(potential_vulns.results, config.confidence)

        # 3. Triage the high-confidence vulns in parallel.
        self.config.logger.info("Triaging high-confidence vulns in parallel")
        triaged_vulns = await asyncio.gather(
            *[
                self.triager_step.run(TriagerInput(vulnerability=str(vuln), code=chunk, config=config))
                for vuln in high_confidence_vulns
            ]
        )

        # 4. Filter the triaged vulnerabilities by confidence
        self.config.logger.info("Filtering the triaged vulnerabilities by confidence")
        high_confidence_triaged_vulns = filter_results_by_confidence(triaged_vulns, config.confidence)

        return high_confidence_triaged_vulns

    async def workflow(self, input: CodeInput) -> SASTOutput:
        config = self.config
        results: List[sarif.Result] = []

        try:
            kwargs = SimpleNamespace(
                location=input.location, globs=input.globs, limit=input.limit, chunk_size=input.chunk_size
            )
            self.project = ProjectInput(config=config, kwargs=kwargs)

            # Process all chunks in parallel, steps are initialized lazily when first accessed
            all_chunk_results = await asyncio.gather(*[self.process_chunk(chunk, config) for chunk in self.project])

            # Flatten the results from all chunks
            for chunk_results in all_chunk_results:
                results.extend(chunk_results)

        except Exception as e:
            config.logger.error(f"Error during scan: {str(e)}")
            raise e

        write_sarif_and_html_report(
            results=results, repo_name=self.project.repo_name, output_dir=config.output_dir, logger=config.logger
        )

        return results


def filter_results_by_confidence(results: List[sarif.Result], confidence_threshold: int) -> List[sarif.Result]:
    """Filter results by confidence."""
    return [result for result in results if result.properties.confidence >= confidence_threshold]
