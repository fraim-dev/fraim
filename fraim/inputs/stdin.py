# SPDX-License-Identifier: MIT
# Copyright (c) 2025 Resourcely Inc.

from types import TracebackType
from typing import Iterator, Optional, Type

from typing_extensions import Self

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
        for chunk in chunk_input(BufferedFile("stdin", self.body), chunk_size=128):
            yield chunk

    def __enter__(self) -> Self:
        return self

    def __exit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_value: Optional[BaseException],
        traceback: Optional[TracebackType],
    ) -> None:
        pass
