# SPDX-License-Identifier: MIT
# Copyright (c) 2025 Resourcely Inc.

"""A step that calls an LLM"""

import dataclasses
from typing import TYPE_CHECKING, Any, Dict, Generic, List, Optional, TypeVar, Union

if TYPE_CHECKING:
    from _typeshed import DataclassInstance

from litellm.types.utils import StreamingChoices

from fraim.core.llms.base import BaseLLM
from fraim.core.messages import Message, SystemMessage, UserMessage
from fraim.core.parsers.base import BaseOutputParser, ParseContext
from fraim.core.parsers.retry import RetryOnErrorOutputParser
from fraim.core.prompts import PromptTemplate
from fraim.core.steps.base import BaseStep
from fraim.core.tools import BaseTool

OUTPUT_FORMAT_KEY = "output_format"

TDynamicInput = TypeVar("TDynamicInput", bound=Union[Dict[str, Any], "DataclassInstance"])
TOutput = TypeVar("TOutput")

# TODO: add rate limiting


class LLMStep(BaseStep[TDynamicInput, TOutput], Generic[TDynamicInput, TOutput]):
    """A step that calls an LLM"""

    def __init__(
        self,
        llm: BaseLLM,
        system_prompt: PromptTemplate,
        user_prompt: PromptTemplate,
        parser: BaseOutputParser[TOutput],
        static_inputs: Optional[Dict[str, Any]] = None,
        tools: Optional[List[BaseTool]] = None,
        max_tool_iterations: Optional[int] = None,
    ):
        """Creates a step that calls an LLM with a system prompt and a user prompt.

        The system prompt is rendered with the static inputs and the output prompt instructions.

        The user prompt is rendered with the static inputs and the dynamic inputs passed to the `run` method.
        If there are any unused dynamic inputs, they are automatically added to the end of the user prompt.

        Typically, the system prompt will be a template that includes a variable for the output format and optionally the static inputs.
        The user prompt will be a template that includes variables some of the dynamic inputs.

        Args:
            llm: The LLM to call
            system_prompt: The system prompt template
            user_prompt: The user prompt template
            parser: The parser to use to parse the output
            static_inputs: Static inputs to use for the system and user prompts
            tools: Optional list of tools to make available to the LLM
            max_tool_iterations: Optional maximum number of tool iterations (if not provided, uses LLM's default)
        """
        if tools is not None:
            self.llm = llm.with_tools(tools, max_tool_iterations)
        else:
            self.llm = llm

        self.system_prompt = system_prompt
        self.user_prompt = user_prompt

        # Automatically wrap parser in RetryOnErrorOutputParser if it's not already one
        # TODO: add a way to disable this automatic wrapping
        self.parser: BaseOutputParser[TOutput]
        if isinstance(parser, RetryOnErrorOutputParser):
            self.parser = parser
        else:
            self.parser = RetryOnErrorOutputParser(parser)

        self.static_inputs = static_inputs or {}

        self._system_message = self._render_system_message()

    def _render_system_message(self) -> SystemMessage:
        """Render the system prompt with the static inputs and the output prompt instructions"""
        inputs = self.static_inputs.copy()

        if OUTPUT_FORMAT_KEY in self.system_prompt.used_variables():
            inputs[OUTPUT_FORMAT_KEY] = self.parser.output_prompt_instructions()
            rendered, _ = self.system_prompt.render(inputs)
            return SystemMessage(content=rendered)
        else:
            # If the system prompt doesn't use the output format key, add it to the end of the prompt
            # automatically.
            rendered, _ = self.system_prompt.render(inputs)
            output_instructions = self.parser.output_prompt_instructions()
            content = f"${rendered}\n<output_format>${output_instructions}</output_format>"
            return SystemMessage(content=content)

    def _render_user_message(self, input: Dict[str, Any]) -> UserMessage:
        """Render the user prompt with the static inputs and the dynamic inputs

        If there are any unused inputs, they are automatically added to the end of the user prompt.
        """
        inputs = self.static_inputs.copy()
        inputs.update(input)

        rendered, unused_keys = self.user_prompt.render(inputs)

        # Automatically add any unused inputs to the user prompt as structured XML
        rendered_unused = ""
        for key in unused_keys:
            value = inputs[key]
            rendered_unused += f"<{key}>{value}</{key}>\n"

        content = f"{rendered}\n{rendered_unused}"
        return UserMessage(content=content)

    async def run(self, input: TDynamicInput, **kwargs: Any) -> TOutput:
        messages = self._prepare_messages(_normalize_input(input))
        response = await self.llm.run(messages)

        choice = response.choices[0]
        if isinstance(choice, StreamingChoices):
            raise ValueError("Streaming responses are not supported")

        # At this point, choice is guaranteed to be of type Choices
        message_content = choice.message.content
        if message_content is None:
            raise ValueError("Message content is None")

        context = ParseContext(llm=self.llm, messages=messages)
        return await self.parser.parse(message_content, context=context)

    def _prepare_messages(self, input: Dict[str, Any]) -> List[Message]:
        user_message = self._render_user_message(input)
        return [self._system_message, user_message]


def _normalize_input(input: TDynamicInput) -> Dict[str, Any]:
    """Normalize the input to a dictionary

    If the input is a dataclass, convert it to a dictionary.
    If the input is a dictionary, return it.
    Otherwise, raise an error.
    """

    if dataclasses.is_dataclass(input):
        return dataclasses.asdict(input)

    if isinstance(input, dict):
        return input

    # Defensive check - should never reach here based on type annotations
    raise ValueError(f"Input type {type(input)} is not supported. Must be a dataclass or dictionary.")
