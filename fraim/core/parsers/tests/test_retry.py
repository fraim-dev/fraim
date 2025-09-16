# SPDX-License-Identifier: MIT
# Copyright (c) 2025 Resourcely Inc.

"""Tests for RetryOnErrorOutputParser"""

from unittest.mock import AsyncMock, Mock

import pytest
from pydantic import BaseModel

from fraim.core.history import History
from fraim.core.messages import AssistantMessage, Message, SystemMessage, UserMessage
from fraim.core.parsers.base import OutputParserError, ParseContext
from fraim.core.parsers.json import JsonOutputParser
from fraim.core.parsers.pydantic import PydanticOutputParser
from fraim.core.parsers.retry import RetryOnErrorOutputParser


class SimpleModel(BaseModel):
    name: str
    age: int


class TestRetryOnErrorOutputParser:
    """Test cases for RetryOnErrorOutputParser"""

    def test_init(self) -> None:
        """Test parser initialization"""
        base_parser = PydanticOutputParser(SimpleModel)
        retry_parser = RetryOnErrorOutputParser(base_parser, max_retries=2)

        assert retry_parser.parser == base_parser
        assert retry_parser.max_retries == 2

    def test_init_default_max_retries(self) -> None:
        """Test parser initialization with default max_retries"""
        base_parser = PydanticOutputParser(SimpleModel)
        retry_parser = RetryOnErrorOutputParser(base_parser)

        assert retry_parser.max_retries == 3

    def test_output_prompt_instructions_delegates(self) -> None:
        """Test that output_prompt_instructions delegates to wrapped parser"""
        base_parser = PydanticOutputParser(SimpleModel)
        retry_parser = RetryOnErrorOutputParser(base_parser)

        assert retry_parser.output_prompt_instructions() == base_parser.output_prompt_instructions()

    @pytest.mark.asyncio
    async def test_parse_success_no_retry_needed(self) -> None:
        """Test successful parsing without retry"""
        mock_llm = Mock()
        messages = Mock()
        context = ParseContext(llm=mock_llm, history=History(), messages=messages)

        base_parser = PydanticOutputParser(SimpleModel)
        retry_parser = RetryOnErrorOutputParser(base_parser)
        valid_json = '{"name": "John", "age": 30}'

        result = await retry_parser.parse(valid_json, context)

        assert isinstance(result, SimpleModel)
        assert result.name == "John"
        assert result.age == 30

    @pytest.mark.asyncio
    async def test_parse_failure_no_context_reraises_error(self) -> None:
        """Test that parse failure without context re-raises the original error"""
        base_parser = PydanticOutputParser(SimpleModel)
        retry_parser = RetryOnErrorOutputParser(base_parser)
        invalid_json = '{"name": "John"}'  # Missing age field

        with pytest.raises(OutputParserError) as exc_info:
            await retry_parser.parse(invalid_json)

        assert "Could not parse JSON into SimpleModel" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_parse_success_after_retry(self) -> None:
        """Test successful parsing after one retry"""
        # Mock LLM that returns valid JSON on retry
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = '{"name": "John", "age": 30}'

        mock_llm = Mock()
        mock_llm.run = AsyncMock()
        mock_llm.run.return_value = mock_response
        mock_llm.with_tools.return_value = mock_llm

        messages: list[Message] = [UserMessage(content="Generate a person")]
        context = ParseContext(llm=mock_llm, history=History(), messages=messages)

        base_parser = PydanticOutputParser(SimpleModel)
        retry_parser = RetryOnErrorOutputParser(base_parser)
        invalid_json = '{"name": "John"}'  # Missing age field

        result = await retry_parser.parse(invalid_json, context)

        assert isinstance(result, SimpleModel)
        assert result.name == "John"
        assert result.age == 30

        # Verify LLM was called for retry
        mock_llm.run.assert_called_once()

        # Verify the retry prompt structure
        retry_messages = mock_llm.run.call_args[0][1]
        assert len(retry_messages) == 3  # original user message + failed assistant response + retry request
        assert retry_messages[0].content == "Generate a person"
        assert retry_messages[1].content == invalid_json
        assert "error parsing your previous response" in retry_messages[2].content.lower()

    @pytest.mark.asyncio
    async def test_parse_failure_after_max_retries(self) -> None:
        """Test parse failure after reaching max retries"""
        # Mock LLM that returns valid JSON on retry
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = '{"name": "John"}'

        mock_llm = Mock()
        mock_llm.run = AsyncMock()
        mock_llm.run.return_value = mock_response
        mock_llm.with_tools.return_value = mock_llm

        # Create context
        messages: list[Message] = [UserMessage(content="Generate a person")]
        context = ParseContext(llm=mock_llm, history=History(), messages=messages)

        base_parser = PydanticOutputParser(SimpleModel)
        retry_parser = RetryOnErrorOutputParser(base_parser, max_retries=2)
        invalid_json = '{"name": "John"}'  # Missing age field

        with pytest.raises(OutputParserError) as exc_info:
            await retry_parser.parse(invalid_json, context)

        # Verify LLM was called max_retries times
        assert mock_llm.run.call_count == 2

    @pytest.mark.asyncio
    async def test_llm_call_failure_during_retry(self) -> None:
        """Test handling of LLM call failure during retry"""
        mock_llm = Mock()
        mock_llm.run = AsyncMock()
        mock_llm.run.side_effect = Exception("LLM service unavailable")
        mock_llm.with_tools.return_value = mock_llm

        # Create context
        messages: list[Message] = [UserMessage(content="Generate a person")]
        context = ParseContext(llm=mock_llm, history=History(), messages=messages)

        base_parser = PydanticOutputParser(SimpleModel)
        retry_parser = RetryOnErrorOutputParser(base_parser)
        invalid_json = '{"name": "John"}'  # Missing age field

        with pytest.raises(Exception) as exc_info:
            await retry_parser.parse(invalid_json, context)

        assert exc_info.value is not None
        assert "LLM service unavailable" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_build_retry_messages_structure(self) -> None:
        """Test the structure of retry messages"""
        base_parser = PydanticOutputParser(SimpleModel)
        retry_parser = RetryOnErrorOutputParser(base_parser)

        original_messages = [
            SystemMessage(content="You are a helpful assistant"),
            UserMessage(content="Generate a person"),
        ]
        failed_output = '{"name": "John"}'
        error = OutputParserError("Missing field", explanation="age field is required")

        retry_messages = retry_parser._build_retry_messages(original_messages, failed_output, error)

        assert len(retry_messages) == 4
        assert retry_messages[0].content == "You are a helpful assistant"
        assert retry_messages[1].content == "Generate a person"
        assert retry_messages[2].content == failed_output
        assert isinstance(retry_messages[2], AssistantMessage)
        assert "error parsing your previous response" in retry_messages[3].content.lower()
        assert "Missing field" in retry_messages[3].content
        assert "age field is required" in retry_messages[3].content
        assert isinstance(retry_messages[3], UserMessage)

    @pytest.mark.asyncio
    async def test_retry_with_json_parser(self) -> None:
        """Test retry functionality with JsonOutputParser"""
        # Mock LLM that returns valid JSON on retry
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = '{"fixed": true}'

        mock_llm = Mock()
        mock_llm.run = AsyncMock()
        mock_llm.run.return_value = mock_response
        mock_llm.with_tools.return_value = mock_llm

        # Create context
        messages: list[Message] = [UserMessage(content="Generate JSON")]
        context = ParseContext(llm=mock_llm, history=History(), messages=messages)

        base_parser = JsonOutputParser()
        retry_parser = RetryOnErrorOutputParser(base_parser)
        invalid_json = '{"broken": json}'  # Invalid JSON

        result = await retry_parser.parse(invalid_json, context)

        assert result == {"fixed": True}
        mock_llm.run.assert_called_once()

    @pytest.mark.asyncio
    async def test_multiple_retry_attempts(self) -> None:
        """Test multiple retry attempts before success"""
        # Mock LLM that fails first retry but succeeds on second
        responses = [
            # First retry - still invalid
            Mock(choices=[Mock(message=Mock(content='{"still": "broken"'))]),
            # Second retry - valid
            Mock(choices=[Mock(message=Mock(content='{"name": "John", "age": 30}'))]),
        ]

        mock_llm = Mock()
        mock_llm.run = AsyncMock()
        mock_llm.run.side_effect = responses
        mock_llm.with_tools.return_value = mock_llm

        # Create context
        messages: list[Message] = [UserMessage(content="Generate a person")]
        context = ParseContext(llm=mock_llm, history=History(), messages=messages)

        base_parser = PydanticOutputParser(SimpleModel)
        retry_parser = RetryOnErrorOutputParser(base_parser, max_retries=2)
        invalid_json = '{"name": "John"}'  # Missing age field

        result = await retry_parser.parse(invalid_json, context)

        assert isinstance(result, SimpleModel)
        assert result.name == "John"
        assert result.age == 30

        # Verify LLM was called twice
        assert mock_llm.run.call_count == 2

    def test_sync_parse_with_context(self) -> None:
        """Test synchronous parse with context"""
        base_parser = PydanticOutputParser(SimpleModel)
        retry_parser = RetryOnErrorOutputParser(base_parser)
        valid_json = '{"name": "John", "age": 30}'

        result = retry_parser.parse_sync(valid_json)

        assert isinstance(result, SimpleModel)
        assert result.name == "John"
        assert result.age == 30
