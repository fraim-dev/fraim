# SPDX-License-Identifier: MIT
# Copyright (c) 2025 Resourcely Inc.

"""
Risk Flagger Workflow

Analyzes source code for risks that the security team should investigate further.
"""

import asyncio
import os
from dataclasses import dataclass, field
from typing import Annotated, Any, List, Literal, Optional

from fraim.actions import notify_github_group
from fraim.config import Config
from fraim.core.contextuals import CodeChunk
from fraim.core.llms.litellm import LiteLLM
from fraim.core.parsers import PydanticOutputParser
from fraim.core.prompts.template import PromptTemplate
from fraim.core.steps.llm import LLMStep
from fraim.core.workflows import ChunkProcessingMixin, ChunkWorkflowInput, Workflow
from fraim.outputs import risk
from fraim.outputs.risk import BaseSchema, Risk
from fraim.workflows.registry import workflow
from fraim.workflows.utils import filter_risks_by_confidence, format_pr_description

RISK_FLAGGER_PROMPTS = PromptTemplate.from_yaml(os.path.join(os.path.dirname(__file__), "risk_flagger_prompts.yaml"))

# Default risks to consider
DEFAULT_RISKS = [
    "Database Changes",
    "Public Facing VMs",
]


@dataclass
class RiskFlaggerWorkflowInput(ChunkWorkflowInput):
    """Input for the Risk Flagger workflow."""

    pr_url: Annotated[str, {"help": "URL of the pull request to analyze"}] = field(default="")
    approver: Annotated[str, {"help": "GitHub username or group to notify for approval"}] = field(default="")
    override_action: Annotated[
        Literal["append", "replace"], {"help": "Whether to append to or replace the default risks list"}
    ] = "append"
    override_filepath: Annotated[Optional[str], {"help": "Path to file containing additional risks to consider"}] = None
    override_text: Annotated[
        Optional[str], {"help": "Raw text containing additional risks to consider (newline or pipe (|) separated)"}
    ] = None


@dataclass
class RiskFlaggerInput:
    """Input for the Risk Flagger step."""

    code: CodeChunk
    config: Config


class RiskFlaggerOutput(BaseSchema):
    """Output for the Risk Flagger step."""

    results: List[risk.Risk]


