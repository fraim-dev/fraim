# SPDX-License-Identifier: MIT
# Copyright (c) 2025 Resourcely Inc.

"""A wrapper around litellm"""

import logging
from collections.abc import Iterable
from typing import Any, Protocol, Self, cast

import litellm
from litellm import CustomStreamWrapper, ModelResponse
from litellm.types.utils import ChatCompletionMessageToolCall

from fraim.core.history import EventRecord, History
from fraim.core.llms.base import BaseLLM
from fraim.core.messages import AssistantMessage, Function, Message, ToolCall
from fraim.core.tools import BaseTool, execute_tool_calls
from fraim.core.utils.retry.http import should_retry_request as should_retry_http_request
from fraim.core.utils.retry.tenacity import with_retry


# Configure LiteLLM on module import
def _configure_litellm() -> None:
    # Allow LiteLLM to modify completion paramters to paper over
    # differences across the various providers. For example,
    # OpenAI allows a null "tools" parameter, while Anthropic requires
    # an empty list instead.
    litellm.modify_params = True

    # Silence LiteLLM loggers
    litellm_loggers = [
        "httpx",
        "litellm",
        "LiteLLM",
        "LiteLLM Proxy",
        "LiteLLM Router",
        "litellm.proxy",
        "litellm.completion",
        "litellm.utils",
        "litellm.llms",
        "litellm.router",
        "litellm.cost_calculator",
        "litellm.utils.cost_calculator",
        "litellm.main",
    ]

    for logger_name in litellm_loggers:
        logger = logging.getLogger(logger_name)
        logger.setLevel(logging.ERROR)


_configure_litellm()


class Config(Protocol):
    """Subset of configuration needed to construct a LiteLLM instance"""

    model: str
    temperature: float


class LiteLLM(BaseLLM):
    """A wrapper around LiteLLM"""

    def __init__(
        self,
        model: str,
        additional_model_params: dict[str, Any] | None = None,
        max_tool_iterations: int = 10,
        tools: Iterable[BaseTool] | None = None,
        max_retries: int = 5,
        base_delay: float = 1.0,
        max_delay: float = 120.0,
    ):
        self.model = model
        self.additional_model_params = additional_model_params or {}

        self.max_tool_iterations = max_tool_iterations
        if self.max_tool_iterations < 0:
            raise ValueError("max_tool_iterations must be a non-negative integer")

        self.tools = list(tools) if tools else []
        self.tools_dict = {tool.name: tool for tool in self.tools}
        self.tools_schema = [tool.to_openai_schema() for tool in self.tools]

        # Retry configuration
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay

    def with_tools(self, tools: Iterable[BaseTool], max_tool_iterations: int | None = None) -> Self:
        if max_tool_iterations is None:
            max_tool_iterations = self.max_tool_iterations

        return self.__class__(
            model=self.model,
            additional_model_params=self.additional_model_params,
            max_tool_iterations=max_tool_iterations,
            tools=tools,
            max_retries=self.max_retries,
            base_delay=self.base_delay,
            max_delay=self.max_delay,
        )

    async def _run_once(
        self, history: History, messages: list[Message], use_tools: bool
    ) -> tuple[ModelResponse, list[Message], bool]:
        """Execute one completion call and return response + updated messages + tools_executed flag.

        Returns:
            Tuple of (response, updated_messages, tools_executed)
        """
        completion_params = self._prepare_completion_params(messages=messages, use_tools=use_tools)

        logging.getLogger().debug(f"LLM request: {completion_params}")

        completion = with_retry(
            acompletion_text,
            max_retries=self.max_retries,
            base_delay=self.base_delay,
            max_delay=self.max_delay,
            retry_predicate=should_retry_acompletion,
        )
        history.append_record(EventRecord(description="Thinking..."))
        response = await completion(**completion_params)
        history.pop_record()

        message = response.choices[0].message  # type: ignore
        message_content = message.content or ""

        logging.getLogger().debug(f"LLM response: {message_content}")

        tool_calls = _convert_tool_calls(message.tool_calls)

        if len(tool_calls) == 0:
            # Final response. Don't log to history.
            return response, messages, False

        if message_content:
            history.append_record(EventRecord(description=message_content))

        # Execute tools using pre-built tools dictionary
        tool_messages = await execute_tool_calls(history, tool_calls, self.tools_dict)

        # Create assistant message with tool calls
        assistant_message = AssistantMessage(content=message_content, tool_calls=tool_calls)

        # Add assistant message and tool responses to conversation
        updated_messages = messages + [assistant_message] + tool_messages

        return response, updated_messages, True

    async def run(self, history: History, messages: list[Message]) -> ModelResponse:
        """Run completion with optional tool support, handling multiple iterations."""
        current_messages = messages.copy()

        for iteration in range(self.max_tool_iterations + 1):
            # Don't provide tools on the final iteration to force a final response
            use_tools = iteration < self.max_tool_iterations

            response, current_messages, tools_executed = await self._run_once(history, current_messages, use_tools)

            if not tools_executed:
                return response

        # This should never be reached due to the loop logic, so raise an exception if we get here
        raise Exception("reached an unreachable code path")

    def _prepare_completion_params(self, messages: list[Message], use_tools: bool) -> dict[str, Any]:
        """Prepare parameters for litellm.acompletion call."""

        # Convert Pydantic Message objects to dictionaries for LiteLLM compatibility
        messages_dict = [message.model_dump() for message in messages]

        params = {"model": self.model, "messages": messages_dict, **self.additional_model_params}

        if use_tools:
            params["tools"] = self.tools_schema

        return params


