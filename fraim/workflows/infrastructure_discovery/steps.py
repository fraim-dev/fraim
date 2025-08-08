# SPDX-License-Identifier: MIT
# Copyright (c) 2025 Resourcely Inc.

"""
Infrastructure Discovery Steps

LLM step creation and configuration logic for infrastructure discovery workflow.
"""

from pathlib import Path
from typing import Optional

from fraim.config import Config
from fraim.core.llms.litellm import LiteLLM
from fraim.core.parsers import PydanticOutputParser
from fraim.core.prompts.template import PromptTemplate
from fraim.core.steps.llm import LLMStep
from fraim.tools.tree_sitter import TreeSitterTools

from .types import AgentInput, DedupInput, InfrastructureAnalysisResult

# Load infrastructure prompts
INFRASTRUCTURE_PROMPTS = PromptTemplate.from_yaml(str(Path(__file__).parent / "infrastructure_prompts.yaml"))
INFRASTRUCTURE_DEDUP_PROMPTS = PromptTemplate.from_yaml(
    str(Path(__file__).parent / "infrastructure_dedup_prompts.yaml")
)


def create_infrastructure_step(llm: LiteLLM) -> LLMStep[AgentInput, InfrastructureAnalysisResult]:
    """Create the main infrastructure analysis step."""
    infrastructure_parser = PydanticOutputParser(InfrastructureAnalysisResult)
    return LLMStep(llm, INFRASTRUCTURE_PROMPTS["system"], INFRASTRUCTURE_PROMPTS["user"], infrastructure_parser)


def create_dedup_step(
    llm: LiteLLM, config: Config, project_path: Optional[str] = None
) -> LLMStep[DedupInput, InfrastructureAnalysisResult]:
    """Create the deduplication step with optional TreeSitter tools."""
    dedup_parser = PydanticOutputParser(InfrastructureAnalysisResult)

    # Try to add TreeSitter tools if we have a valid project path
    dedup_llm = llm
    if project_path:
        try:
            # Add TreeSitter tools for infrastructure analysis
            dedup_tools = TreeSitterTools(project_path).tools
            dedup_llm = llm.with_tools(dedup_tools)
            config.logger.debug(f"TreeSitter tools initialized for deduplication with path: {project_path}")
        except Exception as e:
            config.logger.warning(
                f"Failed to initialize TreeSitter tools for deduplication, proceeding without tools: {str(e)}"
            )
    else:
        config.logger.warning("No project path available for TreeSitter tools, proceeding without tools")

    return LLMStep(
        dedup_llm, INFRASTRUCTURE_DEDUP_PROMPTS["system"], INFRASTRUCTURE_DEDUP_PROMPTS["user"], dedup_parser
    )
