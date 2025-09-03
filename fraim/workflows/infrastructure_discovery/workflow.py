# SPDX-License-Identifier: MIT
# Copyright (c) 2025 Resourcely Inc.

"""
Infrastructure Discovery Workflow

Analyzes infrastructure and deployment configurations to identify container configurations,
orchestration patterns, scaling policies, and deployment strategies.
"""

from typing import Any

from fraim.config import Config
from fraim.core.contextuals import CodeChunk
from fraim.core.llms.litellm import LiteLLM
from fraim.core.workflows import ChunkProcessingMixin, Workflow
from fraim.workflows.registry import workflow
from fraim.workflows.utils import write_json_output

from .aggregation import InfrastructureResultAggregator
from .file_patterns import INFRASTRUCTURE_FILE_PATTERNS
from .processing import InfrastructureChunkProcessor
from .types import InfrastructureAnalysisResult, InfrastructureDiscoveryInput


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

        # Initialize LLM for processing components
        self.llm = LiteLLM.from_config(self.config)

        # Store project path when available
        self._project_path: str | None = None

        # Initialize processing and aggregation components
        self.chunk_processor: InfrastructureChunkProcessor | None = None
        self.result_aggregator: InfrastructureResultAggregator | None = None

    @property
    def file_patterns(self) -> list[str]:
        """File patterns for infrastructure discovery."""
        return INFRASTRUCTURE_FILE_PATTERNS

    def _initialize_processors(self) -> None:
        """Initialize processing and aggregation components."""
        if self.chunk_processor is None:
            self.chunk_processor = InfrastructureChunkProcessor(self.config, self.llm, self._project_path)

        if self.result_aggregator is None:
            self.result_aggregator = InfrastructureResultAggregator(self.config)

    async def _process_single_chunk(
        self,
        chunk: CodeChunk,
        focus_environments: list[str] | None = None,
        include_secrets: bool = True,
        intelligent_test_detection: bool = True,
    ) -> list[InfrastructureAnalysisResult]:
        """Process a single chunk for infrastructure analysis."""
        # Delegate to the chunk processor
        assert self.chunk_processor is not None  # Should be initialized
        return await self.chunk_processor.process_single_chunk(
            chunk, focus_environments, include_secrets, intelligent_test_detection
        )

    async def _aggregate_results(
        self, chunk_results: list[InfrastructureAnalysisResult], input: InfrastructureDiscoveryInput
    ) -> dict[str, Any]:
        """Aggregate infrastructure results from multiple chunks."""
        # Delegate to the result aggregator
        assert self.result_aggregator is not None  # Should be initialized
        return await self.result_aggregator.aggregate_results(chunk_results, input)

    async def workflow(self, input: InfrastructureDiscoveryInput) -> dict[str, Any]:
        """Main Infrastructure Discovery workflow."""
        try:
            self.config.logger.info("Starting Infrastructure Discovery workflow")

            # 1. Setup project input using mixin utility
            project = self.setup_project_input(input)

            # Use project as context manager to keep temp directories alive
            with project:
                # Store project for lazy tool initialization
                self.project = project
                # Capture project path while it's still valid
                self._project_path = project.project_path

                # Initialize processing and aggregation components
                self._initialize_processors()

                # 2. Create a closure that captures workflow parameters
                async def chunk_processor(chunk: CodeChunk) -> list[InfrastructureAnalysisResult]:
                    return await self._process_single_chunk(
                        chunk, input.focus_environments, input.include_secrets, input.intelligent_test_detection
                    )

                # 3. Process chunks concurrently using mixin utility
                chunk_results = await self.process_chunks_concurrently(
                    project=project, chunk_processor=chunk_processor, max_concurrent_chunks=input.max_concurrent_chunks
                )

                # 4. Aggregate results
                final_result = await self._aggregate_results(chunk_results, input)

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
