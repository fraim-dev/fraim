# SPDX-License-Identifier: MIT
# Copyright (c) 2025 Resourcely Inc.

from typing import ContextManager, Iterator, Protocol, runtime_checkable

from fraim.core.contextuals import CodeChunk

@runtime_checkable
class Input(Protocol, ContextManager):

    def __iter__(self) -> Iterator[CodeChunk]: ...

    # The absolute file path that these files are relative to.
    def root_path(self) -> str: ...