def _convert_tool_calls(raw_tool_calls: list[ChatCompletionMessageToolCall] | None) -> list[ToolCall]:
    """Convert raw LiteLLM tool calls to our Pydantic ToolCall models.

    Args:
        raw_tool_calls: Raw tool calls from LiteLLM response

    Returns:
        List of Pydantic ToolCall models
    """
    if raw_tool_calls is None:
        return []

    return [
        ToolCall(
            id=tc.id, function=Function(name=tc.function.name or "", arguments=tc.function.arguments), type="function"
        )
        for tc in raw_tool_calls
    ]


class MalformedModelResponseError(ValueError):
    """An error raised when a model response is malformed"""


async def acompletion_text(**kwargs: Any) -> ModelResponse:
    """
    Wrapper around litellm.acompletion that validates the response has the expected shape for a non-streaming
    text completion response.

    This is needed because some model providers (e.g., Google Gemini 2.5) can return
    200 HTTP responses with malformed response objects that lack the expected 'choices' array.

    Args:
        **kwargs: Arguments to pass to litellm.acompletion

    Returns:
        ModelResponse with guaranteed valid text completion structure

    Raises:
        MalformedModelResponseError: If the response lacks expected structure, with detailed error message
    """
    response = await litellm.acompletion(**kwargs)
    validate_text_model_response(response)
    return cast("ModelResponse", response)


def validate_text_model_response(response: ModelResponse | CustomStreamWrapper) -> None:
    """
    Validate that a response is a proper text completion ModelResponse.

    Args:
        response: The response to validate

    Raises:
        MalformedModelResponseError: With detailed message describing the specific validation failure
    """
    # Check if it's a ModelResponse-like object
    if not hasattr(response, "choices"):
        raise MalformedModelResponseError("Response missing 'choices' attribute")

    # Check that choices exists and is not empty
    choices = getattr(response, "choices", None)
    if not choices:
        raise MalformedModelResponseError("Response has empty or missing 'choices' field")
    first_choice = choices[0]

    # Check that the first choice has a message
    message = getattr(first_choice, "message", None)
    if not message:
        raise MalformedModelResponseError("First choice has missing 'message' attribute")

    # For non-streaming responses, check that message has content field
    # (we allow None or empty string content, just need the field to exist)
    if not hasattr(message, "content"):
        raise MalformedModelResponseError("Message has missing 'content' attribute")


def should_retry_acompletion(exception: BaseException) -> bool:
    """
    Retry the acompletion request if a retriable HTTP error occurs or if the response is malformed.

    Args:
        exception: The exception to check

    Returns:
        True if the completion should be retried, False otherwise
    """
    return should_retry_http_request(exception) or isinstance(exception, MalformedModelResponseError)
