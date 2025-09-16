# SPDX-License-Identifier: MIT
# Copyright (c) 2025 Resourcely Inc.

"""Base class for LLMs"""

import asyncio
from abc import ABC, abstractmethod
from typing import Self

# Standardize on the OpenAI ModelResponse type
from litellm import ModelResponse

from fraim.core.history import History
from fraim.core.messages import Message
from fraim.core.tools import BaseTool


class BaseLLM(ABC):
    """Base class for LLMs"""

    @abstractmethod
    def with_tools(self, tools: list["BaseTool"], max_tool_iterations: int | None = None) -> Self:
        """Return a copy of the LLM with the given tools registered"""

    @abstractmethod
    async def run(self, history: History, prompt: list[Message]) -> ModelResponse:
        """Call the LLM asynchronously"""

    def run_sync(self, history: History, prompt: list[Message]) -> ModelResponse:
        """Call the LLM"""
        return asyncio.run(self.run(history, prompt))
