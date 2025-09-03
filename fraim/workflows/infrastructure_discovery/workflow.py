# SPDX-License-Identifier: MIT
# Copyright (c) 2025 Resourcely Inc.

"""
Infrastructure Discovery Workflow

Analyzes infrastructure and deployment configurations to identify container configurations,
orchestration patterns, scaling policies, and deployment strategies.
"""

import logging
from dataclasses import dataclass
from typing import Annotated, Any

from fraim.config import Config
from fraim.core.contextuals import CodeChunk
from fraim.core.llms.litellm import LiteLLM
from fraim.core.workflows import ChunkProcessingOptions, ChunkProcessor, Workflow
from fraim.core.workflows.llm_processing import LLMProcessor, LLMProcessorOptions
from fraim.core.workflows.write_json_output import write_json_output

from .aggregation import InfrastructureResultAggregator
from .file_patterns import INFRASTRUCTURE_FILE_PATTERNS
from .processing import InfrastructureChunkProcessor
from .types import InfrastructureAnalysisResult, InfrastructureDiscoveryInput


class _ConfigAdapter(Config):
    """Adapter to make InfrastructureDiscoveryOptions compatible with Config interface."""

    def __init__(self, options: "InfrastructureDiscoveryOptions", logger: logging.Logger):
        # Initialize Config parent with required parameters
        super().__init__(
            logger=logger,
            model=options.model,
            temperature=options.temperature,
            output_dir=options.output,
            confidence=getattr(options, "confidence", 7),
            project_path=getattr(options, "project_path", ""),
        )
        self.options = options


# Need to create input options that extend ChunkProcessingOptions and LLMProcessorOptions
@dataclass
class InfrastructureDiscoveryOptions(ChunkProcessingOptions, LLMProcessorOptions):
    """Options for the Infrastructure Discovery workflow."""

    output: Annotated[str, {"help": "Path to save the output JSON report"}] = "fraim_output"
    focus_environments: Annotated[list[str] | None, {"help": "Specific environments to focus on"}] = None
    include_secrets: Annotated[bool, {"help": "Whether to include secret analysis"}] = True
    intelligent_test_detection: Annotated[bool, {"help": "Whether to use intelligent test detection"}] = True


class InfrastructureDiscoveryWorkflow(
    Workflow[InfrastructureDiscoveryOptions, dict[str, Any]], ChunkProcessor, LLMProcessor
):
    """
    Analyzes infrastructure and deployment configurations to extract:
    - Container configurations and orchestration patterns
    - Scaling policies and resource management
    - Deployment strategies and environments
    - Infrastructure components and their relationships
    - Runtime and operational characteristics
    """

    name = "infrastructure_discovery"

    def __init__(self, logger: logging.Logger, args: InfrastructureDiscoveryOptions) -> None:
        super().__init__(args)
        self.logger = logger
        # LLM is initialized by the LLMProcessor mixin

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
            config_adapter = _ConfigAdapter(self.args, self.logger)
            self.chunk_processor = InfrastructureChunkProcessor(config_adapter, self.llm, self._project_path)

        if self.result_aggregator is None:
            config_adapter = _ConfigAdapter(self.args, self.logger)
            self.result_aggregator = InfrastructureResultAggregator(config_adapter)

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

    async def run(self) -> dict[str, Any]:
        """Main Infrastructure Discovery workflow."""
        try:
            self.logger.info("Starting Infrastructure Discovery workflow")

            # 1. Setup project input using mixin utility
            project = self.setup_project_input(self.logger, self.args)

            # Store project for lazy tool initialization
            self.project = project
            # Capture project path while it's still valid
            self._project_path = project.project_path

            # Initialize processing and aggregation components
            self._initialize_processors()

            # 2. Create a closure that captures workflow parameters
            async def chunk_processor(chunk: CodeChunk) -> list[InfrastructureAnalysisResult]:
                return await self._process_single_chunk(
                    chunk, self.args.focus_environments, self.args.include_secrets, self.args.intelligent_test_detection
                )

            # 3. Process chunks concurrently using mixin utility
            chunk_results = await self.process_chunks_concurrently(
                project=project, chunk_processor=chunk_processor, max_concurrent_chunks=self.args.max_concurrent_chunks
            )

            # 4. Aggregate results
            # Create InfrastructureDiscoveryInput from options for compatibility
            discovery_input = InfrastructureDiscoveryInput(
                focus_environments=self.args.focus_environments,
                include_secrets=self.args.include_secrets,
                intelligent_test_detection=self.args.intelligent_test_detection,
            )
            final_result = await self._aggregate_results(chunk_results, discovery_input)

            self.logger.info(
                f"Infrastructure Discovery completed. Analyzed {final_result['files_analyzed']} files. "
                f"Confidence: {final_result['confidence_score']:.2f}"
            )

            # 5. Write output file if output_dir is configured
            config_adapter = _ConfigAdapter(self.args, self.logger)
            write_json_output(results=final_result, workflow_name="infrastructure_discovery", config=config_adapter)

            return final_result

        except Exception as e:
            self.logger.error(f"Error during infrastructure discovery: {str(e)}")
            raise e
