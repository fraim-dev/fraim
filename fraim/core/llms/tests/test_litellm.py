# SPDX-License-Identifier: MIT
# Copyright (c) 2025 Resourcely Inc.

from unittest.mock import Mock, patch

import pytest
from litellm import ModelResponse
from pydantic import BaseModel, Field

from fraim.core.history import History
from fraim.core.llms.litellm import LiteLLM
from fraim.core.messages import AssistantMessage, Function, Message, SystemMessage, ToolCall, ToolMessage, UserMessage
from fraim.core.tools.base import BaseTool, ToolError


class MockArgs(BaseModel):
    value: int = Field(description="A test value")


class ErrorArgs(BaseModel):
    should_error: bool = Field(description="Whether to raise an error")


class MockTool(BaseTool):
    """Mock tool for testing"""

    async def _run(self, value: int) -> str:
        return f"Mock result: {value}"


class ErrorTool(BaseTool):
    """Mock tool that raises errors"""

    async def _run(self, should_error: bool) -> str:
        if should_error:
            raise ToolError("Mock tool error")
        return "Success"


def create_mock_response(content: str = "Test response", tool_calls: list[ToolCall] | None = None) -> ModelResponse:
    """Helper to create mock ModelResponse objects"""
    mock_response = Mock(spec=ModelResponse)
    mock_message = Mock()
    mock_message.content = content
    mock_message.tool_calls = tool_calls or []
    mock_choice = Mock()
    mock_choice.message = mock_message
    mock_response.choices = [mock_choice]
    return mock_response


class TestLiteLLMInit:
    """Test LiteLLM initialization"""

    def test_init_with_minimal_params(self) -> None:
        """Test initialization with minimal required parameters"""
        llm = LiteLLM(model="gpt-3.5-turbo")

        assert llm.model == "gpt-3.5-turbo"
        assert llm.additional_model_params == {}
        assert llm.max_tool_iterations == 10
        assert llm.tools == []
        assert llm.tools_dict == {}
        assert llm.tools_schema == []

    def test_init_with_all_params(self) -> None:
        """Test initialization with all parameters"""
        mock_tool = MockTool(name="mock_tool", description="A mock tool for testing", args_schema=MockArgs)
        additional_params = {"temperature": 0.7, "max_tokens": 100}

        llm = LiteLLM(
            model="gpt-4", additional_model_params=additional_params, max_tool_iterations=5, tools=[mock_tool]
        )

        assert llm.model == "gpt-4"
        assert llm.additional_model_params == additional_params
        assert llm.max_tool_iterations == 5
        assert len(llm.tools) == 1
        assert llm.tools[0] == mock_tool
        assert "mock_tool" in llm.tools_dict
        assert len(llm.tools_schema) == 1

    def test_init_with_negative_max_iterations_raises_error(self) -> None:
        """Test that negative max_tool_iterations raises ValueError"""
        with pytest.raises(ValueError, match="max_tool_iterations must be a non-negative integer"):
            LiteLLM(model="gpt-3.5-turbo", max_tool_iterations=-1)

    def test_init_with_zero_max_iterations(self) -> None:
        """Test initialization with zero max_tool_iterations"""
        llm = LiteLLM(model="gpt-3.5-turbo", max_tool_iterations=0)
        assert llm.max_tool_iterations == 0


