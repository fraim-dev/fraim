# SPDX-License-Identifier: MIT
# Copyright (c) 2025 Resourcely Inc.

from collections.abc import Iterator
from types import TracebackType
from typing import Self

from fraim.config import Config
from fraim.core.contextuals import CodeChunk
from fraim.inputs.chunks import chunk_input
from fraim.inputs.file import BufferedFile
from fraim.inputs.input import Input


class StandardInput(Input):
    def __init__(self, config: Config, body: str):
        self.config = config
        self.body = body

    def root_path(self) -> str:
        return "stdin"

    def __iter__(self) -> Iterator[CodeChunk]:
        yield CodeChunk(
            file_path="stdin",
            content=self.body,
            line_number_start_inclusive=1,
            line_number_end_inclusive=len(self.body),
        )

    def __enter__(self) -> Self:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        pass
