# SPDX-License-Identifier: MIT
# Copyright (c) 2025 Resourcely Inc.

"""
Risk Flagger Workflow

Analyzes source code for risks that the security team should investigate further.
"""

import logging
import os
import threading
from dataclasses import dataclass, field
from typing import Annotated, Dict, List, Literal, Optional

from fraim.actions import add_reviewer
from fraim.core.contextuals import CodeChunk
from fraim.core.parsers import PydanticOutputParser
from fraim.core.prompts.template import PromptTemplate
from fraim.core.steps.llm import LLMStep
from fraim.core.workflows import ChunkProcessingOptions, ChunkProcessor, Workflow
from fraim.outputs import sarif
from fraim.tools.filesystem import FilesystemTools
from fraim.util.pydantic import merge_models
from fraim.workflows.risk_flagger import risk_sarif_overlay
from fraim.workflows.risk_flagger.risk_list import build_risks_list, format_risks_for_prompt

from ...core.workflows.format_pr_comment import format_pr_comment
from ...core.workflows.llm_processing import LLMMixin, LLMOptions
from ...core.workflows.sarif import ConfidenceFilterOptions, filter_results_by_confidence

RISK_FLAGGER_PROMPTS = PromptTemplate.from_yaml(os.path.join(os.path.dirname(__file__), "prompts.yaml"))

# Default risks to consider, these can be overridden by the user
DEFAULT_RISKS = {
    # Infrastructure & Cloud Configuration
    "Database Changes": "All changes to a database should be flagged, similarly any networking changes that might affect the database should be flagged. Only flag if the database resource itself is being modified, not when adding unrelated resources to the same file.",
    "Public Facing VMs": "Changes that expose VMs to public internet access, via security groups or flags in the VM that would allow public access. Ignore changes that maintain existing public access without expanding it.",
    "Storage Bucket Public Access": "Changes that make storage buckets (S3, GCS, Azure Storage) publicly accessible or modify bucket policies to allow public read/write access. Ignore intentional public buckets for static websites if explicitly documented as such.",
    "IAM Permission Escalation": "Changes that grant excessive permissions, create new privileged roles, or modify existing IAM policies to allow broader access than previously configured. Ignore legitimate service-to-service permissions or principle of least privilege implementations.",
    "Network Security Groups": "Changes to security groups, network ACLs, or firewall rules that open ports to wider CIDR ranges (especially 0.0.0.0/0) or remove restrictive rules. Ignore opening specific ports for legitimate services when properly justified.",
    "Load Balancer Exposure": "Changes that expose internal services through load balancers or application gateways to public internet access. Ignore intentional public exposure of web applications that are designed to be public.",
    "VPC and Subnet Configuration": "Changes that modify VPC settings, subnet routing, or internet gateway configurations that could affect network isolation. Ignore routine maintenance changes that don't affect security posture.",
    "Container Security Context": "Changes to container configurations that run with privileged access, disable security features, or modify capabilities and security contexts. Ignore legitimate privileged containers when required for specific functionality like system monitoring.",
    # Application Security
    "Secrets in Code": "flag any hardcoded secrets, API keys, passwords, tokens, or credentials directly embedded in source code, configuration files, or environment variables. Only flag real credentials, if it is test credentials (ie 12345.. or abcd... or test... then you can ignore it)",
    "Authentication Bypass": "Changes that modify authentication logic, disable authentication checks, or implement custom authentication without proper validation. Ignore legitimate refactoring that maintains or improves authentication security.",
    "Authorization Changes": "Changes to access control logic, role-based permissions, or authorization middleware that could allow unauthorized access to resources. Ignore changes that make authorization more restrictive or implement proper role-based access control.",
    "Input Validation Removal": "Changes that remove or weaken input validation, sanitization, or parameter checking that could lead to injection vulnerabilities. Ignore moving validation to a different layer if it's still being performed.",
    "Cryptographic Implementation": "Changes involving custom cryptographic implementations, weak encryption algorithms, hardcoded encryption keys, or disabled SSL/TLS verification. Ignore usage of well-established cryptographic libraries or upgrading to stronger algorithms.",
    "Privileged Operations": "Changes that involve system calls, file system operations with elevated privileges, or execution of external commands with user input. Ignore legitimate system operations that are properly sanitized and authorized.",
    "CORS Configuration": "Changes to Cross-Origin Resource Sharing (CORS) policies that allow overly permissive origins, methods, or headers. Ignore specific, well-defined CORS policies for legitimate cross-origin communication.",
    "Session Management": "Changes to session handling, token generation, or cookie configuration that could weaken session security. Ignore improvements to session security or migration to more secure session management.",
    # Monitoring & Compliance
    "Logging Disablement": "Changes that disable, reduce, or redirect security logging, audit trails, or monitoring capabilities. Or any new resources that could enable security logging but do not. Ignore improvements to logging efficiency or legitimate log rotation configurations.",
    "Backup Security": "Changes to backup configurations, retention policies, or access controls that could affect data recovery or expose backup data. Ignore improvements to backup security or legitimate retention policy updates for compliance.",
    "Compliance Controls": "Changes that modify or remove compliance-related configurations, data retention policies, or regulatory control implementations. Ignore updates that enhance compliance or implement new regulatory requirements.",
    "Error Handling Changes": "Changes that modify error handling to expose sensitive information in error messages or disable proper error logging. Ignore improvements to error handling that provide better user experience without exposing sensitive data.",
    # Development & Deployment
    "Debug Mode Enablement": "Changes that enable debug modes, verbose logging, or development features in production environments. You must verify it is a production environment, if you cannot determine that the change is directly in a production environment then ignore the risk.",
    "Environment Configuration": "Changes to environment-specific configurations that could affect security posture between development, staging, and production. Ignore routine configuration updates that maintain or improve security across environments.",
}