class TestLiteLLMWithTools:
    """Test the with_tools method"""

    def test_with_tools_creates_new_instance(self) -> None:
        """Test that with_tools returns a new LiteLLM instance"""
        original_llm = LiteLLM(model="gpt-3.5-turbo", max_tool_iterations=5)
        mock_tool = MockTool(name="mock_tool", description="A mock tool for testing", args_schema=MockArgs)

        new_llm = original_llm.with_tools([mock_tool])

        assert new_llm is not original_llm
        assert new_llm.model == original_llm.model
        assert new_llm.max_tool_iterations == original_llm.max_tool_iterations
        assert len(new_llm.tools) == 1
        assert new_llm.tools[0] == mock_tool

    def test_with_tools_preserves_additional_params(self) -> None:
        """Test that with_tools preserves additional model parameters"""
        additional_params = {"temperature": 0.8}
        original_llm = LiteLLM(model="gpt-4", additional_model_params=additional_params)
        mock_tool = MockTool(name="mock_tool", description="A mock tool for testing", args_schema=MockArgs)

        new_llm = original_llm.with_tools([mock_tool])

        assert new_llm.additional_model_params == additional_params

    def test_with_tools_overrides_max_tool_iterations(self) -> None:
        """Test that with_tools can override max_tool_iterations"""
        original_llm = LiteLLM(model="gpt-3.5-turbo", max_tool_iterations=10)
        mock_tool = MockTool(name="mock_tool", description="A mock tool for testing", args_schema=MockArgs)

        new_llm = original_llm.with_tools([mock_tool], max_tool_iterations=3)

        assert new_llm is not original_llm
        assert new_llm.model == original_llm.model
        assert new_llm.max_tool_iterations == 3  # Should be overridden
        assert original_llm.max_tool_iterations == 10  # Original should be unchanged
        assert len(new_llm.tools) == 1
        assert new_llm.tools[0] == mock_tool

    def test_with_tools_preserves_max_tool_iterations_when_none(self) -> None:
        """Test that with_tools preserves original max_tool_iterations when None is passed"""
        original_llm = LiteLLM(model="gpt-3.5-turbo", max_tool_iterations=7)
        mock_tool = MockTool(name="mock_tool", description="A mock tool for testing", args_schema=MockArgs)

        new_llm = original_llm.with_tools([mock_tool], max_tool_iterations=None)

        assert new_llm.max_tool_iterations == 7  # Should preserve original value

    def test_with_tools_allows_zero_max_tool_iterations(self) -> None:
        """Test that with_tools allows setting max_tool_iterations to zero"""
        original_llm = LiteLLM(model="gpt-3.5-turbo", max_tool_iterations=5)
        mock_tool = MockTool(name="mock_tool", description="A mock tool for testing", args_schema=MockArgs)

        new_llm = original_llm.with_tools([mock_tool], max_tool_iterations=0)

        assert new_llm.max_tool_iterations == 0


class TestLiteLLMPrepareCompletionParams:
    """Test the _prepare_completion_params method"""

    def test_prepare_params_without_tools(self) -> None:
        """Test parameter preparation without tools"""
        llm = LiteLLM(model="gpt-3.5-turbo", additional_model_params={"temperature": 0.7})
        messages: list[Message] = [UserMessage(content="Hello")]

        params = llm._prepare_completion_params(messages, use_tools=False)

        # Messages should be converted to dictionaries
        expected_messages = [msg.model_dump() for msg in messages]
        expected_params = {"model": "gpt-3.5-turbo", "messages": expected_messages, "temperature": 0.7}
        assert params == expected_params

    def test_prepare_params_with_tools(self) -> None:
        """Test parameter preparation with tools"""
        mock_tool = MockTool(name="mock_tool", description="A mock tool for testing", args_schema=MockArgs)
        llm = LiteLLM(model="gpt-3.5-turbo", tools=[mock_tool])
        messages: list[Message] = [UserMessage(content="Hello")]

        params = llm._prepare_completion_params(messages, use_tools=True)

        assert params["model"] == "gpt-3.5-turbo"
        # Messages should be converted to dictionaries
        expected_messages = [msg.model_dump() for msg in messages]
        assert params["messages"] == expected_messages
        assert "tools" in params
        assert len(params["tools"]) == 1

    def test_prepare_params_with_multiple_message_types(self) -> None:
        """Test parameter preparation with different message types"""
        llm = LiteLLM(model="gpt-3.5-turbo")
        messages: list[Message] = [
            SystemMessage(content="You are a helpful assistant"),
            UserMessage(content="Hello"),
            AssistantMessage(content="Hi there!"),
        ]

        params = llm._prepare_completion_params(messages, use_tools=False)

        # Messages should be converted to dictionaries
        expected_messages = [msg.model_dump() for msg in messages]
        assert params["messages"] == expected_messages

    def test_prepare_params_with_tools_disabled(self) -> None:
        """Test parameter preparation with tools disabled even when LLM has tools"""
        mock_tool = MockTool(name="mock_tool", description="A mock tool for testing", args_schema=MockArgs)
        llm = LiteLLM(model="gpt-3.5-turbo", tools=[mock_tool])
        messages: list[Message] = [UserMessage(content="Hello")]

        params = llm._prepare_completion_params(messages, use_tools=False)

        assert params["model"] == "gpt-3.5-turbo"
        # Messages should be converted to dictionaries
        expected_messages = [msg.model_dump() for msg in messages]
        assert params["messages"] == expected_messages
        assert "tools" not in params  # Should not include tools when use_tools=False


