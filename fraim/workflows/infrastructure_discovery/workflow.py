# SPDX-License-Identifier: MIT
# Copyright (c) 2025 Resourcely Inc.

"""
Infrastructure Discovery Workflow

Analyzes infrastructure and deployment configurations to identify container configurations,
orchestration patterns, scaling policies, and deployment strategies.
"""

import os
from pathlib import Path
from typing import Any, Optional

from fraim.config import Config
from fraim.core.contextuals import CodeChunk
from fraim.core.llms.litellm import LiteLLM
from fraim.core.steps.llm import LLMStep
from fraim.core.workflows import ChunkProcessingMixin, Workflow
from fraim.workflows.registry import workflow
from fraim.workflows.utils import write_json_output
from fraim.workflows.utils.filter_results_by_confidences import filter_by_confidence_float, convert_int_confidence_to_float

from .file_patterns import INFRASTRUCTURE_FILE_PATTERNS
from .steps import create_dedup_step, create_infrastructure_step
from .types import (
    AgentInput,
    DedupInput,
    InfrastructureAnalysisResult,
    InfrastructureDiscoveryInput,
)
from .utils import create_infrastructure_summary


@workflow("infrastructure_discovery")
class InfrastructureDiscoveryWorkflow(ChunkProcessingMixin, Workflow[InfrastructureDiscoveryInput, dict[str, Any]]):
    """
    Analyzes infrastructure and deployment configurations to extract:
    - Container configurations and orchestration patterns
    - Scaling policies and resource management
    - Deployment strategies and environments
    - Infrastructure components and their relationships
    - Runtime and operational characteristics
    """

    def __init__(self, config: Config, *args: Any, **kwargs: Any) -> None:
        super().__init__(config, *args, **kwargs)

        # Initialize LLM and infrastructure analysis step
        self.llm = LiteLLM.from_config(self.config)

        # Infrastructure analysis step
        self.infrastructure_step: LLMStep[AgentInput, InfrastructureAnalysisResult] = create_infrastructure_step(
            self.llm
        )

        # Keep deduplication step as lazy since it depends on project setup for tools
        self._dedup_step: Optional[LLMStep[DedupInput, InfrastructureAnalysisResult]] = None
        # Store project path early when it's still valid
        self._project_path: Optional[str] = None

    @property
    def file_patterns(self) -> list[str]:
        """File patterns for infrastructure discovery."""
        return INFRASTRUCTURE_FILE_PATTERNS

    @property
    def dedup_step(self) -> LLMStep[DedupInput, InfrastructureAnalysisResult]:
        """Lazily initialize the deduplication step with tools."""
        if self._dedup_step is None:
            self._dedup_step = create_dedup_step(self.llm, self.config, self._project_path)
        return self._dedup_step

    async def _process_single_chunk(
        self, chunk: CodeChunk, focus_environments: list[str] | None = None, include_secrets: bool = True, confidence_threshold: float | None = None
    ) -> list[InfrastructureAnalysisResult]:
        """Process a single chunk for infrastructure analysis."""
        try:
            self.config.logger.debug(f"Processing infrastructure chunk: {Path(chunk.file_path)}")

            chunk_input = AgentInput(
                code=chunk,
                config=self.config,
                focus_environments=focus_environments,
            )

            # Run infrastructure analysis
            result = await self.infrastructure_step.run(chunk_input)

            # Apply confidence filtering if threshold is provided
            if confidence_threshold is not None:
                self.config.logger.debug(
                    f"Filtering infrastructure findings by confidence threshold: {confidence_threshold}")

                # Filter each type of finding by confidence
                filtered_containers = filter_by_confidence_float(
                    result.container_configs, confidence_threshold)
                filtered_components = filter_by_confidence_float(
                    result.infrastructure_components, confidence_threshold)
                filtered_environments = filter_by_confidence_float(
                    result.deployment_environments, confidence_threshold)

                # Create new result with filtered findings
                filtered_result = InfrastructureAnalysisResult(
                    container_configs=filtered_containers,
                    infrastructure_components=filtered_components,
                    deployment_environments=filtered_environments
                )

                # Log filtering results
                original_count = len(result.container_configs) + len(
                    result.infrastructure_components) + len(result.deployment_environments)
                filtered_count = len(
                    filtered_containers) + len(filtered_components) + len(filtered_environments)
                self.config.logger.debug(
                    f"Confidence filtering: {original_count} -> {filtered_count} findings")

                return [filtered_result]

            return [result]

        except Exception as e:
            self.config.logger.error(
                f"Failed to process infrastructure chunk {chunk.file_path}:{chunk.line_number_start_inclusive}-{chunk.line_number_end_inclusive}: {str(e)}"
            )
            return []

    async def _aggregate_results(self, chunk_results: list[InfrastructureAnalysisResult]) -> dict[str, Any]:
        """Aggregate infrastructure results from multiple chunks."""

        if not chunk_results:
            self.config.logger.warning("No infrastructure chunks processed successfully")
            return {
                "container_configs": [],
                "infrastructure_components": [],
                "deployment_environments": [],
                "confidence_score": 0.0,
                "analysis_summary": "No infrastructure files found or processed",
                "files_analyzed": 0,
                "total_chunks_processed": 0,
            }

        # Use LLM for intelligent deduplication instead of simple name matching
        deduplicated_results = await self._llm_deduplicate_results(chunk_results)

        unique_containers = deduplicated_results.container_configs
        unique_components = deduplicated_results.infrastructure_components
        unique_environments = deduplicated_results.deployment_environments

        # Calculate confidence based on number of files and quality of findings
        confidence_score = min(0.9, 0.4 + (len(chunk_results) * 0.1) + (len(unique_containers) * 0.05))

        analysis_summary = create_infrastructure_summary(
            unique_containers, unique_components, unique_environments, len(chunk_results)
        )

        return {
            "container_configs": [config.model_dump() for config in unique_containers],
            "infrastructure_components": [component.model_dump() for component in unique_components],
            "deployment_environments": [env.model_dump() for env in unique_environments],
            "confidence_score": confidence_score,
            "analysis_summary": analysis_summary,
            "files_analyzed": len(chunk_results),
            "total_chunks_processed": len(chunk_results),
        }

    async def _llm_deduplicate_results(
        self, chunk_results: list[InfrastructureAnalysisResult]
    ) -> InfrastructureAnalysisResult:
        """Use LLM to intelligently deduplicate infrastructure findings."""

        # Prepare findings for LLM analysis
        findings_summary = []
        for i, result in enumerate(chunk_results):
            findings_summary.append(
                {
                    "chunk_id": f"chunk_{i + 1}",
                    "container_configs": [config.model_dump() for config in result.container_configs],
                    "infrastructure_components": [comp.model_dump() for comp in result.infrastructure_components],
                    "deployment_environments": [env.model_dump() for env in result.deployment_environments],
                }
            )

        self.config.logger.debug(f"Running LLM deduplication on {len(chunk_results)} chunks")

        dedup_input = DedupInput(findings_summary=findings_summary, config=self.config)

        deduplicated_result = await self.dedup_step.run(dedup_input)
        self.config.logger.debug(f"LLM deduplication completed successfully")
        return deduplicated_result

    async def workflow(self, input: InfrastructureDiscoveryInput) -> dict[str, Any]:
        """Main Infrastructure Discovery workflow."""
        try:
            self.config.logger.info("Starting Infrastructure Discovery workflow")

            # Determine confidence threshold
            confidence_threshold = input.confidence_threshold
            if confidence_threshold is None:
                # Convert integer confidence (1-10) to float (0.0-1.0)
                confidence_threshold = convert_int_confidence_to_float(
                    self.config.confidence)

            self.config.logger.info(
                f"Using confidence threshold: {confidence_threshold}")

            # 1. Setup project input using mixin utility
            project = self.setup_project_input(input)

            # Use project as context manager to keep temp directories alive
            with project:
                # Store project for lazy tool initialization
                self.project = project
                # Capture project path while it's still valid
                self._project_path = project.project_path

                # 2. Create a closure that captures workflow parameters
                async def chunk_processor(chunk: CodeChunk) -> list[InfrastructureAnalysisResult]:
                    return await self._process_single_chunk(
                        chunk,
                        input.focus_environments,
                        input.include_secrets,
                        confidence_threshold
                    )

                # 3. Process chunks concurrently using mixin utility
                chunk_results = await self.process_chunks_concurrently(
                    project=project, chunk_processor=chunk_processor, max_concurrent_chunks=input.max_concurrent_chunks
                )

                # 4. Aggregate results (now temp directory is still available for tools)
                final_result = await self._aggregate_results(chunk_results)

            self.config.logger.info(
                f"Infrastructure Discovery completed. Analyzed {final_result['files_analyzed']} files. "
                f"Confidence: {final_result['confidence_score']:.2f}"
            )

            # 5. Write output file if output_dir is configured
            write_json_output(results=final_result, workflow_name="infrastructure_discovery", config=self.config)

            return final_result

        except Exception as e:
            self.config.logger.error(f"Error during infrastructure discovery: {str(e)}")
            raise e
