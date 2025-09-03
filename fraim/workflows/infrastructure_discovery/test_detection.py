# SPDX-License-Identifier: MIT
# Copyright (c) 2025 Resourcely Inc.

"""
Test File Detection for Infrastructure Discovery

LLM-based intelligent detection of test, example, and mock files.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field

from fraim.config import Config
from fraim.core.contextuals import CodeChunk
from fraim.core.llms.base import BaseLLM
from fraim.core.parsers import PydanticOutputParser
from fraim.core.prompts.template import PromptTemplate
from fraim.core.steps.llm import LLMStep


class TestFileDetectionResult(BaseModel):
    """Result of test file detection analysis."""

    is_test_file: bool = Field(description="Whether the file appears to be a test, example, mock, or demo file")

    confidence: float = Field(description="Confidence level (0.0-1.0) in the test file determination")

    reasoning: str = Field(description="Brief explanation of why the file was classified as test or production code")

    file_category: str = Field(description="Category of the file: test|example|mock|demo|fixture|production|unknown")


@dataclass
class TestDetectionInput:
    """Input for test file detection analysis."""

    code: CodeChunk
    config: Config
    project_root: Optional[str] = None


# Load test detection prompts
TEST_DETECTION_PROMPTS = PromptTemplate.from_yaml(str(Path(__file__).parent / "test_detection_prompts.yaml"))


def create_test_detection_step(
    llm: BaseLLM, config: Config, project_path: Optional[str] = None
) -> LLMStep[TestDetectionInput, TestFileDetectionResult]:
    """Create an LLM step for detecting test files."""

    test_detection_parser = PydanticOutputParser(TestFileDetectionResult)

    return LLMStep(
        llm=llm,
        system_prompt=TEST_DETECTION_PROMPTS["system"],
        user_prompt=TEST_DETECTION_PROMPTS["user"],
        parser=test_detection_parser,
    )
