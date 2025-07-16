# SPDX-License-Identifier: MIT
# Copyright (c) 2025 Resourcely Inc.

"""A wrapper around litellm"""

import logging
from typing import Any, Dict, List, Optional, Protocol, Self, Sequence, Tuple

import litellm
from litellm import ModelResponse
from litellm.types.utils import ChatCompletionMessageToolCall

from fraim.core.llms.base import BaseLLM
from fraim.core.messages import AssistantMessage, Function, Message, ToolCall
from fraim.core.tools import BaseTool, execute_tool_calls


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

    @classmethod
    def from_config(cls, config: Config, max_tool_iterations: int = 10, tools: Optional[List[BaseTool]] = None) -> Self:
        model_params = {"temperature": config.temperature}
        return cls(
            model=config.model,
            additional_model_params=model_params,
            max_tool_iterations=max_tool_iterations,
            tools=tools,
        )

    def __init__(
        self,
        model: str,
        additional_model_params: Optional[Dict[str, Any]] = None,
        max_tool_iterations: int = 10,
        tools: Optional[Sequence[BaseTool]] = None,
    ):
        self.model = model
        self.additional_model_params = additional_model_params or {}

        self.max_tool_iterations = max_tool_iterations
        if self.max_tool_iterations < 0:
            raise ValueError("max_tool_iterations must be a non-negative integer")

        self.tools = tools or []
        self.tools_dict = {tool.name: tool for tool in self.tools}
        self.tools_schema = [tool.to_openai_schema() for tool in self.tools]

    def with_tools(self, tools: Sequence[BaseTool], max_tool_iterations: Optional[int] = None) -> Self:
        if max_tool_iterations is None:
            max_tool_iterations = self.max_tool_iterations

        return self.__class__(
            model=self.model,
            additional_model_params=self.additional_model_params,
            max_tool_iterations=max_tool_iterations,
            tools=tools,
        )

    async def _run_once(self, messages: List[Message], use_tools: bool) -> Tuple[ModelResponse, List[Message], bool]:
        """Execute one completion call and return response + updated messages + tools_executed flag.

        Returns:
            Tuple of (response, updated_messages, tools_executed)
        """
        completion_params = self._prepare_completion_params(messages=messages, use_tools=use_tools)

        logging.getLogger().debug(f"LLM request: {completion_params}")

        response = await litellm.acompletion(**completion_params)

        message = response.choices[0].message
        message_content = message.content or ""

        logging.getLogger().debug(f"LLM response: {message_content}")

        tool_calls = _convert_tool_calls(message.tool_calls)

        if len(tool_calls) == 0:
            return response, messages, False

        # Execute tools using pre-built tools dictionary
        tool_messages = await execute_tool_calls(tool_calls, self.tools_dict)

        # Create assistant message with tool calls
        assistant_message = AssistantMessage(content=message_content, tool_calls=tool_calls)

        updated_messages = messages + [assistant_message] + tool_messages

        return response, updated_messages, True

    async def run(self, messages: List[Message]) -> ModelResponse:
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

    def _prepare_completion_params(self, messages: List[Message], use_tools: bool) -> Dict[str, Any]:
        """Prepare parameters for litellm.acompletion call."""

        # Convert Pydantic Message objects to dictionaries for LiteLLM compatibility
        messages_dict = [message.model_dump() for message in messages]

        params = {"model": self.model, "messages": messages_dict, **self.additional_model_params}

        if use_tools:
            params["tools"] = self.tools_schema

        return params


def _convert_tool_calls(raw_tool_calls: Optional[List[ChatCompletionMessageToolCall]]) -> List[ToolCall]:
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
