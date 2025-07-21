# SPDX-License-Identifier: MIT
# Copyright (c) 2025 Resourcely Inc.

"""
Remediate Wiz Findings Workflow

Analyzes Wiz security findings and generates actionable remediation steps.
"""
import json
import asyncio
import os
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Annotated, Any, List, Optional, cast

from fraim.config import Config
from fraim.core.llms.litellm import LiteLLM
from fraim.core.parsers import PydanticOutputParser
from fraim.core.prompts.template import PromptTemplate
from fraim.core.steps.llm import LLMStep
from fraim.core.workflows import Workflow
from fraim.inputs.wiz_findings import WizFindings, WizFinding
from fraim.outputs import sarif
from fraim.outputs.remediate import (
    Remediation, 
    RemediationReport, 
    RemediationAction,
    RemediationMetadata,
    RemediationSeverity,
    RemediationStatus,
    RemediationType,
    create_remediation_report
)
from fraim.workflows.utils.generate_remediation_html_report import generate_remediation_html_report
from fraim.workflows.registry import workflow


@dataclass
class RemediateInput:
    """Input for the remediate workflow."""
    config: Config
    api_token: Annotated[Optional[str], {"help": "Wiz API token for authentication (defaults to WIZ_API_TOKEN environment variable)"}] = None
    endpoint: Annotated[str, {"help": "Wiz GraphQL API endpoint"}] = "https://api.us17.app.wiz.io/graphql"
    
    # Pagination and filtering options
    first: Annotated[int, {"help": "Number of findings to fetch per page"}] = 100
    include_deleted: Annotated[bool, {"help": "Whether to include deleted findings"}] = False
    analyzed_after: Annotated[Optional[str], {"help": "ISO timestamp - only include findings analyzed after this date"}] = None
    
    # Additional filter options
    severity_filter: Annotated[Optional[List[str]], {"help": "Filter by severity levels"}] = field(default_factory=list)
    status_filter: Annotated[Optional[List[str]], {"help": "Filter by status"}] = field(default_factory=list)
    
    # Concurrency control
    max_concurrent_findings: Annotated[int, {"help": "Maximum number of findings to process concurrently"}] = 10


@dataclass
class RemediateStepInput:
    """Input for the remediation step."""
    finding: WizFinding
    config: Config


REMEDIATE_PROMPTS = PromptTemplate.from_yaml(os.path.join(os.path.dirname(__file__), "remediate_prompts.yaml"))


type RemediateOutput = List[sarif.Result]


