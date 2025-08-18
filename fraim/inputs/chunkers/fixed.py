# SPDX-License-Identifier: MIT
# Copyright (c) 2025 Resourcely Inc.
import re

from bisect import bisect_right
from typing import Iterator

from langchain_text_splitters import CharacterTextSplitter

from fraim.core.contextuals.code import CodeChunk
from fraim.inputs.chunkers.base import Chunker
from fraim.inputs.files import File, Files


class FixedChunker(Chunker):
    def __init__(self, files: Files, chunk_size: int, chunk_overlap: int | None = None, **kwargs) -> None:
        if chunk_overlap is None:
            # Default to 10% overlap if not specified
            chunk_overlap = int(chunk_size / 10)

        super().__init__(**kwargs)
        self.files = files
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.splitter = CharacterTextSplitter(
            separator="\n",
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            strip_whitespace=False,
            add_start_index=True,
        )

    def __iter__(self) -> Iterator[CodeChunk]:
        with self.files as files:
            for file in files:
                yield from self.split_file(file)

    def split_file(self, file: File) -> Iterator[CodeChunk]:
        line_starts = [0] + [match.start() + 1 for match in re.finditer('\n', file.body)]
        for doc in self.splitter.create_documents([file.body]):
            start_index = doc.metadata["start_index"]
            end_index = start_index + len(doc.page_content)

            start_line = bisect_right(line_starts, start_index)
            end_line = bisect_right(line_starts, end_index)

            yield CodeChunk(
                content=doc.page_content,
                file_path=str(file.path),
                line_number_start_inclusive=start_line,  # Line numbers are already prepended
                line_number_end_inclusive=end_line,
            )
