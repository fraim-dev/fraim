# SPDX-License-Identifier: MIT
# Copyright (c) 2025 Resourcely Inc.

"""
Infrastructure Discovery Result Aggregation

Handles aggregation and summarization of infrastructure analysis results
from multiple chunks into final workflow output.
"""

from typing import Any

from fraim.config import Config

from .consolidation import InfrastructureConsolidator
from .types import InfrastructureAnalysisResult, InfrastructureDiscoveryInput
from .utils import create_infrastructure_summary


class InfrastructureResultAggregator:
    """Handles aggregation of infrastructure results from multiple chunks."""

    def __init__(self, config: Config) -> None:
        self.config = config
        self.consolidator = InfrastructureConsolidator(config)

    async def aggregate_results(
        self, chunk_results: list[InfrastructureAnalysisResult], input: InfrastructureDiscoveryInput
    ) -> dict[str, Any]:
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

        # Use rule-based consolidation for fast, reliable results
        self.config.logger.info(f"Starting consolidation for {len(chunk_results)} chunks")
        consolidated_results = self.consolidator.consolidate(chunk_results)

        unique_containers = consolidated_results.container_configs
        unique_components = consolidated_results.infrastructure_components
        unique_environments = consolidated_results.deployment_environments

        # Apply discovery method filtering if specified
        if input.discovery_method_filter:
            unique_components = [
                comp
                for comp in unique_components
                if hasattr(comp, "discovery_method") and comp.discovery_method == input.discovery_method_filter
            ]
            self.config.logger.debug(
                f"Filtered infrastructure components by discovery_method='{input.discovery_method_filter}': "
                f"{len(consolidated_results.infrastructure_components)} -> {len(unique_components)}"
            )

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
