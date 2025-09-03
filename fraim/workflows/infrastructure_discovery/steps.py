# SPDX-License-Identifier: MIT
# Copyright (c) 2025 Resourcely Inc.

"""
Infrastructure Discovery Steps

LLM step creation and configuration logic for infrastructure discovery workflow.
"""

from pathlib import Path

from fraim.core.llms.litellm import LiteLLM
from fraim.core.parsers import PydanticOutputParser
from fraim.core.prompts.template import PromptTemplate
from fraim.core.steps.llm import LLMStep

from .types import AgentInput, InfrastructureAnalysisResult

# Load infrastructure prompts
INFRASTRUCTURE_PROMPTS = PromptTemplate.from_yaml(str(Path(__file__).parent / "infrastructure_prompts.yaml"))


def create_infrastructure_step(llm: LiteLLM) -> LLMStep[AgentInput, InfrastructureAnalysisResult]:
    """Create the main infrastructure analysis step."""
    infrastructure_parser = PydanticOutputParser(InfrastructureAnalysisResult)
    return LLMStep(llm, INFRASTRUCTURE_PROMPTS["system"], INFRASTRUCTURE_PROMPTS["user"], infrastructure_parser)
