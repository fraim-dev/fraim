# SPDX-License-Identifier: MIT
# Copyright (c) 2025 Resourcely Inc.

"""A message for an LLM"""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class Function(BaseModel):
    """Parameters for a function"""

    name: str
    arguments: str = Field(description="JSON string of arguments")

    model_config = ConfigDict(extra="forbid")


class ToolCall(BaseModel):
    """Parameters for a tool call"""

    id: str
    function: Function
    type: Literal["function"] = "function"

    model_config = ConfigDict(extra="forbid")


class Message(BaseModel):
    """A message for an LLM"""

    role: Literal["assistant", "system", "tool", "user"]
    content: str

    model_config = ConfigDict(extra="forbid")


class SystemMessage(Message):
    """A system message for an LLM"""

    role: Literal["system"] = "system"


class UserMessage(Message):
    """A user message for an LLM"""

    role: Literal["user"] = "user"


class AssistantMessage(Message):
    """An assistant message for an LLM"""

    role: Literal["assistant"] = "assistant"
    tool_calls: list[ToolCall] | None = None


class ToolMessage(Message):
    """A tool message for an LLM"""

    role: Literal["tool"] = "tool"
    tool_call_id: str
