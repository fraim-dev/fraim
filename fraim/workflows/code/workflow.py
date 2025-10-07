# SPDX-License-Identifier: MIT
# Copyright (c) 2025 Resourcely Inc.

"""
Code Security Analysis Workflow

Analyzes source code for security vulnerabilities using AI-powered scanning.
"""

import asyncio
import logging
import os
from dataclasses import dataclass, field
from typing import Annotated
from rich.console import Console
from rich.markdown import Markdown

from fraim.core.contextuals import CodeChunk
from fraim.core.history import EventRecord, History, HistoryRecord
from fraim.core.parsers import PydanticOutputParser
from fraim.core.prompts.template import PromptTemplate
from fraim.core.steps.llm import LLMStep
from fraim.core.workflows import ChunkProcessingOptions, ChunkProcessor, Workflow
from fraim.outputs import sarif
from fraim.tools import FilesystemTools
from fraim.util.pydantic import merge_models

from ...actions import add_comment, add_reviewer, send_message, add_code_annotation
from ...core.workflows.format_pr_comment import format_pr_comment
from ...core.workflows.format_slack_message import format_slack_message
from ...core.workflows.llm_processing import LLMMixin, LLMOptions
from ...core.workflows.sarif import ConfidenceFilterOptions, filter_results_by_confidence, write_sarif_and_html_report
from . import triage_sarif_overlay

logger = logging.getLogger(__name__)

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
class SASTWorkflowOptions(ChunkProcessingOptions, LLMOptions, ConfidenceFilterOptions):
    """Input for the Code workflow."""

    output: Annotated[str, {"help": "Path to save the output HTML report"}] = "fraim_output"
    pr_url: Annotated[str, {"help": "URL of the PR to add a comment to"}] = field(default="")
    approver: Annotated[str, {"help": "GitHub username of the approver to add to the PR"}] = field(default="")
    slack_webhook_url: Annotated[str, {"help": "URL of the Slack webhook to send a message to"}] = field(default="")
    no_gh_comment: Annotated[bool, {"help": "Whether to skip adding a comment to the PR"}] = False

    max_concurrent_triagers: Annotated[
        int, {"help": "Maximum number of triager requests per chunk to run concurrently"}
    ] = 3


@dataclass
class SASTInput:
    """Input for the SAST scanner step."""

    code: CodeChunk


@dataclass
class TriagerInput:
    """Input for the triage step."""

    vulnerability: str
    code: CodeChunk


