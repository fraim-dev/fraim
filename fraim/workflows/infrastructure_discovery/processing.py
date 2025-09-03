# SPDX-License-Identifier: MIT
# Copyright (c) 2025 Resourcely Inc.

"""
Infrastructure Discovery Chunk Processing

Handles processing of individual code chunks for infrastructure analysis,
including test file detection and infrastructure component extraction.
"""

from pathlib import Path
from typing import Optional

from fraim.config import Config
from fraim.core.contextuals import CodeChunk
from fraim.core.llms.litellm import LiteLLM
from fraim.core.steps.llm import LLMStep

from .steps import create_infrastructure_step
from .test_detection import TestDetectionInput, TestFileDetectionResult, create_test_detection_step
from .types import AgentInput, InfrastructureAnalysisResult


class InfrastructureChunkProcessor:
    """Handles processing of individual code chunks for infrastructure analysis."""

    def __init__(self, config: Config, llm: LiteLLM, project_path: Optional[str] = None) -> None:
        self.config = config
        self.llm = llm
        self._project_path = project_path

        # Infrastructure analysis step
        self.infrastructure_step: LLMStep[AgentInput, InfrastructureAnalysisResult] = create_infrastructure_step(
            self.llm
        )

        # Keep test detection step as lazy since it depends on project setup for tools
        self._test_detection_step: Optional[LLMStep[TestDetectionInput, TestFileDetectionResult]] = None

    def get_test_detection_step(self) -> LLMStep[TestDetectionInput, TestFileDetectionResult]:
        """Get test file detection step with tool access."""
        if self._test_detection_step is None:
            self._test_detection_step = create_test_detection_step(self.llm, self.config, self._project_path)
        return self._test_detection_step

    async def process_single_chunk(
        self,
        chunk: CodeChunk,
        focus_environments: list[str] | None = None,
        include_secrets: bool = True,
        intelligent_test_detection: bool = True,
    ) -> list[InfrastructureAnalysisResult]:
        """Process a single chunk for infrastructure analysis."""
        try:
            self.config.logger.debug(f"Processing infrastructure chunk: {Path(chunk.file_path)}")

            # Run intelligent test file detection if enabled
            if intelligent_test_detection:
                test_detection_input = TestDetectionInput(
                    code=chunk,
                    config=self.config,
                    project_root=self._project_path,
                )

                try:
                    test_detection_step = self.get_test_detection_step()
                    test_result = await test_detection_step.run(test_detection_input)

                    if test_result.is_test_file:
                        self.config.logger.debug(
                            f"Skipping test file {chunk.file_path}: {test_result.reasoning} "
                            f"(confidence: {test_result.confidence:.2f}, category: {test_result.file_category})"
                        )
                        return []  # Skip processing this chunk

                    self.config.logger.debug(
                        f"Processing production file {chunk.file_path}: {test_result.reasoning} "
                        f"(confidence: {test_result.confidence:.2f})"
                    )

                except Exception as e:
                    # If test detection fails, log the error but continue with infrastructure analysis
                    self.config.logger.warning(
                        f"Test detection failed for {chunk.file_path}: {str(e)}. Proceeding with infrastructure analysis."
                    )

            # Run infrastructure analysis on non-test files
            chunk_input = AgentInput(
                code=chunk,
                config=self.config,
                focus_environments=focus_environments,
                include_secrets=include_secrets,
            )

            result = await self.infrastructure_step.run(chunk_input)
            return [result]

        except Exception as e:
            self.config.logger.error(
                f"Failed to process infrastructure chunk {chunk.file_path}:{chunk.line_number_start_inclusive}-{chunk.line_number_end_inclusive}: {str(e)}"
            )
            return []
