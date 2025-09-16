# SPDX-License-Identifier: MIT
# Copyright (c) 2025 Resourcely Inc.

"""Base class for output parsers"""

import asyncio
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Generic, TypeVar

from fraim.core.history import History
from fraim.core.llms.base import BaseLLM
from fraim.core.messages import Message

T = TypeVar("T")


@dataclass
class ParseContext:
    """Context object containing LLM and conversation history for parsers that need retry functionality"""

    llm: BaseLLM
    history: History
    messages: list[Message]


class BaseOutputParser(ABC, Generic[T]):
    """Base class for output parsers"""

    # TODO: consider making BaseOutputParser a Contextual
    @abstractmethod
    def output_prompt_instructions(self) -> str:
        """Return a prompt instruction for the output of an LLM call"""

    @abstractmethod
    async def parse(self, text: str, context: ParseContext | None = None) -> T:
        """Parse the output of an LLM call"""

    def parse_sync(self, text: str, context: ParseContext | None = None) -> T:
        """Parse the output of an LLM call"""
        return asyncio.run(self.parse(text, context))


class OutputParserError(ValueError):
    """Error raised by output parsers when parsing fails."""

    def __init__(self, msg: str, explanation: str | None = None, raw_output: str | None = None):
        """
        Args:
            msg: Brief description of the error
            explanation: Additional details about the error
            raw_output: The raw LLM output that failed to parse
        """
        super().__init__(msg)
        self.explanation = explanation
        self.raw_output = raw_output
