# SPDX-License-Identifier: MIT
# Copyright (c) 2025 Resourcely Inc.

from pathlib import Path
from types import TracebackType
from typing import Iterator, Optional, Type

from typing_extensions import Self

from fraim.core.contextuals import CodeChunk
from fraim.inputs.file import File
from fraim.inputs.input import Input

class StandardInput(Input):
    def __init__(self, body: str):
        self.body = body

    def root_path(self) -> str:
        return "stdin"

    def __iter__(self) -> Iterator[CodeChunk]:
        yield File(Path("stdin"), self.body)

    def __enter__(self) -> Self:
        return self

    def __exit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_value: Optional[BaseException],
        traceback: Optional[TracebackType],
    ) -> None:
        pass