@workflow("risk_flagger")
class RiskFlaggerWorkflow(ChunkProcessingMixin, Workflow[RiskFlaggerWorkflowInput, List[risk.Risk]]):
    """Analyzes source code for risks that the security team should investigate further."""

    @property
    def file_patterns(self) -> List[str]:
        """File patterns for risk flagging analysis."""
        return [
            "*.py",
            "*.js",
            "*.ts",
            "*.jsx",
            "*.tsx",
            "*.java",
            "*.cs",
            "*.cpp",
            "*.c",
            "*.h",
            "*.go",
            "*.rs",
            "*.php",
            "*.rb",
            "*.swift",
            "*.kt",
            "*.scala",
            "*.sh",
            "*.sql",
            "*.yml",
            "*.yaml",
            "*.json",
            "*.xml",
            "*.tf",
            "*.hcl",
            "*.dockerfile",
            "Dockerfile*",
        ]

    def __init__(self, config: Config, *args: Any, **kwargs: Any) -> None:
        super().__init__(config, *args, **kwargs)
        self.llm = LiteLLM.from_config(self.config)
        # Note: flagger_step will be initialized in workflow() method with configurable risks
        self.flagger_step: Optional[LLMStep[Any, Any]] = None

    def _load_risks_from_file(self, filepath: str) -> List[str]:
        """Load risks from a file, expecting one risk per line."""
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read().strip()
                # Split by newlines and filter out empty lines
                risks = [line.strip() for line in content.split("\n") if line.strip()]
                return risks
        except FileNotFoundError:
            self.config.logger.error(f"Risk file not found: {filepath}")
            raise
        except Exception as e:
            self.config.logger.error(f"Error reading risk file {filepath}: {e}")
            raise

    def _parse_risks_from_text(self, text: str) -> List[str]:
        """Parse risks from raw text, supporting both newline and comma separation."""
        text = text.strip()
        if not text:
            return []

        # Try pipe separation first, then newline separation
        if "|" in text:
            risks = [risk.strip() for risk in text.split(",") if risk.strip()]
        else:
            risks = [risk.strip() for risk in text.split("\n") if risk.strip()]

        return risks

    def _build_risks_list(self, input: RiskFlaggerWorkflowInput) -> List[str]:
        """Build the final list of risks to consider based on input configuration."""
        # Start with default risks
        risks = DEFAULT_RISKS.copy()

        # Get additional risks from file or text
        additional_risks = []
        if input.override_filepath:
            additional_risks.extend(self._load_risks_from_file(input.override_filepath))

        if input.override_text:
            additional_risks.extend(self._parse_risks_from_text(input.override_text))

        # Apply the override action
        if input.override_action == "replace" and additional_risks:
            risks = additional_risks
        elif input.override_action == "append":
            risks.extend(additional_risks)

        # Remove duplicates while preserving order
        seen = set()
        unique_risks = []
        for risk in risks:
            if risk.lower() not in seen:
                seen.add(risk.lower())
                unique_risks.append(risk)

        return unique_risks

    def _format_risks_for_prompt(self, risks: List[str]) -> str:
        """Format risks list for inclusion in the prompt."""
        return "\n".join(f"- {risk}" for risk in risks)

    def _initialize_flagger_step(self, risks_to_consider: str) -> None:
        """Initialize the flagger step with the configured risks."""
        flagger_parser = PydanticOutputParser(RiskFlaggerOutput)
        self.flagger_step = LLMStep(
            self.llm,
            RISK_FLAGGER_PROMPTS["system"],
            RISK_FLAGGER_PROMPTS["user"],
            flagger_parser,
            custom_system_tags={
                "risks_to_consider": risks_to_consider,
            },
        )

    async def _process_single_chunk(self, chunk: CodeChunk) -> List[risk.Risk]:
        """Process a single chunk with multi-step processing and error handling."""
        try:
            if self.flagger_step is None:
                raise ValueError("Flagger step not initialized")

            # 1. Scan the code for potential risks.
            self.config.logger.debug("Scanning the code for potential risks")
            risks = await self.flagger_step.run(RiskFlaggerInput(code=chunk, config=self.config))

            # 2. Filter risks by confidence.
            self.config.logger.debug(f"Filtering {len(risks.results)} risks by confidence")
            self.config.logger.debug(f"risks: {risks.results}")
            high_confidence_risks = filter_risks_by_confidence(risks.results, self.config.confidence)
            self.config.logger.debug(f"Found {len(high_confidence_risks)} high-confidence risks")

            return high_confidence_risks

        except Exception as e:
            self.config.logger.error(
                f"Failed to process chunk {chunk.file_path}:{chunk.line_number_start_inclusive}-{chunk.line_number_end_inclusive}: {str(e)}. "
                "Skipping this chunk and continuing with scan."
            )
            return []

    async def workflow(self, input: RiskFlaggerWorkflowInput) -> List[risk.Risk]:
        """Main Risk Flagger workflow.

        Args:
            input: RiskFlaggerWorkflowInput containing pr_url, approver and other workflow parameters

        Returns:
            List of Risk objects identified in the code

        Raises:
            ValueError: If required fields pr_url or approver are missing or empty
            RuntimeError: If GitHub notification fails
            Exception: If any other error occurs during workflow execution
        """
        # 1. Validate required fields
        if not input.diff:
            raise ValueError(
                "This workflow is intended to only run on a diff, therefore it is required and cannot be empty"
            )
        if not input.pr_url or input.pr_url.strip() == "":
            raise ValueError("pr_url is required and cannot be empty")
        if not input.approver or input.approver.strip() == "":
            raise ValueError("approver is required and cannot be empty")

        # 2. Build the configurable risks list and initialize flagger step
        risks_list = self._build_risks_list(input)
        risks_formatted = self._format_risks_for_prompt(risks_list)
        self._initialize_flagger_step(risks_formatted)

        self.config.logger.info(f"Using {len(risks_list)} risks to consider: {', '.join(risks_list)}")

        # 3. Setup project input using utility
        self.project = self.setup_project_input(input)

        # 4. Create a closure that captures max_concurrent_triagers
        async def chunk_processor(chunk: CodeChunk) -> List[risk.Risk]:
            return await self._process_single_chunk(chunk)

        # 5. Process chunks concurrently using utility
        results = await self.process_chunks_concurrently(
            project=self.project, chunk_processor=chunk_processor, max_concurrent_chunks=input.max_concurrent_chunks
        )

        # 6. Format results into PR description
        pr_description = format_pr_description(results)

        # 7. Notify Github groups with formatted description
        if len(results) > 0:
            notify_github_group(input.pr_url, pr_description, input.approver)

        self.config.logger.debug("--------------------------------")
        self.config.logger.debug(pr_description)
        self.config.logger.debug("--------------------------------")

        return results
