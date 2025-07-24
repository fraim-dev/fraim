# SPDX-License-Identifier: MIT
# Copyright (c) 2025 Resourcely Inc.

"""
System Analysis Workflow

Analyzes source code and documentation to extract system purpose, intended users, and business context.
This workflow addresses the Project Overview section of threat assessment questionnaires.
"""

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Annotated, Any, Dict, List, Optional

from pydantic import BaseModel

from fraim.config import Config
from fraim.core.contextuals import CodeChunk
from fraim.core.llms.litellm import LiteLLM
from fraim.core.parsers import PydanticOutputParser
from fraim.core.prompts.template import PromptTemplate
from fraim.core.steps.llm import LLMStep
from fraim.core.workflows import ChunkProcessingMixin, ChunkWorkflowInput, Workflow
from fraim.workflows.registry import workflow

# File patterns for system analysis - focusing on documentation and key configuration files
FILE_PATTERNS = [
    # Documentation files
    "README.md",
    "readme.md",
    "README.txt",
    "readme.txt",
    "README.rst",
    "readme.rst",
    "CHANGELOG.md",
    "changelog.md",
    "INSTALL.md",
    "install.md",
    "CONTRIBUTING.md",
    "contributing.md",
    "LICENSE",
    "license",
    "LICENSE.md",
    "license.md",
    "*.md",
    "*.rst",
    "*.txt",
    # API documentation
    "*.yaml",
    "*.yml",
    "*.json",
    "openapi.json",
    "swagger.json",
    "api.json",
    "*.openapi.yaml",
    "*.swagger.yaml",
    # Configuration files that reveal system purpose
    "package.json",
    "setup.py",
    "pyproject.toml",
    "Cargo.toml",
    "pom.xml",
    "build.gradle",
    "composer.json",
    "Gemfile",
    "requirements.txt",
    "Pipfile",
    # Docker and deployment files
    "Dockerfile",
    "docker-compose.yml",
    "docker-compose.yaml",
    # Web application entry points
    "index.html",
    "app.py",
    "main.py",
    "__init__.py",
    "server.py",
    "app.js",
    "main.js",
    "index.js",
    "server.js",
    "main.go",
    "main.java",
    "Application.java",
    "*.component.ts",
    "*.component.js",
    "routes.py",
    "urls.py",
    "routes.js",
]

# Load prompts from YAML files
DOCUMENT_ASSESSMENT_PROMPTS = PromptTemplate.from_yaml(
    os.path.join(os.path.dirname(__file__), "document_assessment_prompts.yaml")
)
ANALYSIS_AND_DEDUP_PROMPTS = PromptTemplate.from_yaml(
    os.path.join(os.path.dirname(__file__), "analysis_and_dedup_prompts.yaml")
)
FINAL_DEDUP_PROMPTS = PromptTemplate.from_yaml(os.path.join(os.path.dirname(__file__), "final_dedup_prompts.yaml"))


@dataclass
class SystemAnalysisInput(ChunkWorkflowInput):
    """Input for the System Analysis workflow."""

    business_context: Annotated[str, {"help": "Additional business context to consider during analysis"}] = ""

    focus_areas: Annotated[
        Optional[List[str]],
        {"help": "Specific areas to focus on (e.g., authentication, data_processing, api_endpoints)"},
    ] = None


class DocumentAssessmentResult(BaseModel):
    """Result from document type assessment and confidence scoring."""

    document_type: str  # "SYSTEM_INFORMATION" or "POLICY_PROCESS_DOCUMENTATION"
    confidence_score: float
    reasoning: str


class SystemAnalysisResult(BaseModel):
    """Structured result from system analysis."""

    system_purpose: str
    intended_users: List[str]
    business_context: str
    key_features: List[str]
    user_roles: List[str]
    external_integrations: List[str]
    data_types: List[str]


