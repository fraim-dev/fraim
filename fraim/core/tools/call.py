# SPDX-License-Identifier: MIT
# Copyright (c) 2025 Resourcely Inc.

from typing import Literal, Protocol


class Function(Protocol):
    """Function representation"""

    name: str
    arguments: str  # JSON string


class ToolCall(Protocol):
    """Tool call representation"""

    id: str
    function: Function
    type: Literal["function"]
