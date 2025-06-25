# SPDX-License-Identifier: MIT
# Copyright (c) 2025 Resourcely Inc.

from typing import Generic, Protocol, TypeVar

T = TypeVar("T")


class Contextual(Protocol, Generic[T]):
    """A piece of content with a contextual description.

    When Contextual content is added to a prompt, the contextual description
    can be included to help the LLM better understand the content.
    """

    description: str
    content: T

    def __str__(self) -> str: ...
