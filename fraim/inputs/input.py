# SPDX-License-Identifier: MIT
# Copyright (c) 2025 Resourcely Inc.

from typing import ContextManager, Iterator, Protocol, runtime_checkable

from fraim.core.contextuals import CodeChunk
from fraim.inputs.file import File


@runtime_checkable
class Input(Protocol, ContextManager):
    def __iter__(self) -> Iterator[File]: ...

    # TODO: Allow inputs to describe themselves
    # def describe(self) -> str: ...

    # The relative file path of the input, related to the project path.
    def root_path(self) -> str: ...