class TestLiteLLMRunOnce:
    """Test the _run_once method"""

    @pytest.mark.asyncio
    async def test_run_once_without_tool_calls(self) -> None:
        """Test _run_once when LLM doesn't make tool calls"""
        llm = LiteLLM(model="gpt-3.5-turbo")
        messages: list[Message] = [UserMessage(content="Hello")]
        mock_response = create_mock_response("Hello there!")

        with patch("litellm.acompletion", return_value=mock_response) as mock_completion:
            response, updated_messages, tools_executed = await llm._run_once(History(), messages, use_tools=False)

            assert response == mock_response
            assert updated_messages == messages  # No new messages added
            assert tools_executed is False
            mock_completion.assert_called_once()

    @pytest.mark.asyncio
    async def test_run_once_with_tool_calls(self) -> None:
        """Test _run_once when LLM makes tool calls"""
        mock_tool = MockTool(name="mock_tool", description="A mock tool for testing", args_schema=MockArgs)
        llm = LiteLLM(model="gpt-3.5-turbo", tools=[mock_tool])
        messages: list[Message] = [UserMessage(content="Use the mock tool")]

        tool_call = ToolCall(
            id="call_123", function=Function(name="mock_tool", arguments='{"value": 42}'), type="function"
        )
        mock_response = create_mock_response("I'll use the tool", [tool_call])

        with patch("litellm.acompletion", return_value=mock_response):
            response, updated_messages, tools_executed = await llm._run_once(History(), messages, use_tools=True)

            assert response == mock_response
            assert tools_executed is True
            assert len(updated_messages) == 3  # original + assistant + tool response

            # Check assistant message
            assistant_msg = updated_messages[1]
            assert isinstance(assistant_msg, AssistantMessage)
            assert assistant_msg.content == "I'll use the tool"
            assert assistant_msg.tool_calls == [tool_call]

            # Check tool message
            tool_msg = updated_messages[2]
            assert isinstance(tool_msg, ToolMessage)
            assert tool_msg.tool_call_id == "call_123"
            assert "Mock result: 42" in tool_msg.content

    @pytest.mark.asyncio
    async def test_run_once_with_empty_content(self) -> None:
        """Test _run_once when LLM returns empty content"""
        llm = LiteLLM(model="gpt-3.5-turbo")
        messages: list[Message] = [UserMessage(content="Hello")]
        mock_response = create_mock_response("")

        with patch("litellm.acompletion", return_value=mock_response):
            response, updated_messages, tools_executed = await llm._run_once(History(), messages, use_tools=False)

            assert response == mock_response
            assert updated_messages == messages
            assert tools_executed is False

    @pytest.mark.asyncio
    async def test_run_once_with_tool_error(self) -> None:
        """Test _run_once when tool execution fails"""
        error_tool = ErrorTool(name="error_tool", description="A tool that raises errors", args_schema=ErrorArgs)
        llm = LiteLLM(model="gpt-3.5-turbo", tools=[error_tool])
        messages: list[Message] = [UserMessage(content="Use the error tool")]

        tool_call = ToolCall(
            id="call_error", function=Function(name="error_tool", arguments='{"should_error": true}'), type="function"
        )
        mock_response = create_mock_response("I'll use the error tool", [tool_call])

        with patch("litellm.acompletion", return_value=mock_response):
            response, updated_messages, tools_executed = await llm._run_once(History(), messages, use_tools=True)

            assert tools_executed is True
            tool_msg = updated_messages[2]
            assert isinstance(tool_msg, ToolMessage)
            assert "Error: Mock tool error" in tool_msg.content


