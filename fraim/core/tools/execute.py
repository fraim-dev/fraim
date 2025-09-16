# SPDX-License-Identifier: MIT
# Copyright (c) 2025 Resourcely Inc.

"""Tool execution utilities"""

import json
import logging
from typing import Any

from pydantic import BaseModel, ValidationError

from fraim.core.history import EventRecord, History
from fraim.core.messages import ToolCall, ToolMessage
from fraim.core.tools.base import BaseTool, ToolError


async def execute_tool_calls(
    history: History, tool_calls: list[ToolCall], available_tools: dict[str, BaseTool]
) -> list[ToolMessage]:
    """Execute multiple tool calls and return list of ToolMessage results.

    Args:
        tool_calls: List of ToolCall instances to execute
        available_tools: Dictionary mapping tool names to BaseTool instances

    Returns:
        List of ToolMessage objects with results or errors
    """
    results: list[ToolMessage] = []
    for tool_call in tool_calls:
        result = await execute_tool_call(history, tool_call, available_tools)
        results.append(result)
    return results


async def execute_tool_call(history: History, tool_call: ToolCall, available_tools: dict[str, BaseTool]) -> ToolMessage:
    """Execute a single tool call and return ToolMessage result.

    Args:
        tool_call: ToolCall instance to execute
        available_tools: Dictionary mapping tool names to BaseTool instances

    Returns:
        ToolMessage with result or error
    """
    tool = available_tools.get(tool_call.function.name)
    if not tool:
        error_msg = f"Tool '{tool_call.function.name}' not found"
        return ToolMessage(content=f"Error: {error_msg}", tool_call_id=tool_call.id)

    try:
        args_dict = _deserialize_arguments(tool_call.function.arguments, tool.args_schema)
    except ValidationError as e:
        error_msg = f"Invalid arguments for tool '{tool.name}': {e}"

        return ToolMessage(content=f"Error: {error_msg}", tool_call_id=tool_call.id)

    try:
        history.append_record(EventRecord(description=tool.display_message(**args_dict)))
        result = await tool.run(**args_dict)
        logging.getLogger().debug(f"Tool call result: {tool.name}: {result!s}")
        return ToolMessage(content=str(result), tool_call_id=tool_call.id)
    except ToolError as e:
        return ToolMessage(content=f"Error: {e}", tool_call_id=tool_call.id)


def _deserialize_arguments(arguments: str, schema: type[BaseModel] | None) -> dict[str, Any]:
    """Deserialize tool arguments using schema if available, otherwise fallback to JSON.

    Args:
        arguments: JSON string of arguments
        schema: Optional Pydantic model class for validation

    Returns:
        Dictionary of deserialized arguments

    Raises:
        Exception: If deserialization or validation fails
    """
    if not arguments:
        return {}

    if schema:
        # Use Pydantic schema for proper validation and type conversion
        validated_model = schema.model_validate_json(arguments)

        # Return a dictionary of the top-level fields
        return {
            field_name: getattr(validated_model, field_name) for field_name in validated_model.__class__.model_fields
        }
    # Fallback to generic JSON parsing
    parsed_result: dict[str, Any] = json.loads(arguments)
    return parsed_result