class FinalAnalysisResult(BaseModel):
    """Final aggregated and deduplicated system analysis result."""

    system_purpose: str
    intended_users: List[str]
    business_context: str
    key_features: List[str]
    user_roles: List[str]
    external_integrations: List[str]
    data_types: List[str]


@dataclass
class SystemAnalysisChunkInput:
    """Input for analyzing a single chunk."""

    code: CodeChunk
    config: Config
    business_context: str = ""
    focus_areas: Optional[List[str]] = None
    previous_findings: Optional[Dict[str, List[str]]] = None


@dataclass
class FinalDedupInput:
    """Input for final deduplication step."""

    # List of individual results with file_name added
    analysis_results: List[Dict[str, Any]]
    config: Config


@workflow("system_analysis")
class SystemAnalysisWorkflow(ChunkProcessingMixin, Workflow[SystemAnalysisInput, Dict[str, Any]]):
    """
    Analyzes codebase and documentation to extract system purpose, intended users, and business context.

    This workflow examines:
    - Documentation files (README, API specs, etc.)
    - Configuration files that reveal system purpose
    - Application entry points and routing logic
    - Authentication and user management code
    - Business logic to understand core functionality
    """

    def __init__(self, config: Config, *args: Any, **kwargs: Any) -> None:
        super().__init__(config, *args, **kwargs)

        # Initialize LLM and both analysis steps
        self.llm = LiteLLM.from_config(self.config)

        # Step 1: Document assessment and confidence scoring
        assessment_parser = PydanticOutputParser(DocumentAssessmentResult)
        self.assessment_step: LLMStep[SystemAnalysisChunkInput, DocumentAssessmentResult] = LLMStep(
            self.llm, DOCUMENT_ASSESSMENT_PROMPTS["system"], DOCUMENT_ASSESSMENT_PROMPTS["user"], assessment_parser
        )

        # Step 2: Analysis and deduplication
        analysis_parser = PydanticOutputParser(SystemAnalysisResult)
        self.analysis_step: LLMStep[SystemAnalysisChunkInput, SystemAnalysisResult] = LLMStep(
            self.llm, ANALYSIS_AND_DEDUP_PROMPTS["system"], ANALYSIS_AND_DEDUP_PROMPTS["user"], analysis_parser
        )

        # Step 3: Final aggregation and deduplication
        final_parser = PydanticOutputParser(FinalAnalysisResult)
        self.final_dedup_step: LLMStep[FinalDedupInput, FinalAnalysisResult] = LLMStep(
            self.llm, FINAL_DEDUP_PROMPTS["system"], FINAL_DEDUP_PROMPTS["user"], final_parser
        )

    @property
    def file_patterns(self) -> List[str]:
        """File patterns for system analysis."""
        return FILE_PATTERNS

    async def _process_single_chunk(
        self, chunk: CodeChunk, business_context: str = "", focus_areas: Optional[List[str]] = None
    ) -> List[SystemAnalysisResult]:
        """Process a single chunk using two-step analysis: assessment then analysis."""
        try:
            self.config.logger.debug(f"Processing chunk: {Path(chunk.file_path)}")

            chunk_input = SystemAnalysisChunkInput(
                code=chunk,
                config=self.config,
                business_context=business_context,
                focus_areas=focus_areas,
                previous_findings={},  # Empty for now since each chunk is analyzed independently
            )

            # Step 1: Document assessment and confidence scoring
            assessment = await self.assessment_step.run(chunk_input)

            self.config.logger.debug(
                f"Assessment for {chunk.file_path}: confidence={assessment.confidence_score:.2f}, "
                f"type='{assessment.document_type}', reasoning='{assessment.reasoning[:100]}...'"
            )

            # Only proceed to analysis if confidence is high enough and document type is relevant
            # Lowered threshold to 0.5 and made document type matching case-insensitive
            if assessment.confidence_score < 0.5 or "SYSTEM" not in assessment.document_type.upper():
                self.config.logger.debug(
                    f"Skipping chunk {chunk.file_path} - confidence: {assessment.confidence_score:.2f}, "
                    f"type: '{assessment.document_type}'"
                )
                return []

            # Step 2: System analysis and deduplication
            self.config.logger.debug(f"Analyzing chunk: {Path(chunk.file_path)}")
            result = await self.analysis_step.run(chunk_input)
            return [result]

        except Exception as e:
            self.config.logger.error(
                f"Failed to process chunk {chunk.file_path}:{chunk.line_number_start_inclusive}-{chunk.line_number_end_inclusive}: {str(e)}"
            )
            return []

    async def _aggregate_results(self, chunk_results: List[SystemAnalysisResult]) -> Dict[str, Any]:
        """Aggregate results from multiple chunks using LLM-based deduplication."""

        if not chunk_results:
            self.config.logger.warning(
                "No chunks passed document assessment filtering. "
                "This might indicate that the confidence threshold is too high or "
                "document types are not being classified as expected."
            )
            return {
                "system_purpose": "Unable to determine system purpose from available files",
                "intended_users": [],
                "business_context": "",
                "key_features": [],
                "user_roles": [],
                "external_integrations": [],
                "data_types": [],
                "confidence_score": 0.0,
                "analysis_summary": "No analyzable files found - check assessment filtering",
                "files_analyzed": 0,
                "total_chunks_processed": 0,
            }

        try:
            # Prepare data for final deduplication step
            analysis_results_for_llm = []
            for i, result in enumerate(chunk_results):
                analysis_results_for_llm.append(
                    {
                        # We don't have individual file names, so use generic names
                        "file_name": f"File {i + 1}",
                        "system_purpose": result.system_purpose,
                        "intended_users": result.intended_users,
                        "business_context": result.business_context,
                        "key_features": result.key_features,
                        "user_roles": result.user_roles,
                        "external_integrations": result.external_integrations,
                        "data_types": result.data_types,
                    }
                )

            # Run final LLM-based deduplication
            final_input = FinalDedupInput(analysis_results=analysis_results_for_llm, config=self.config)

            final_result = await self.final_dedup_step.run(final_input)

            # Set confidence based on number of files analyzed (more files = higher confidence)
            confidence_score = min(0.9, 0.6 + (len(chunk_results) * 0.1))

            # Create comprehensive summary
            analysis_summary = self._create_analysis_summary(
                final_result.system_purpose,
                final_result.intended_users,
                final_result.key_features,
                final_result.user_roles,
                len(chunk_results),
            )

            return {
                "system_purpose": final_result.system_purpose,
                "intended_users": final_result.intended_users,
                "business_context": final_result.business_context,
                "key_features": final_result.key_features,
                "user_roles": final_result.user_roles,
                "external_integrations": final_result.external_integrations,
                "data_types": final_result.data_types,
                "confidence_score": confidence_score,
                "analysis_summary": analysis_summary,
                "files_analyzed": len(chunk_results),
                "total_chunks_processed": len(chunk_results),
            }

        except Exception as e:
            self.config.logger.error(f"Failed to run final deduplication: {str(e)}")
            # Fallback to simple aggregation if LLM step fails
            return self._simple_fallback_aggregation(chunk_results)

    def _simple_fallback_aggregation(self, chunk_results: List[SystemAnalysisResult]) -> Dict[str, Any]:
        """Simple fallback aggregation when LLM deduplication fails."""
        all_purposes = [r.system_purpose for r in chunk_results if r.system_purpose.strip()]
        all_users = []
        all_features = []
        all_roles = []
        all_integrations = []
        all_data_types = []
        all_contexts = []

        for result in chunk_results:
            all_users.extend(result.intended_users)
            all_features.extend(result.key_features)
            all_roles.extend(result.user_roles)
            all_integrations.extend(result.external_integrations)
            all_data_types.extend(result.data_types)
            if result.business_context.strip():
                all_contexts.append(result.business_context)

        # Simple deduplication (just remove exact duplicates)
        unique_users = list(dict.fromkeys(all_users))[:7]
        unique_features = list(dict.fromkeys(all_features))[:10]
        unique_roles = list(dict.fromkeys(all_roles))[:6]
        unique_integrations = list(dict.fromkeys(all_integrations))[:8]
        unique_data_types = list(dict.fromkeys(all_data_types))[:10]

        system_purpose = max(all_purposes, key=len) if all_purposes else "System purpose unclear"
        business_context = " ".join(all_contexts)[:500]  # Simple truncation

        return {
            "system_purpose": system_purpose,
            "intended_users": unique_users,
            "business_context": business_context,
            "key_features": unique_features,
            "user_roles": unique_roles,
            "external_integrations": unique_integrations,
            "data_types": unique_data_types,
            "confidence_score": 0.5,  # Lower confidence for fallback
            "analysis_summary": f"Fallback analysis of {len(chunk_results)} files",
            "files_analyzed": len(chunk_results),
            "total_chunks_processed": len(chunk_results),
        }

    def _create_analysis_summary(
        self, purpose: str, users: List[str], features: List[str], roles: List[str], files_analyzed: int
    ) -> str:
        """Create a human-readable summary of the analysis."""

        summary_parts = [
            f"Analyzed {files_analyzed} files to understand system characteristics.",
            f"System Purpose: {purpose}",
        ]

        if users:
            summary_parts.append(f"Intended Users: {', '.join(users[:5])}")
            if len(users) > 5:
                summary_parts[-1] += f" and {len(users) - 5} others"

        if features:
            summary_parts.append(f"Key Features: {', '.join(features[:3])}")
            if len(features) > 3:
                summary_parts[-1] += f" and {len(features) - 3} others"

        if roles:
            summary_parts.append(f"User Roles: {', '.join(roles[:3])}")
            if len(roles) > 3:
                summary_parts[-1] += f" and {len(roles) - 3} others"

        return " ".join(summary_parts)

    async def workflow(self, input: SystemAnalysisInput) -> Dict[str, Any]:
        """Main System Analysis workflow."""
        try:
            self.config.logger.info("Starting System Analysis workflow")

            # 1. Setup project input using mixin utility
            project = self.setup_project_input(input)

            # 2. Create a closure that captures business_context and focus_areas
            async def chunk_processor(chunk: CodeChunk) -> List[SystemAnalysisResult]:
                return await self._process_single_chunk(chunk, input.business_context, input.focus_areas)

            # 3. Process chunks concurrently using mixin utility
            chunk_results = await self.process_chunks_concurrently(
                project=project, chunk_processor=chunk_processor, max_concurrent_chunks=input.max_concurrent_chunks
            )

            # 4. Aggregate results
            final_result = await self._aggregate_results(chunk_results)

            self.config.logger.info(
                f"System Analysis completed. Analyzed {final_result['files_analyzed']} files. "
                f"Confidence: {final_result['confidence_score']:.2f}"
            )

            # 5. Write output file if output_dir is configured
            output_dir = getattr(self.config, "output_dir", None)
            if output_dir:
                import datetime
                import os

                os.makedirs(output_dir, exist_ok=True)
                app_name = getattr(self.config, "project_path", "application")
                app_name = os.path.basename(app_name.rstrip(os.sep)) or "application"
                timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                output_filename = f"system_analysis_{app_name}_{timestamp}.json"
                output_path = os.path.join(output_dir, output_filename)
                try:
                    import json

                    with open(output_path, "w", encoding="utf-8") as f:
                        json.dump(final_result, f, indent=2)
                    self.config.logger.info(f"System analysis results written to {output_path}")
                except Exception as write_exc:
                    self.config.logger.error(f"Failed to write system analysis results: {write_exc}")

            return final_result

        except Exception as e:
            self.config.logger.error(f"Error during system analysis: {str(e)}")
            raise e
