# SPDX-License-Identifier: MIT
# Copyright (c) 2025 Resourcely Inc.

"""
Code Security Analysis Workflow

Analyzes source code for security vulnerabilities using AI-powered scanning.
"""

import asyncio
import logging
import os
from dataclasses import dataclass
from typing import Any, List

from fraim.config import Config
from fraim.core.contextuals import CodeChunk
from fraim.core.llms.litellm import LiteLLM
from fraim.core.parsers import PydanticOutputParser
from fraim.core.prompts.template import PromptTemplate
from fraim.core.steps.llm import LLMStep
from fraim.core.workflows import Workflow
from fraim.outputs import sarif
from fraim.tools.tree_sitter import TreeSitterTools
from fraim.util.pydantic import merge_models
from fraim.workflows.registry import workflow

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


@workflow("code", file_patterns=FILE_PATTERNS)
class SASTWorkflow(Workflow[SASTInput, SASTOutput]):
    """Analyzes source code for security vulnerabilities"""

    def __init__(self, config: Config, *args: Any, **kwargs: Any) -> None:
        # Construct an LLM instance
        llm = LiteLLM.from_config(config)

        # Construct the Scanner Step
        scanner_llm = llm
        scanner_parser = PydanticOutputParser(sarif.RunResults)
        self.scanner_step: LLMStep[SASTInput, sarif.RunResults] = LLMStep(
            scanner_llm, SCANNER_PROMPTS["system"], SCANNER_PROMPTS["user"], scanner_parser
        )

        # Construct the Triager Step
        triager_tools = TreeSitterTools(config.project_path).tools
        triager_llm = llm.with_tools(triager_tools)
        triager_parser = PydanticOutputParser(triage_sarif.Result)
        self.triager_step: LLMStep[TriagerInput, sarif.Result] = LLMStep(
            triager_llm, TRIAGER_PROMPTS["system"], TRIAGER_PROMPTS["user"], triager_parser
        )

    async def workflow(self, input: SASTInput) -> SASTOutput:
        # 1. Scan the code for potential vulnerabilities.
        logging.getLogger().info("Scanning the code for potential vulnerabilities")
        sast_input = SASTInput(code=input.code, config=input.config)
        potential_vulns = await self.scanner_step.run(sast_input)

        # 2. Filter vulnerabilities by confidence.
        logging.getLogger().info("Filtering vulnerabilities by confidence")
        high_confidence_vulns = filter_results_by_confidence(potential_vulns.results, input.config.confidence)

        # 3. Triage the high-confidence vulns in parallel.
        logging.getLogger().info("Triaging high-confidence vulns in parallel")
        triaged_vulns = await asyncio.gather(
            *[
                self.triager_step.run(TriagerInput(vulnerability=str(vuln), code=input.code, config=input.config))
                for vuln in high_confidence_vulns
            ]
        )

        # 4. Filter the triaged vulnerabilities by confidence
        logging.getLogger().info("Filtering the triaged vulnerabilities by confidence")
        high_confidence_triaged_vulns = filter_results_by_confidence(triaged_vulns, input.config.confidence)

        # 5. Report the vulnerabilities that still have a high confidence after triaging
        return high_confidence_triaged_vulns


def filter_results_by_confidence(results: List[sarif.Result], confidence_threshold: int) -> List[sarif.Result]:
    """Filter results by confidence."""
    return [result for result in results if result.properties.confidence > confidence_threshold]
