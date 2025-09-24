# SPDX-License-Identifier: MIT
# Copyright (c) 2025 Resourcely Inc.

"""Text output parser that returns raw string responses without interpretation."""

from textwrap import dedent

from .base import BaseOutputParser, ParseContext


class TextOutputParser(BaseOutputParser[str]):
    """Parser that returns the raw string response without any interpretation or parsing."""

    def __init__(self, instructions: str):
        """
        Initialize the TextOutputParser with the output instructions.

        Args:
            instructions: Instructions to include in the output format prompt
                         that tell the LLM should format its response.

        Example:
            TextOutputParser("Use the add_sarif_result tool to record the findings as SARIF `Result` objects as you go.\n\n"
                             "For your final text response, return a succint summary of your analysis.")
        """
        self.instructions = instructions

    def output_prompt_instructions(self) -> str:
        return dedent("""
        <output_format>
          { self.instructions }
        </output_format>
        """)

    async def parse(self, text: str, context: ParseContext | None = None) -> str:
        """
        Parse the text by returning it as-is without any modification.

        Args:
            text: The raw text response to parse
            context: Optional parse context (unused for text parsing)

        Returns:
            str: The original text unchanged
        """
        return text
