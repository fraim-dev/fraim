# SPDX-License-Identifier: MIT
# Copyright (c) 2025 Resourcely Inc.

"""A wrapper around litellm"""

import logging
from collections.abc import Iterable
from typing import Any, Iterable, Protocol, Self, cast

import litellm
from litellm.files.main import ModelResponse
from litellm.types.utils import ChatCompletionMessageToolCall

from fraim.core.llms.base import BaseLLM
from fraim.core.messages import AssistantMessage, Function, Message, ToolCall
from fraim.core.tools import BaseTool, execute_tool_calls
from fraim.core.utils.retry.tenacity import with_retry


def _configure_litellm_logging() -> None:
    """Configure LiteLLM logging to be less verbose."""
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


# Configure LiteLLM logging on module import
_configure_litellm_logging()


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

    async def _run_once(self, messages: list[Message], use_tools: bool) -> tuple[ModelResponse, list[Message], bool]:
        """Execute one completion call and return response + updated messages + tools_executed flag.

        Returns:
            Tuple of (response, updated_messages, tools_executed)
        """
        completion_params = self._prepare_completion_params(messages=messages, use_tools=use_tools)

        logging.getLogger().debug(f"LLM request: {completion_params}")

        acompletion = with_retry(
            litellm.acompletion, max_retries=self.max_retries, base_delay=self.base_delay, max_delay=self.max_delay
        )
        response = await acompletion(**completion_params)

        # Type assertion - we're not using streaming so this should be ModelResponse
        response = cast(ModelResponse, response)

        message = response.choices[0].message  # type: ignore
        message_content = message.content or ""

        logging.getLogger().debug(f"LLM response: {message_content}")

        tool_calls = _convert_tool_calls(message.tool_calls)

        if len(tool_calls) == 0:
            return response, messages, False

        # Execute tools using pre-built tools dictionary
        tool_messages = await execute_tool_calls(tool_calls, self.tools_dict)

        # Create assistant message with tool calls
        assistant_message = AssistantMessage(content=message_content, tool_calls=tool_calls)

        # Add assistant message and tool responses to conversation
        updated_messages = messages + [assistant_message] + tool_messages

        return response, updated_messages, True

    async def run(self, messages: list[Message]) -> ModelResponse:
        """Run completion with optional tool support, handling multiple iterations."""
        current_messages = messages.copy()

        for iteration in range(self.max_tool_iterations + 1):
            # Don't provide tools on the final iteration to force a final response
            use_tools = iteration < self.max_tool_iterations

            response, current_messages, tools_executed = await self._run_once(current_messages, use_tools)

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