class TestLiteLLMRun:
    """Test the main run method"""

    @pytest.mark.asyncio
    async def test_run_without_tools(self) -> None:
        """Test run method without tool calls"""
        llm = LiteLLM(model="gpt-3.5-turbo")
        messages: list[Message] = [UserMessage(content="Hello")]
        mock_response = create_mock_response("Hello there!")

        with patch("litellm.acompletion", return_value=mock_response) as mock_completion:
            result = await llm.run(History(), messages)

            assert result == mock_response
            mock_completion.assert_called_once()

    @pytest.mark.asyncio
    async def test_run_with_single_tool_iteration(self) -> None:
        """Test run method with one tool call iteration"""
        mock_tool = MockTool(name="mock_tool", description="A mock tool for testing", args_schema=MockArgs)
        llm = LiteLLM(model="gpt-3.5-turbo", tools=[mock_tool], max_tool_iterations=5)
        messages: list[Message] = [UserMessage(content="Use the tool")]

        # First call with tool calls
        tool_call = ToolCall(
            id="call_123", function=Function(name="mock_tool", arguments='{"value": 42}'), type="function"
        )
        first_response = create_mock_response("Using tool", [tool_call])

        # Second call without tool calls (final response)
        final_response = create_mock_response("Tool result processed")

        with patch("litellm.acompletion", side_effect=[first_response, final_response]) as mock_completion:
            result = await llm.run(History(), messages)

            assert result == final_response
            assert mock_completion.call_count == 2

    @pytest.mark.asyncio
    async def test_run_reaches_max_iterations(self) -> None:
        """Test run method when max tool iterations is reached"""
        mock_tool = MockTool(name="mock_tool", description="A mock tool for testing", args_schema=MockArgs)
        llm = LiteLLM(model="gpt-3.5-turbo", tools=[mock_tool], max_tool_iterations=2)
        messages: list[Message] = [UserMessage(content="Keep using tools")]

        # Create tool call that keeps triggering
        tool_call = ToolCall(
            id="call_123", function=Function(name="mock_tool", arguments='{"value": 1}'), type="function"
        )

        # First two calls with tool calls
        tool_response = create_mock_response("Using tool again", [tool_call])
        # Final call without tools (forced)
        final_response = create_mock_response("Final response without tools")

        with patch(
            "litellm.acompletion", side_effect=[tool_response, tool_response, final_response]
        ) as mock_completion:
            result = await llm.run(History(), messages)

            assert result == final_response
            assert mock_completion.call_count == 3

            # Check that the final call doesn't include tools
            final_call_args = mock_completion.call_args_list[-1]
            assert "tools" not in final_call_args[1]

    @pytest.mark.asyncio
    async def test_run_with_zero_max_iterations(self) -> None:
        """Test run method with zero max iterations"""
        mock_tool = MockTool(name="mock_tool", description="A mock tool for testing", args_schema=MockArgs)
        llm = LiteLLM(model="gpt-3.5-turbo", tools=[mock_tool], max_tool_iterations=0)
        messages: list[Message] = [UserMessage(content="Hello")]
        mock_response = create_mock_response("Response without tools")

        with patch("litellm.acompletion", return_value=mock_response) as mock_completion:
            result = await llm.run(History(), messages)

            assert result == mock_response
            mock_completion.assert_called_once()
            # Should not include tools in the call
            call_args = mock_completion.call_args
            assert "tools" not in call_args[1]

    @pytest.mark.asyncio
    async def test_run_preserves_original_messages(self) -> None:
        """Test that run method doesn't modify the original messages list"""
        llm = LiteLLM(model="gpt-3.5-turbo")
        original_messages: list[Message] = [UserMessage(content="Hello")]
        messages_copy = original_messages.copy()
        mock_response = create_mock_response("Hello there!")

        with patch("litellm.acompletion", return_value=mock_response):
            await llm.run(History(), original_messages)

            assert original_messages == messages_copy

    @pytest.mark.asyncio
    async def test_run_with_litellm_exception(self) -> None:
        """Test run method when litellm.acompletion raises an exception"""
        llm = LiteLLM(model="gpt-3.5-turbo")
        messages: list[Message] = [UserMessage(content="Hello")]

        with patch("litellm.acompletion", side_effect=Exception("API Error")):
            with pytest.raises(Exception, match="API Error"):
                await llm.run(History(), messages)


