# SPDX-License-Identifier: MIT
# Copyright (c) 2025 Resourcely Inc.

"""Base class for tools"""

import asyncio
import logging
from abc import ABC, abstractmethod
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from ...util.jsonschema.simplify import simplify_json_schema


class ToolError(ValueError):
    """Exception raised when tool execution fails due to invalid inputs or other errors."""


class BaseTool(BaseModel, ABC):
    """Base class for all tools.

    Args:
        name: The name of the tool
        description: Description of what the tool does
        args_schema: Pydantic model for tool arguments

    Implement the async _run method to define the tool's behavior. The run (and run_sync)
    methods will validate the arguments (if args_schema is provided) and call _run.

    Example:
        class MultiplyArgs(BaseModel):
            a: int
            b: int

        class MultiplyTool(BaseTool):
            name: str = "multiply"
            description: str = "Multiply two numbers"
            args_schema: Type[BaseModel] = MultiplyArgs

            async def _run(self, a: int, b: int) -> int:
                return a * b
    """

    name: str = Field(..., description="The name of the tool")
    description: str = Field(..., description="Description of what the tool does")
    args_schema: type[BaseModel] | None = Field(None, description="Pydantic model for tool arguments")

    # Allows `args_schema` to be a type (BaseModel) that is not serializable by Pydantic
    model_config = ConfigDict(arbitrary_types_allowed=True)

    @property
    def args(self) -> dict[str, Any]:
        """Get the arguments schema as a JSON schema dict."""
        if self.args_schema:
            return self.args_schema.model_json_schema()
        return {}

    @abstractmethod
    async def _run(self, *args: Any, **kwargs: Any) -> Any:
        """Run the tool implementation."""

    async def run(self, *args: Any, **kwargs: Any) -> Any:
        """Run the tool with optional validation."""
        logging.getLogger().debug(f"Running tool {self.name} with args: {args}")
        if self.args_schema:
            validated_kwargs = self._validate_args(**kwargs)
            return await self._run(*args, **validated_kwargs)
        return await self._run(*args, **kwargs)

    def run_sync(self, *args: Any, **kwargs: Any) -> Any:
        """Synchronous wrapper around the async run method."""
        return asyncio.run(self.run(*args, **kwargs))

    def display_message(self, *args: Any, **kwargs: Any) -> str:
        """Get a human-readable message for a tool call to display in the history UI."""
        return f"Calling tool {self.name}: {kwargs}"

    def to_openai_schema(self) -> dict[str, Any]:
        """Convert to OpenAI tool schema format."""
        if not self.args_schema:
            # Handle case where args_schema is None
            simplified_parameters: dict[str, Any] = {}
        else:
            simplified_parameters = simplify_json_schema(self.args_schema.model_json_schema())

        schema = {
            "type": "function",
            "function": {"name": self.name, "description": self.description, "parameters": simplified_parameters},
        }
        return schema

    def _validate_args(self, **kwargs: Any) -> dict[str, Any]:
        """Validate kwargs against the args_schema."""
        if not self.args_schema:
            return kwargs
        try:
            logging.getLogger().debug(f"Validating args for tool {self.name}")
            validated = self.args_schema(**kwargs)
            return validated.model_dump()
        except ValidationError as e:
            raise ToolError(f"Invalid arguments for tool '{self.name}': {e}") from e
