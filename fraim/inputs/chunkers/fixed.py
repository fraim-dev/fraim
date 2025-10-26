# SPDX-License-Identifier: MIT
# Copyright (c) 2025 Resourcely Inc.
import re
from bisect import bisect_right
from typing import Any, Iterator

from langchain_text_splitters import RecursiveCharacterTextSplitter, TextSplitter

from fraim.core.contextuals import Contextual
from fraim.core.contextuals.code import CodeChunk
from fraim.inputs.chunkers.base import Chunker
from fraim.inputs.input import Input


class FixedTokenChunker(Chunker):
    def __init__(self, input: Input, chunk_size: int | None, chunk_overlap: int | None = None, **kwargs: Any) -> None:
        self.chunk_size = chunk_size if chunk_size else 3_000
        self.chunk_overlap = chunk_overlap if chunk_overlap else int(self.chunk_size / 10)  # Default to 10% overlap
        self.input = input

    def __iter__(self) -> Iterator[Contextual[str]]:
        for file in self.chunks():
            yield from self.split_file(self.splitter, file)

    # Chunks is kept separate from iterator so we have a type annotation that returns the concrete class
    def chunks(self) -> Iterator[CodeChunk]:
        with self.input as input:
            for file in input:
                yield from self.split_file(self.splitter, file)

    def split_file(self, splitter: TextSplitter, chunk: CodeChunk) -> Iterator[CodeChunk]:
        line_starts = [0] + [match.start() + 1 for match in re.finditer("\n", chunk.content)]
        for doc in splitter.create_documents([chunk.content]):
            start_index = doc.metadata["start_index"]
            end_index = start_index + len(doc.page_content)

            start_line = bisect_right(line_starts, start_index)
            end_line = bisect_right(line_starts, end_index)

            yield CodeChunk(
                content=doc.page_content,
                file_path=str(chunk.file_path),
                line_number_start_inclusive=start_line,  # Line numbers are already prepended
                line_number_end_inclusive=end_line,
            )

    @property
    def splitter(self) -> RecursiveCharacterTextSplitter:
        return RecursiveCharacterTextSplitter.from_tiktoken_encoder(
            separators=["\n"],
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap,
            strip_whitespace=False,
            add_start_index=True,
        )