class TestLiteLLMIntegration:
    """Integration tests combining multiple features"""

    @pytest.mark.asyncio
    async def test_complex_tool_interaction_flow(self) -> None:
        """Test a complex flow with multiple tools and iterations"""
        mock_tool = MockTool(name="mock_tool", description="A mock tool for testing", args_schema=MockArgs)
        error_tool = ErrorTool(name="error_tool", description="A tool that raises errors", args_schema=ErrorArgs)
        llm = LiteLLM(
            model="gpt-4",
            tools=[mock_tool, error_tool],
            max_tool_iterations=3,
            additional_model_params={"temperature": 0.5},
        )

        messages: list[Message] = [
            SystemMessage(content="You are a helpful assistant"),
            UserMessage(content="Use both tools"),
        ]

        # First iteration: use mock_tool
        tool_call_1 = ToolCall(
            id="call_1", function=Function(name="mock_tool", arguments='{"value": 10}'), type="function"
        )
        response_1 = create_mock_response("Using mock tool", [tool_call_1])

        # Second iteration: use error_tool (success)
        tool_call_2 = ToolCall(
            id="call_2", function=Function(name="error_tool", arguments='{"should_error": false}'), type="function"
        )
        response_2 = create_mock_response("Using error tool", [tool_call_2])

        # Final iteration: no tools
        final_response = create_mock_response("All tools completed successfully")

        with patch("litellm.acompletion", side_effect=[response_1, response_2, final_response]) as mock_completion:
            result = await llm.run(History(), messages)

            assert result == final_response
            assert mock_completion.call_count == 3

            # Verify parameters passed to each call
            calls = mock_completion.call_args_list

            # First call should include tools
            assert "tools" in calls[0][1]
            assert calls[0][1]["temperature"] == 0.5

            # Second call should include tools
            assert "tools" in calls[1][1]

            # Final call should include tools (not at max iterations yet)
            assert "tools" in calls[2][1]

    @pytest.mark.asyncio
    async def test_tool_schema_generation(self) -> None:
        """Test that tool schemas are properly generated"""
        mock_tool = MockTool(name="mock_tool", description="A mock tool for testing", args_schema=MockArgs)
        llm = LiteLLM(model="gpt-3.5-turbo", tools=[mock_tool])

        assert len(llm.tools_schema) == 1
        schema = llm.tools_schema[0]

        assert schema["type"] == "function"
        assert schema["function"]["name"] == "mock_tool"
        assert schema["function"]["description"] == "A mock tool for testing"
        assert "parameters" in schema["function"]

    def test_tools_dict_creation(self) -> None:
        """Test that tools dictionary is properly created"""
        mock_tool = MockTool(name="mock_tool", description="A mock tool for testing", args_schema=MockArgs)
        error_tool = ErrorTool(name="error_tool", description="A tool that raises errors", args_schema=ErrorArgs)
        llm = LiteLLM(model="gpt-3.5-turbo", tools=[mock_tool, error_tool])

        assert len(llm.tools_dict) == 2
        assert "mock_tool" in llm.tools_dict
        assert "error_tool" in llm.tools_dict
        assert llm.tools_dict["mock_tool"] == mock_tool
        assert llm.tools_dict["error_tool"] == error_tool

    @pytest.mark.asyncio
    async def test_multiple_tool_calls_in_single_response(self) -> None:
        """Test handling multiple tool calls in a single LLM response"""
        mock_tool = MockTool(name="mock_tool", description="A mock tool for testing", args_schema=MockArgs)
        llm = LiteLLM(model="gpt-3.5-turbo", tools=[mock_tool])
        messages: list[Message] = [UserMessage(content="Use the tool twice")]

        # Multiple tool calls in one response
        tool_calls = [
            ToolCall(id="call_1", function=Function(name="mock_tool", arguments='{"value": 1}'), type="function"),
            ToolCall(id="call_2", function=Function(name="mock_tool", arguments='{"value": 2}'), type="function"),
        ]
        first_response = create_mock_response("Using tool twice", tool_calls)
        final_response = create_mock_response("Both tools completed")

        with patch("litellm.acompletion", side_effect=[first_response, final_response]):
            response, updated_messages, tools_executed = await llm._run_once(History(), messages, use_tools=True)

            assert tools_executed is True
            # Should have original message + assistant message + 2 tool messages
            assert len(updated_messages) == 4

            # Check that both tool calls were executed
            tool_messages = [msg for msg in updated_messages if isinstance(msg, ToolMessage)]
            assert len(tool_messages) == 2
            assert tool_messages[0].tool_call_id == "call_1"
            assert tool_messages[1].tool_call_id == "call_2"