risk_sarif = merge_models(sarif, risk_sarif_overlay)


@dataclass
class RiskFlaggerWorkflowOptions(ChunkProcessingOptions, LLMOptions, ConfidenceFilterOptions):
    """Input for the Risk Flagger workflow."""

    pr_url: Annotated[str, {"help": "URL of the pull request to analyze"}] = field(default="")
    approver: Annotated[str, {"help": "GitHub username or group to notify for approval"}] = field(default="")
    custom_risk_list_action: Annotated[
        Literal["append", "replace"], {"help": "Whether to append to or replace the default risks list"}
    ] = "append"
    custom_risk_list_filepath: Annotated[
        Optional[str], {"help": "Path to JSON/YAML file containing additional risks to consider"}
    ] = None
    custom_risk_list_json: Annotated[Optional[str], {"help": "JSON string containing additional risks to consider"}] = (
        None
    )
    custom_false_positive_considerations: Annotated[
        List[str], {"help": "List of additional considerations to help reduce false positives"}
    ] = field(default_factory=list)


@dataclass
class RiskFlaggerInput:
    """Input for the Risk Flagger step."""

    code: CodeChunk


class RiskFlaggerOutput(sarif.BaseSchema):
    """Output for the Risk Flagger step."""

    results: List[sarif.Result]


class RiskFlaggerWorkflow(Workflow[RiskFlaggerWorkflowOptions, List[sarif.Result]], ChunkProcessor, LLMMixin):
    """Analyzes source code for risks that the security team should investigate further."""

    name = "risk_flagger"

    def __init__(self, logger: logging.Logger, args: RiskFlaggerWorkflowOptions) -> None:
        super().__init__(logger, args)

        self.project = self.setup_project_input(self.logger, args)

        # Initialize the flagger step
        risks_dict = build_risks_list(
            default_risks=DEFAULT_RISKS,
            custom_risk_list_action=self.args.custom_risk_list_action,
            custom_risk_list_filepath=self.args.custom_risk_list_filepath,
            custom_risk_list_json=self.args.custom_risk_list_json,
        )
        self.logger.info(f"Using {len(risks_dict)} risks to consider: {', '.join(risks_dict.keys())}")

        risks_to_consider = format_risks_for_prompt(risks_dict)
        flagger_parser = PydanticOutputParser(risk_sarif.RunResults)
        flagger_llm = self.llm.with_tools(FilesystemTools(self.project.project_path))
        self.flagger_step: LLMStep[RiskFlaggerInput, RiskFlaggerOutput] = LLMStep(
            flagger_llm,
            RISK_FLAGGER_PROMPTS["system"],
            RISK_FLAGGER_PROMPTS["user"],
            flagger_parser,
            static_inputs={
                "risks_to_consider": risks_to_consider,
                "custom_false_positive_considerations": args.custom_false_positive_considerations,
            },
        )

    async def _process_single_chunk(self, chunk: CodeChunk) -> List[sarif.Result]:
        """Process a single chunk with multi-step processing and error handling."""
        try:
            # 1. Scan the code for potential risks.
            self.logger.debug("Scanning the code for potential risks")
            risks = await self.flagger_step.run(RiskFlaggerInput(code=chunk))

            # 2. Filter risks by confidence.
            self.logger.debug(f"Filtering {len(risks.results)} risks by confidence")
            self.logger.debug(f"risks: {risks.results}")
            high_confidence_risks: List[sarif.Result] = filter_results_by_confidence(
                risks.results, self.args.confidence
            )
            self.logger.debug(f"Found {len(high_confidence_risks)} high-confidence risks")

            return high_confidence_risks

        except Exception as e:
            self.logger.error(
                f"Failed to process chunk {chunk.file_path}:{chunk.line_number_start_inclusive}-{chunk.line_number_end_inclusive}: {str(e)}. "
                "Skipping this chunk and continuing with scan."
            )
            return []

    async def run(self) -> List[sarif.Result]:
        """Main Risk Flagger workflow.

        Args:
            input: RiskFlaggerWorkflowInput containing pr_url, approver and other workflow parameters

        Returns:
            List of Risk objects identified in the code

        Raises:
            ValueError: If diff is not set to true
            RuntimeError: If GitHub notification fails
            Exception: If any other error occurs during workflow execution
        """
        # 1. Validate required fields
        if not self.args.diff:
            raise ValueError(
                "This workflow is intended to only run on a diff, therefore it is required and cannot be empty"
            )

        # 2. Create a closure that captures max_concurrent_chunks
        async def chunk_processor(chunk: CodeChunk) -> List[sarif.Result]:
            return await self._process_single_chunk(chunk)

        # 3. Process chunks concurrently using utility
        results = await self.process_chunks_concurrently(
            project=self.project, chunk_processor=chunk_processor, max_concurrent_chunks=self.args.max_concurrent_chunks
        )

        # 4. Format results into PR comment
        pr_comment = format_pr_comment(results)

        # 5. Notify Github groups with formatted comment
        if len(results) > 0:
            if self.args.pr_url and self.args.approver:
                add_reviewer(self.args.pr_url, pr_comment, self.args.approver)
            else:
                self.logger.warning("PR URL and/or approver are missing, skipping GitHub notification")

        self.logger.info(pr_comment)

        return results