class SASTWorkflow(ChunkProcessor[sarif.Result], LLMMixin, Workflow[SASTWorkflowOptions, list[sarif.Result]]):
    """
    Analyzes source code for security vulnerabilities
    """

    name = "code"

    def __init__(self, args: SASTWorkflowOptions) -> None:
        super().__init__(args)

        # Configure the project
        self.project = self.setup_project_input(self.args)

        # Configure the scanner step
        scanner_parser = PydanticOutputParser(sarif.RunResults)
        self.scanner_step: LLMStep[SASTInput, sarif.RunResults] = LLMStep(
            self.llm,
            SCANNER_PROMPTS["system"],
            SCANNER_PROMPTS["user"],
            scanner_parser,
        )

        # Configure the triager step with tools
        triager_tools = FilesystemTools(self.project.project_path)
        triager_llm = self.llm.with_tools(triager_tools)
        triager_parser = PydanticOutputParser(triage_sarif.Result)
        self.triager_step: LLMStep[TriagerInput, sarif.Result] = LLMStep(
            triager_llm,
            TRIAGER_PROMPTS["system"],
            TRIAGER_PROMPTS["user"],
            triager_parser,
        )

    @property
    def file_patterns(self) -> list[str]:
        """Code file patterns."""
        return FILE_PATTERNS

    async def _process_single_chunk(
        self, history: History, chunk: CodeChunk, max_concurrent_triagers: int
    ) -> list[sarif.Result]:
        """Process a single chunk with multi-step processing and error handling."""
        try:
            # 1. Scan the code for potential vulnerabilities.
            logger.debug("Scanning the code for potential vulnerabilities")
            potential_vulns = await self.scanner_step.run(history, SASTInput(code=chunk))

            # 2. Filter vulnerabilities by confidence.
            logger.debug("Filtering vulnerabilities by confidence")
            high_confidence_vulns = filter_results_by_confidence(potential_vulns.results, self.args.confidence)

            # 3. Triage the high-confidence vulns with limited concurrency.
            logger.debug("Triaging high-confidence vulns with limited concurrency")

            # Create semaphore to limit concurrent triager requests
            triager_semaphore = asyncio.Semaphore(max_concurrent_triagers)

            async def triage_with_semaphore(vuln: sarif.Result) -> sarif.Result | None:
                """Triage a vulnerability with semaphore to limit concurrency."""
                # Create a subhistory for this task
                task_record = HistoryRecord(description=f"Triaging potential vulnerability {vuln.message.text}")
                history.append_record(task_record)

                async with triager_semaphore:
                    return await self.triager_step.run(
                        task_record.history, TriagerInput(vulnerability=str(vuln), code=chunk)
                    )

            triaged_results = await asyncio.gather(*[triage_with_semaphore(vuln) for vuln in high_confidence_vulns])

            # Filter out None results from failed triaging attempts
            triaged_vulns = [result for result in triaged_results if result is not None]

            # 4. Filter the triaged vulnerabilities by confidence
            logger.debug("Filtering the triaged vulnerabilities by confidence")
            high_confidence_triaged_vulns = filter_results_by_confidence(triaged_vulns, self.args.confidence)

            self.history.append_record(
                EventRecord(description=f"Done. Found {len(high_confidence_triaged_vulns)} results.")
            )

            return high_confidence_triaged_vulns

        except Exception as e:
            logger.error(
                f"Failed to process chunk {chunk.file_path}:{chunk.line_number_start_inclusive}-{chunk.line_number_end_inclusive}: {e!s}. "
                "Skipping this chunk and continuing with scan."
            )

            return []

    async def run(self) -> list[sarif.Result]:
        """Main Code workflow - full control over execution with multi-step processing."""

        # Create a closure that captures max_concurrent_triagers
        async def chunk_processor(history: History, chunk: CodeChunk) -> list[sarif.Result]:
            return await self._process_single_chunk(history, chunk, self.args.max_concurrent_triagers)

        # Process chunks concurrently using utility
        results = await self.process_chunks_concurrently(
            history=self.history,
            project=self.project,
            chunk_processor=chunk_processor,
            max_concurrent_chunks=self.args.max_concurrent_chunks,
        )

        # Generate reports
        report_paths = write_sarif_and_html_report(
            results=results,
            repo_name=self.project.repo_name,
            output_dir=self.args.output,
        )
        
        if len(results) > 0:
            pr_comment = format_pr_comment(results)

            # 4. Print comment to console
            console = Console()
            console.print(Markdown(pr_comment))
        
            # Add comment to PR, if enabled
            if self.args.pr_url and not self.args.no_gh_comment:
                add_comment(self.history, self.args.pr_url, pr_comment, self.args.approver)
                add_code_annotation(self.history, self.args.pr_url, results, self.args.approver)
            else:
                logger.warning("PR URL missing or no_gh_comment is True, skipping Add Comment")

            # Add reviewer to PR, if enabled
            if self.args.pr_url and self.args.approver:
                try:
                    add_reviewer(self.history, self.args.pr_url, self.args.approver)
                except Exception as e:
                    logger.warning(
                        f"Failed to add reviewer, check to make sure you have the right permissions: {e}\nContinuing with comment only."
                    )
            else:
                logger.warning("PR URL and/or approver are missing, skipping Add Reviewer")

            # Send message to Slack, if enabled
            if self.args.slack_webhook_url:
                slack_message = format_slack_message(results, workflow_name=self.name, pr_url=self.args.pr_url)
                send_message(self.history, self.args.slack_webhook_url, slack_message)

        print(f"Found {len(results)} results.")
        print(f"Wrote SARIF report to {report_paths.sarif_path}")
        print(f"Wrote HTML report to {report_paths.html_path}")

        return results
