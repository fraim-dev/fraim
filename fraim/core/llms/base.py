# SPDX-License-Identifier: MIT
# Copyright (c) 2025 Resourcely Inc.

"""Base class for LLMs"""

import asyncio
from abc import ABC, abstractmethod
from typing import List, Optional, Self

# Standardize on the OpenAI ModelResponse type
from litellm import ModelResponse

from fraim.core.messages import Message
from fraim.core.tools import BaseTool


class BaseLLM(ABC):
    """Base class for LLMs"""

    @abstractmethod
    def with_tools(self, tools: List["BaseTool"], max_tool_iterations: Optional[int] = None) -> Self:
        """Return a copy of the LLM with the given tools registered"""

    @abstractmethod
    async def run(self, prompt: List[Message]) -> ModelResponse:
        """Call the LLM asynchronously"""

    def run_sync(self, prompt: List[Message]) -> ModelResponse:
        """Call the LLM"""
        return asyncio.run(self.run(prompt))
