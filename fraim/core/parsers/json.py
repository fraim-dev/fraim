# SPDX-License-Identifier: MIT
# Copyright (c) 2025 Resourcely Inc.

"""Parses an LLM response to JSON"""

from textwrap import dedent
from typing import Any

from fraim.core.parsers.base import BaseOutputParser, OutputParserError, ParseContext
from fraim.core.utils.json import parse_json_markdown


class JsonOutputParser(BaseOutputParser[Any]):
    """Parses an LLM response to JSON

    If the text is not valid JSON, try to find JSON within a markdown code block.

    Args:
        text: The text to parse

    Returns:
        The parsed JSON object

    Raises:
        OutputParserError: If the text is not valid JSON and could not be fixed
    """

    def output_prompt_instructions(self) -> str:
        return dedent("""
        <output_format>
          Format your response as valid JSON syntax as defined by RFC 8259.
        </output_format>
        """)

    async def parse(self, text: str, context: ParseContext | None = None) -> Any:
        try:
            return parse_json_markdown(text)
        except Exception as e:
            msg = f"Invalid JSON: {e}"
            raise OutputParserError(msg, raw_output=text) from e
