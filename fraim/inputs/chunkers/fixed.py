# SPDX-License-Identifier: MIT
# Copyright (c) 2025 Resourcely Inc.
import re
from bisect import bisect_right
from functools import cached_property
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
        yield from self.chunks()

    # Chunks is kept separate from iterator so we have a type annotation that returns the concrete class
    def chunks(self) -> Iterator[Contextual[str]]:
        with self.input as input:
            for file in input:
                yield from self.split_file(self.splitter, file)

    def split_file(self, splitter: TextSplitter, chunk: CodeChunk) -> Iterator[CodeChunk]:
        line_starts = [0] + [match.start() + 1 for match in re.finditer("\n", chunk.content)]
        search_from = 0
        for doc in splitter.create_documents([chunk.content]):
            raw_content = doc.page_content or ""
            stripped_content = raw_content.strip("\n")
            if not stripped_content:
                continue

            start_index = chunk.content.find(stripped_content, search_from)
            if start_index == -1:
                start_index = chunk.content.find(stripped_content)
            if start_index == -1:
                start_index = search_from
            search_from = max(start_index + 1, search_from)

            start_offset = max(start_index, 0)
            end_offset = start_offset + len(stripped_content) - 1
            start_line = bisect_right(line_starts, start_offset)
            end_line = bisect_right(line_starts, end_offset)

            yield CodeChunk(
                content=stripped_content,
                file_path=str(chunk.file_path),
                line_number_start_inclusive=start_line,
                line_number_end_inclusive=end_line,
            )

    @cached_property
    def splitter(self) -> RecursiveCharacterTextSplitter:
        # add_start_index=True currently returns -1 for overlap chunks; disable and recover offsets manually.
        return RecursiveCharacterTextSplitter.from_tiktoken_encoder(
            separators=["\n"],
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap,
            strip_whitespace=False, # Strip whitespace manually to preserve offsets
            add_start_index=False,
        )
