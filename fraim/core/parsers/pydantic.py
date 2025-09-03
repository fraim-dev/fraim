# SPDX-License-Identifier: MIT
# Copyright (c) 2025 Resourcely Inc.

"""Parses an LLM response to a Pydantic model"""

import json
from textwrap import dedent
from typing import Generic, NoReturn, TypeVar

from pydantic import BaseModel, ValidationError

from fraim.core.parsers.base import OutputParserError, ParseContext
from fraim.core.parsers.json import JsonOutputParser

TBaseModel = TypeVar("TBaseModel", bound=BaseModel)


class PydanticOutputParser(JsonOutputParser, Generic[TBaseModel]):
    """Parses an LLM response to a Pydantic model

    If the text is not valid JSON, try to find JSON within a markdown code block.

    Args:
        model: The Pydantic model to parse the response into

    Returns:
        The parsed Pydantic model

    Raises:
        OutputParserError: If the text is not valid JSON or does not match the model schema
    """

    def __init__(self, model: type[TBaseModel]):
        self.model = model

    def output_prompt_instructions(self) -> str:
        return dedent(f"""
        <output_format>
          Format your response as a JSON object with the following schema. You MUST follow
          the schema exactly. You MUST use valid JSON syntax as defined by RFC 8259.
          <schema>
           {json.dumps(self.model.model_json_schema())}
          </schema>
        </output_format>
        """)

    async def parse(self, text: str, context: ParseContext | None = None) -> TBaseModel:
        json_obj = await super().parse(text, context)
        try:
            return self.model.model_validate(json_obj)
        except ValidationError as e:
            self._parse_error(text, e)

    def _parse_error(self, text: str, error: ValidationError) -> NoReturn:
        name = self.model.__name__
        msg = f"Could not parse JSON into {name}: {error}"
        explanation = f"Errors: {error.json()}"
        raise OutputParserError(msg, explanation, raw_output=text) from error
