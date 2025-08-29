# SPDX-License-Identifier: MIT
# Copyright (c) 2025 Resourcely Inc.
from typing import Iterator

from fraim.core.contextuals.code import CodeChunk
from fraim.inputs.chunkers.base import Chunker
from fraim.inputs.file import Files


class FileChunker(Chunker):
    def __init__(self, files: Files, **kwargs) -> None:
        super().__init__(**kwargs)
        self.files = files

    def __iter__(self) -> Iterator[CodeChunk]:
        """Yield each file as a single chunk."""

        for file in self.files:
            yield CodeChunk(
                content=file.body,
                file_path=str(file.path),
                line_number_start_inclusive=1,
                line_number_end_inclusive=len(file.body.splitlines()),
            )
