# SPDX-License-Identifier: MIT
# Copyright (c) 2025 Resourcely Inc.
from pathlib import Path
from typing import List, Iterator

from multipart import file_path

from fraim.core.contextuals.code import CodeChunk
from fraim.inputs.chunkers.base import Chunker
from fraim.inputs.files import Files


class FileChunker(Chunker):
    def __init__(self, files: Files, project_path: str, chunk_size: int, **kwargs) -> None:
        super().__init__(**kwargs)
        self.files = files
        self.project_path = project_path
        self.chunk_size = chunk_size

    def __iter__(self) -> Iterator[CodeChunk]:
        """Yield each file as a single chunk."""

        with self.files as files:
            for file in files:

                path = Path(file.path)
                if path.is_absolute():
                    path = path.relative_to(self.project_path)

                yield CodeChunk(
                    content=file.body,
                    file_path=str(path),
                    line_number_start_inclusive=1,
                    line_number_end_inclusive=len(file.body.splitlines()),
                )
