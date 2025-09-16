# SPDX-License-Identifier: MIT
# Copyright (c) 2025 Resourcely Inc.

"""Parser that retries with LLM help when parsing fails"""

from textwrap import dedent
from typing import Generic, TypeVar

from litellm.types.utils import StreamingChoices

from fraim.core.messages import AssistantMessage, Message, UserMessage
from fraim.core.parsers.base import BaseOutputParser, OutputParserError, ParseContext
from fraim.core.prompts import PromptTemplate

T = TypeVar("T")


class RetryOnErrorOutputParser(BaseOutputParser[T], Generic[T]):
    """
    A parser wrapper that retries parsing by asking the LLM to fix its output when parsing fails.

    When the wrapped parser fails to parse the LLM output, this parser constructs a new prompt
    containing the original conversation, the error message, and a request to fix the output.
    It then calls the LLM again and attempts to parse the corrected response.

    Args:
        parser: The underlying output parser to use
        max_retries: Maximum number of retry attempts (default: 1)
    """

    DEFAULT_RETRY_PROMPT_TEMPLATE = PromptTemplate.from_string(
        dedent("""
        There was an error parsing your previous response:

        {{ error_explanation }}

        Please fix your response to address this error. {{ output_prompt_instructions }}

        Make sure your response follows the exact format requirements.
        """).strip()
    )

    def __init__(
        self,
        parser: BaseOutputParser[T],
        max_retries: int = 3,
        retry_prompt_template: PromptTemplate = DEFAULT_RETRY_PROMPT_TEMPLATE,
    ):
        self.parser = parser
        self.max_retries = max_retries
        self.retry_prompt_template = retry_prompt_template

    def output_prompt_instructions(self) -> str:
        """Delegate to the wrapped parser"""
        return self.parser.output_prompt_instructions()

    async def parse(self, text: str, context: ParseContext | None = None) -> T:
        """
        Parse the text, retrying with LLM help if parsing fails.

        Args:
            text: The text to parse
            context: ParseContext containing LLM and conversation (required for retry functionality)

        Returns:
            The parsed result

        Raises:
            OutputParserError: If parsing fails after all retry attempts
        """
        retries = 0
        while retries <= self.max_retries:
            try:
                return await self.parser.parse(text, context)
            except OutputParserError as e:
                if context is None:
                    raise OutputParserError(f"context is required for retry functionality: {e}") from e
                if retries == self.max_retries:
                    raise e
                text = await self._retry_on_error(text, e, context)
                retries += 1

        raise Exception("unreachable code")

    async def _retry_on_error(self, original_text: str, error: OutputParserError, context: ParseContext) -> str:
        """
        Retry the initial prompt by asking the LLM to fix its output based on the error.

        Args:
            original_text: The original text that failed to parse
            error: The parsing error that occurred
            context: ParseContext containing LLM and conversation

        Returns:
            The raw result of the retry attempt
        """
        # Construct retry prompt
        retry_messages = self._build_retry_messages(context.messages, original_text, error)
        response = await context.llm.with_tools([]).run(context.history, retry_messages)

        # if we get a StreamingChoices or don't get a response just return the original text
        # and the LLM can try again
        if isinstance(response.choices[0], StreamingChoices) or not response.choices[0].message.content:
            return original_text

        # Return the retry prompt
        return response.choices[0].message.content

    def _build_retry_messages(
        self,
        original_messages: list[Message],
        failed_output: str,
        error: OutputParserError,
    ) -> list[Message]:
        """
        Build the message list for the retry attempt.

        Args:
            original_messages: The original conversation messages
            failed_output: The output that failed to parse
            error: The parsing error

        Returns:
            List of messages for the retry prompt
        """
        # Start with the original conversation
        retry_messages = original_messages.copy()

        # Add the failed assistant response
        retry_messages.append(AssistantMessage(content=failed_output))

        # Construct the error explanation
        error_explanation = str(error)
        if error.explanation:
            error_explanation += f"\n\nAdditional details: {error.explanation}"

        # Add user message asking for correction
        retry_template_inputs = {
            "error_explanation": error_explanation,
            "output_prompt_instructions": self.parser.output_prompt_instructions(),
        }
        retry_prompt, _ = self.retry_prompt_template.render(retry_template_inputs)

        retry_messages.append(UserMessage(content=retry_prompt))

        return retry_messages
