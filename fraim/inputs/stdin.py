# SPDX-License-Identifier: MIT
# Copyright (c) 2025 Resourcely Inc.

from collections.abc import Iterator
from types import TracebackType
from typing import Self

from fraim.core.contextuals import CodeChunk
from fraim.inputs.chunks import chunk_input
from fraim.inputs.file import BufferedFile
from fraim.inputs.input import Input


class StandardInput(Input):
    def __init__(self, body: str):
        self.body = body

    def root_path(self) -> str:
        return "stdin"

    def __iter__(self) -> Iterator[CodeChunk]:
        for chunk in chunk_input(BufferedFile("stdin", self.body), chunk_size=128):
            yield chunk

    def __enter__(self) -> Self:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        pass
