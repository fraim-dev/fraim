# SPDX-License-Identifier: MIT
# Copyright (c) 2025 Resourcely Inc.

from collections.abc import Iterator
from typing import ContextManager, Protocol, runtime_checkable

from fraim.core.contextuals import CodeChunk


@runtime_checkable
class Input(Protocol, ContextManager):
    def __iter__(self) -> Iterator[CodeChunk]: ...

    # TODO: Allow inputs to describe themselves
    # def describe(self) -> str: ...

    # The relative file path of the input, related to the project path.
    def root_path(self) -> str: ...
