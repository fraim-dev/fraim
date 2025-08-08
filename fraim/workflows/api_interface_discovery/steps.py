# SPDX-License-Identifier: MIT
# Copyright (c) 2025 Resourcely Inc.

"""
API Interface Discovery Steps

LLM step creation and configuration logic for API interface discovery workflow.
"""

from pathlib import Path
from typing import Optional

from fraim.config import Config
from fraim.core.llms.litellm import LiteLLM
from fraim.core.parsers import PydanticOutputParser
from fraim.core.prompts.template import PromptTemplate
from fraim.core.steps.llm import LLMStep
from fraim.tools.tree_sitter import TreeSitterTools

from .types import AgentInput, ApiInterfaceResult

# Load API interface prompts
API_INTERFACE_PROMPTS = PromptTemplate.from_yaml(str(Path(__file__).parent / "api_interface_prompts.yaml"))




def create_api_interface_step(
    llm: LiteLLM, config: Config, project_path: Optional[str] = None
) -> LLMStep[AgentInput, ApiInterfaceResult]:
    """Create the API interface analysis step with optional TreeSitter tools."""
    api_parser = PydanticOutputParser(ApiInterfaceResult)

    # Try to add TreeSitter tools if we have a valid project path
    enhanced_llm = llm
    if project_path:
        try:
            tree_sitter_tools = TreeSitterTools(project_path).tools
            enhanced_llm = llm.with_tools(tree_sitter_tools)
            config.logger.debug(f"TreeSitter tools initialized for API interface analysis with path: {project_path}")
        except Exception as e:
            config.logger.warning(
                f"Failed to initialize TreeSitter tools for API interface analysis, proceeding without tools: {str(e)}"
            )
    else:
        config.logger.warning("No project path available for TreeSitter tools, proceeding without tools")

    return LLMStep(enhanced_llm, API_INTERFACE_PROMPTS["system"], API_INTERFACE_PROMPTS["user"], api_parser)
