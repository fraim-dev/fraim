# SPDX-License-Identifier: MIT
# Copyright (c) 2025 Resourcely Inc.

"""Tests for tool execution utilities"""

from typing import Any

import pytest
from pydantic import BaseModel, Field

from fraim.core.history import History
from fraim.core.messages import Function, ToolCall, ToolMessage
from fraim.core.tools.base import BaseTool, ToolError
from fraim.core.tools.execute import execute_tool_call, execute_tool_calls


class MultiplyArgs(BaseModel):
    """Arguments for multiply tool"""

    a: int = Field(description="First number to multiply")
    b: int = Field(description="Second number to multiply")


class MultiplyTool(BaseTool):
    """A simple tool that multiplies two numbers"""

    name: str = "multiply"
    description: str = "Multiply two numbers"
    args_schema: type[BaseModel] = MultiplyArgs

    async def _run(self, a: int, b: int) -> int:
        return a * b


class ErrorTool(BaseTool):
    """A tool that always raises a ToolError"""

    name: str = "error_tool"
    description: str = "A tool that always fails"
    args_schema: type[BaseModel] = MultiplyArgs

    async def _run(self, a: int, b: int) -> int:
        raise ToolError("This tool always fails")


class NoSchemaTool(BaseTool):
    """A tool without argument schema"""

    name: str = "no_schema"
    description: str = "A tool without schema"
    args_schema: type[BaseModel] | None = None

    async def _run(self, **kwargs: Any) -> str:
        return f"Called with: {kwargs}"


class TestExecuteToolCall:
    """Test cases for execute_tool_call function"""

    @pytest.fixture
    def multiply_tool(self) -> MultiplyTool:
        """Fixture providing a multiply tool instance"""
        return MultiplyTool()

    @pytest.fixture
    def error_tool(self) -> ErrorTool:
        """Fixture providing an error tool instance"""
        return ErrorTool()

    @pytest.fixture
    def no_schema_tool(self) -> NoSchemaTool:
        """Fixture providing a tool without schema"""
        return NoSchemaTool()

    @pytest.fixture
    def available_tools(
        self, multiply_tool: MultiplyTool, error_tool: ErrorTool, no_schema_tool: NoSchemaTool
    ) -> dict[str, BaseTool]:
        """Fixture providing a dictionary of available tools"""
        return {
            "multiply": multiply_tool,
            "error_tool": error_tool,
            "no_schema": no_schema_tool,
        }

    def create_tool_call(self, tool_name: str, arguments: str, call_id: str = "test-call-1") -> ToolCall:
        """Helper to create a ToolCall instance"""
        return ToolCall(id=call_id, type="function", function=Function(name=tool_name, arguments=arguments))

    @pytest.mark.asyncio
    async def test_successful_multiply(self, available_tools: dict[str, BaseTool]) -> None:
        """Test successful multiplication - happy path"""
        tool_call = self.create_tool_call(tool_name="multiply", arguments='{"a": 5, "b": 3}')

        result = await execute_tool_call(History(), tool_call, available_tools)

        assert isinstance(result, ToolMessage)
        assert result.content == "15"
        assert result.tool_call_id == "test-call-1"
        assert result.role == "tool"

    @pytest.mark.asyncio
    async def test_tool_not_found(self, available_tools: dict[str, BaseTool]) -> None:
        """Test error when tool is not found"""
        tool_call = self.create_tool_call(tool_name="nonexistent_tool", arguments='{"a": 5, "b": 3}')

        result = await execute_tool_call(History(), tool_call, available_tools)

        assert isinstance(result, ToolMessage)
        assert result.content == "Error: Tool 'nonexistent_tool' not found"
        assert result.tool_call_id == "test-call-1"

    @pytest.mark.asyncio
    async def test_invalid_json_arguments(self, available_tools: dict[str, BaseTool]) -> None:
        """Test error when arguments are invalid JSON"""
        tool_call = self.create_tool_call(
            tool_name="multiply",
            arguments='{"a": 5, "b":}',  # Invalid JSON
        )

        result = await execute_tool_call(History(), tool_call, available_tools)

        assert isinstance(result, ToolMessage)
        assert "Error: Invalid arguments for tool 'multiply'" in result.content
        assert result.tool_call_id == "test-call-1"

    @pytest.mark.asyncio
    async def test_missing_required_arguments(self, available_tools: dict[str, BaseTool]) -> None:
        """Test error when required arguments are missing"""
        tool_call = self.create_tool_call(
            tool_name="multiply",
            arguments='{"a": 5}',  # Missing 'b'
        )

        result = await execute_tool_call(History(), tool_call, available_tools)

        assert isinstance(result, ToolMessage)
        assert "Error: Invalid arguments for tool 'multiply'" in result.content
        assert result.tool_call_id == "test-call-1"

    @pytest.mark.asyncio
    async def test_wrong_argument_types(self, available_tools: dict[str, BaseTool]) -> None:
        """Test error when argument types are wrong"""
        tool_call = self.create_tool_call(
            tool_name="multiply",
            arguments='{"a": "not_a_number", "b": 3}',  # Wrong type for 'a'
        )

        result = await execute_tool_call(History(), tool_call, available_tools)

        assert isinstance(result, ToolMessage)
        assert "Error: Invalid arguments for tool 'multiply'" in result.content
        assert result.tool_call_id == "test-call-1"

    @pytest.mark.asyncio
    async def test_extra_arguments_ignored(self, available_tools: dict[str, BaseTool]) -> None:
        """Test that extra arguments are ignored when schema is present"""
        tool_call = self.create_tool_call(tool_name="multiply", arguments='{"a": 5, "b": 3, "extra": "ignored"}')

        result = await execute_tool_call(History(), tool_call, available_tools)

        assert result.content == "15"
        assert result.tool_call_id == "test-call-1"

    @pytest.mark.asyncio
    async def test_empty_arguments_with_schema(self, available_tools: dict[str, BaseTool]) -> None:
        """Test error when arguments are empty but schema requires them"""
        tool_call = self.create_tool_call(tool_name="multiply", arguments="")

        result = await execute_tool_call(History(), tool_call, available_tools)

        assert isinstance(result, ToolMessage)
        assert "Error: Invalid arguments for tool 'multiply'" in result.content
        assert result.tool_call_id == "test-call-1"

    @pytest.mark.asyncio
    async def test_tool_raises_tool_error(self, available_tools: dict[str, BaseTool]) -> None:
        """Test handling when tool raises ToolError"""
        tool_call = self.create_tool_call(tool_name="error_tool", arguments='{"a": 5, "b": 3}')

        result = await execute_tool_call(History(), tool_call, available_tools)

        assert isinstance(result, ToolMessage)
        assert result.content == "Error: This tool always fails"
        assert result.tool_call_id == "test-call-1"

    @pytest.mark.asyncio
    async def test_tool_without_schema(self, available_tools: dict[str, BaseTool]) -> None:
        """Test tool execution without argument schema"""
        tool_call = self.create_tool_call(tool_name="no_schema", arguments='{"any": "arguments", "are": "accepted"}')

        result = await execute_tool_call(History(), tool_call, available_tools)

        assert isinstance(result, ToolMessage)
        assert "Called with: {'any': 'arguments', 'are': 'accepted'}" in result.content
        assert result.tool_call_id == "test-call-1"

    @pytest.mark.asyncio
    async def test_tool_without_schema_empty_args(self, available_tools: dict[str, BaseTool]) -> None:
        """Test tool execution without schema and empty arguments"""
        tool_call = self.create_tool_call(tool_name="no_schema", arguments="")

        result = await execute_tool_call(History(), tool_call, available_tools)

        assert isinstance(result, ToolMessage)
        assert "Called with: {}" in result.content
        assert result.tool_call_id == "test-call-1"

    @pytest.mark.asyncio
    async def test_different_call_ids(self, available_tools: dict[str, BaseTool]) -> None:
        """Test that tool call IDs are preserved correctly"""
        tool_call = self.create_tool_call(tool_name="multiply", arguments='{"a": 2, "b": 4}', call_id="custom-id-123")

        result = await execute_tool_call(History(), tool_call, available_tools)

        assert result.content == "8"
        assert result.tool_call_id == "custom-id-123"


