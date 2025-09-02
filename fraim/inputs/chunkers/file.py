# SPDX-License-Identifier: MIT
# Copyright (c) 2025 Resourcely Inc.
from typing import Iterator, Any

from fraim.core.contextuals.code import CodeChunk
from fraim.inputs.chunkers.base import Chunker
from fraim.inputs.input import Input


class FileChunker(Chunker):
    def __init__(self, input: Input, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.input = input

    def __iter__(self) -> Iterator[CodeChunk]:
        """Yield each file as a single chunk."""

        with self.input as input:
            for file in input:
                yield file