@workflow("remediate")
class RemediateWorkflow(Workflow[RemediateInput, RemediateOutput]):
    """Analyzes Wiz security findings and generates actionable remediation steps"""

    def __init__(self, config: Config, *args: Any, **kwargs: Any) -> None:
        self.config = config

        # Lazy initialization
        self._llm: Optional[LiteLLM] = None
        self._remediate_step: Optional[LLMStep[RemediateStepInput, Remediation]] = None

    @property
    def llm(self) -> LiteLLM:
        """Lazily initialize the LLM instance."""
        if self._llm is None:
            self._llm = LiteLLM.from_config(self.config)
        return self._llm

    @property
    def remediate_step(self) -> LLMStep[RemediateStepInput, Remediation]:
        """Lazily initialize the remediation step."""
        if self._remediate_step is None:
            remediate_parser = PydanticOutputParser(Remediation)
            self._remediate_step = LLMStep(
                self.llm, 
                REMEDIATE_PROMPTS["system"], 
                REMEDIATE_PROMPTS["user"], 
                remediate_parser
            )
        return self._remediate_step

    def _map_wiz_severity_to_remediation_severity(self, wiz_severity: str) -> RemediationSeverity:
        """Map Wiz severity levels to remediation severity levels."""
        severity_mapping = {
            "CRITICAL": RemediationSeverity.CRITICAL,
            "HIGH": RemediationSeverity.HIGH,
            "MEDIUM": RemediationSeverity.MEDIUM,
            "LOW": RemediationSeverity.LOW,
            "INFORMATIONAL": RemediationSeverity.INFO,
            "INFO": RemediationSeverity.INFO,
        }
        return severity_mapping.get(wiz_severity.upper(), RemediationSeverity.MEDIUM)



    async def _process_finding(self, finding: WizFinding) -> Optional[Remediation]:
        """Process a single Wiz finding to generate a remediation."""
        try:
            # Generate remediation using LLM
            step_input = RemediateStepInput(finding=finding, config=self.config)
            remediation = await self.remediate_step.run(step_input)

            # Ensure metadata is properly set
            if not remediation.metadata.finding_id:
                remediation.metadata.finding_id = finding.id
            
            if not remediation.metadata.created_at:
                remediation.metadata.created_at = datetime.utcnow().isoformat() + "Z"
            
            if not remediation.metadata.created_by:
                remediation.metadata.created_by = "fraim-remediate-workflow"
            
            # Map severity from Wiz finding if not already set appropriately
            if finding.severity:
                remediation.metadata.risk_level = self._map_wiz_severity_to_remediation_severity(finding.severity)
            
            return remediation
            
        except Exception as e:
            # Log error and continue with next finding
            print(f"Error processing finding {finding.id}: {str(e)}")
            return None

    def _remediation_to_sarif_result(self, remediation: Remediation) -> sarif.Result:
        """Convert a Remediation to a SARIF Result."""
        # Map remediation severity to SARIF level with proper typing
        if remediation.metadata.risk_level in [RemediationSeverity.CRITICAL, RemediationSeverity.HIGH]:
            level: sarif.ResultLevelEnum = "error"
        elif remediation.metadata.risk_level in [RemediationSeverity.MEDIUM, RemediationSeverity.LOW]:
            level = "warning"  
        else:
            level = "note"
        
        # Extract action-specific details and location information
        location = sarif.Location(
            physicalLocation=sarif.PhysicalLocation(
                artifactLocation=sarif.ArtifactLocation(uri="remediation://generated"),
                region=sarif.Region(startLine=1, endLine=1)
            )
        )
        
        # Extract action details based on remediation type
        action_dict = remediation.action.model_dump()
        
        # Create properties with action-specific details
        properties_dict = {
            "type": f"Remediation-{remediation.action.type}",
            "confidence": int(remediation.metadata.confidence_score * 10),  # Convert 0-1 to 1-10
            "exploitable": False,  # Remediations are fixes, not vulnerabilities
            "explanation": sarif.Message(text=f"Remediation: {remediation.title}"),
        }
        
        # Add action-specific properties for the HTML generator
        if remediation.action.type == RemediationType.CODE:
            properties_dict.update({
                "file_path": action_dict.get("file_path"),
                "original_code": action_dict.get("original_code"),
                "remediated_code": action_dict.get("remediated_code"),
                "line_start": action_dict.get("line_start"),
                "line_end": action_dict.get("line_end"),
                "change_description": action_dict.get("description"),
            })
            # Update location with actual file path if available
            if action_dict.get("file_path"):
                location = sarif.Location(
                    physicalLocation=sarif.PhysicalLocation(
                        artifactLocation=sarif.ArtifactLocation(uri=action_dict["file_path"]),
                        region=sarif.Region(
                            startLine=action_dict.get("line_start", 1),
                            endLine=action_dict.get("line_end", 1)
                        )
                    )
                )
                
        elif remediation.action.type == RemediationType.CLI:
            properties_dict.update({
                "command": action_dict.get("command"),
                "working_directory": action_dict.get("working_directory"),
                "requires_sudo": action_dict.get("requires_sudo", False),
                "timeout_seconds": action_dict.get("timeout_seconds"),
                "expected_output": action_dict.get("expected_output"),
            })
            
        elif remediation.action.type == RemediationType.CONFIGURATION:
            properties_dict.update({
                "config_file": action_dict.get("config_file"),
                "config_path": action_dict.get("config_path"),
                "original_value": action_dict.get("original_value"),
                "remediated_value": action_dict.get("remediated_value"),
                "config_format": action_dict.get("config_format"),
                "change_description": action_dict.get("description"),
            })
            # Update location with actual config file path if available
            if action_dict.get("config_file"):
                location = sarif.Location(
                    physicalLocation=sarif.PhysicalLocation(
                        artifactLocation=sarif.ArtifactLocation(uri=action_dict["config_file"]),
                        region=sarif.Region(startLine=1, endLine=1)
                    )
                )
                
        elif remediation.action.type == RemediationType.MANUAL:
            properties_dict.update({
                "steps": action_dict.get("steps", []),
                "documentation_url": action_dict.get("documentation_url"),
                "estimated_time_minutes": action_dict.get("estimated_time_minutes"),
                "prerequisites": action_dict.get("prerequisites"),
            })
        
        # Create properties object with core SARIF fields only
        properties = sarif.ResultProperties(
            type=f"Remediation-{remediation.action.type}",
            confidence=int(remediation.metadata.confidence_score * 10),  # Convert 0-1 to 1-10
            exploitable=False,  # Remediations are fixes, not vulnerabilities
            explanation=sarif.Message(text=f"Remediation: {remediation.title}")
        )
        
        # Store action details in the result message as JSON for the HTML generator to parse
        import json
        action_details_json = json.dumps(action_dict)
        result_message = f"{remediation.title} | ACTION_DETAILS: {action_details_json}"
        
        return sarif.Result(
            message=sarif.Message(text=result_message),
            level=level,
            locations=[location],
            properties=properties
        )

    async def workflow(self, input: RemediateInput) -> RemediateOutput:
        """Main workflow implementation."""
        results: List[sarif.Result] = []
        
        # Resolve API token from environment if not provided
        api_token = input.api_token
        if api_token is None:
            api_token = os.getenv("WIZ_API_TOKEN")
            if api_token is None:
                raise ValueError("API token must be provided either as parameter or WIZ_API_TOKEN environment variable")
        
        # Create WizFindings object from input parameters
        wiz_findings = WizFindings(
            config=input.config,
            api_token=api_token,
            endpoint=input.endpoint,
            first=input.first,
            include_deleted=input.include_deleted,
            analyzed_after=input.analyzed_after,
            severity_filter=input.severity_filter,
            status_filter=input.status_filter
        )
        
        # Process findings with controlled concurrency
        findings_processed = 0
        findings_with_remediations = 0
        
        try:
            # Use the WizFindings iterator to fetch findings via API calls
            self.config.logger.info("Fetching Wiz findings...")
            
            # Create semaphore to limit concurrent finding processing
            max_concurrent_findings = input.max_concurrent_findings or 5
            semaphore = asyncio.Semaphore(max_concurrent_findings)
            
            async def process_finding_with_semaphore(finding: WizFinding) -> Optional[sarif.Result]:
                """Process a finding with semaphore to limit concurrency."""
                async with semaphore:
                    self.config.logger.info(f"Processing finding: {finding.id}")
                    remediation = await self._process_finding(finding)
                    if remediation:
                        # Convert remediation to SARIF Result
                        sarif_result = self._remediation_to_sarif_result(remediation)
                        self.config.logger.info(f"Generated remediation for finding {finding.id}")
                        return sarif_result
                    else:
                        self.config.logger.warning(f"Failed to generate remediation for finding {finding.id}")
                        return None
            
            # Process findings as they stream in from the WizFindings iterator
            active_tasks = set()
            
            # The iterator handles API calls and pagination automatically
            for finding in wiz_findings:
                findings_processed += 1
                
                # Create task for this finding and add to active tasks
                task = asyncio.create_task(process_finding_with_semaphore(finding))
                active_tasks.add(task)
                
                # If we've hit our concurrency limit, wait for some tasks to complete
                if len(active_tasks) >= max_concurrent_findings:
                    done, active_tasks = await asyncio.wait(active_tasks, return_when=asyncio.FIRST_COMPLETED)
                    for completed_task in done:
                        finding_result = await completed_task
                        if finding_result:
                            results.append(finding_result)
                            findings_with_remediations += 1
                
                # Optional: Add a small delay to avoid overwhelming the API
                if findings_processed == 20:
                    break # TODO: remove this
                    await asyncio.sleep(0.1)
                    
            # Wait for any remaining tasks to complete
            if active_tasks:
                for future in asyncio.as_completed(active_tasks):
                    finding_result = await future
                    if finding_result:
                        results.append(finding_result)
                        findings_with_remediations += 1
                    
        except Exception as e:
            self.config.logger.error(f"Error fetching Wiz findings: {str(e)}")
            raise
        
        self.config.logger.info(f"Processed {findings_processed} findings, generated {findings_with_remediations} remediations")
        
        # Generate HTML remediation report
        if results:
            try:
                output_dir = getattr(self.config, 'output_dir', 'fraim_output')
                if not os.path.exists(output_dir):
                    os.makedirs(output_dir, exist_ok=True)
                
                repo_name = getattr(self.config, 'repo_name', 'Wiz Findings')
                report_path = generate_remediation_html_report(
                    results=results,
                    repo_name=repo_name,
                    output_dir=output_dir,
                    logger=self.config.logger
                )
                self.config.logger.info(f"Generated remediation HTML report: {report_path}")
            except Exception as e:
                self.config.logger.error(f"Failed to generate HTML report: {str(e)}")
        
        print(f"results: {results}")
        return results 