class TestLiteLLMRetry:
    """Test retry functionality for various error types"""

    @pytest.mark.asyncio
    async def test_rate_limit_error_retry(self) -> None:
        """Test that RateLimitError is retried and eventually succeeds"""
        llm = LiteLLM(model="gpt-3.5-turbo", max_retries=2)
        messages: list[Message] = [UserMessage(content="Hello")]

        # Import the specific exception we need
        from litellm.exceptions import RateLimitError

        # Mock response that succeeds after retry
        mock_response = create_mock_response("Success after retry")

        rate_limit_error = RateLimitError("Rate limit exceeded", "openai", "gpt-3.5-turbo")

        with patch("litellm.acompletion", side_effect=[rate_limit_error, mock_response]) as mock_completion:
            result = await llm.run(History(), messages)

            # Should succeed after retry
            assert result == mock_response
            assert mock_completion.call_count == 2

    @pytest.mark.asyncio
    async def test_internal_server_error_retry(self) -> None:
        """Test that InternalServerError is retried and eventually succeeds"""
        llm = LiteLLM(model="gpt-3.5-turbo", max_retries=2)
        messages: list[Message] = [UserMessage(content="Hello")]

        # Import the specific exception we need
        from litellm.exceptions import InternalServerError

        # Mock response that succeeds after retry
        mock_response = create_mock_response("Success after retry")
        internal_error = InternalServerError("Internal server error", "openai", "gpt-3.5-turbo")

        with patch("litellm.acompletion", side_effect=[internal_error, mock_response]) as mock_completion:
            result = await llm.run(History(), messages)

            # Should succeed after retry
            assert result == mock_response
            assert mock_completion.call_count == 2

    @pytest.mark.asyncio
    async def test_connection_error_retry(self) -> None:
        """Test that connection errors (aiohttp/httpx) are retried and eventually succeed"""
        llm = LiteLLM(model="gpt-3.5-turbo", max_retries=2)
        messages: list[Message] = [UserMessage(content="Hello")]

        # Import connection error types
        import httpx

        # Mock response that succeeds after retry
        mock_response = create_mock_response("Success after retry")
        connection_error = httpx.ConnectError("Connection failed")

        with patch("litellm.acompletion", side_effect=[connection_error, mock_response]) as mock_completion:
            result = await llm.run(History(), messages)

            # Should succeed after retry
            assert result == mock_response
            assert mock_completion.call_count == 2

    @pytest.mark.asyncio
    async def test_malformed_model_response_error_retry(self) -> None:
        """Test that MalformedModelResponseError is retried and eventually succeeds"""
        llm = LiteLLM(model="gpt-3.5-turbo", max_retries=2)
        messages: list[Message] = [UserMessage(content="Hello")]

        # Import the specific exception we need
        from fraim.core.llms.litellm import MalformedModelResponseError

        # Mock response that succeeds after retry
        mock_response = create_mock_response("Success after retry")
        malformed_error = MalformedModelResponseError("Response missing 'choices' attribute")

        with patch("litellm.acompletion", side_effect=[malformed_error, mock_response]) as mock_completion:
            result = await llm.run(History(), messages)

            # Should succeed after retry
            assert result == mock_response
            assert mock_completion.call_count == 2