class TestExecuteToolCalls:
    """Test cases for execute_tool_calls function (multiple calls)"""

    @pytest.fixture
    def multiply_tool(self) -> MultiplyTool:
        """Fixture providing a multiply tool instance"""
        return MultiplyTool()

    @pytest.fixture
    def available_tools(self, multiply_tool: MultiplyTool) -> dict[str, BaseTool]:
        """Fixture providing a dictionary of available tools"""
        return {"multiply": multiply_tool}

    def create_tool_call(self, tool_name: str, arguments: str, call_id: str) -> ToolCall:
        """Helper to create a ToolCall instance"""
        return ToolCall(id=call_id, type="function", function=Function(name=tool_name, arguments=arguments))

    @pytest.mark.asyncio
    async def test_multiple_successful_calls(self, available_tools: dict[str, BaseTool]) -> None:
        """Test execution of multiple successful tool calls"""
        tool_calls = [
            self.create_tool_call("multiply", '{"a": 2, "b": 3}', "call-1"),
            self.create_tool_call("multiply", '{"a": 4, "b": 5}', "call-2"),
            self.create_tool_call("multiply", '{"a": 6, "b": 7}', "call-3"),
        ]

        results = await execute_tool_calls(History(), tool_calls, available_tools)

        assert len(results) == 3
        assert all(isinstance(result, ToolMessage) for result in results)

        assert results[0].content == "6"
        assert results[0].tool_call_id == "call-1"

        assert results[1].content == "20"
        assert results[1].tool_call_id == "call-2"

        assert results[2].content == "42"
        assert results[2].tool_call_id == "call-3"

    @pytest.mark.asyncio
    async def test_mixed_success_and_failure(self, available_tools: dict[str, BaseTool]) -> None:
        """Test execution with mix of successful and failed calls"""
        tool_calls = [
            self.create_tool_call("multiply", '{"a": 2, "b": 3}', "call-1"),
            self.create_tool_call("nonexistent", '{"a": 4, "b": 5}', "call-2"),
            self.create_tool_call("multiply", '{"a": "invalid", "b": 7}', "call-3"),
        ]

        results = await execute_tool_calls(History(), tool_calls, available_tools)

        assert len(results) == 3

        # First call should succeed
        assert results[0].content == "6"
        assert results[0].tool_call_id == "call-1"

        # Second call should fail (tool not found)
        assert "Error: Tool 'nonexistent' not found" in results[1].content
        assert results[1].tool_call_id == "call-2"

        # Third call should fail (invalid arguments)
        assert "Error: Invalid arguments for tool 'multiply'" in results[2].content
        assert results[2].tool_call_id == "call-3"

    @pytest.mark.asyncio
    async def test_empty_tool_calls_list(self, available_tools: dict[str, BaseTool]) -> None:
        """Test execution with empty list of tool calls"""
        results = await execute_tool_calls(History(), [], available_tools)

        assert results == []
