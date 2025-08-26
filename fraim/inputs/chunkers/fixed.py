# SPDX-License-Identifier: MIT
# Copyright (c) 2025 Resourcely Inc.
import re
from abc import abstractmethod
from bisect import bisect_right
from typing import Iterator

from langchain_text_splitters import CharacterTextSplitter, RecursiveCharacterTextSplitter, TextSplitter

from fraim.core.contextuals.code import CodeChunk
from fraim.inputs.chunkers.base import Chunker
from fraim.inputs.file import Files, File


class FixedBaseChunker(Chunker):
    def __init__(self, files: Files, chunk_size: int, chunk_overlap: int | None = None, **kwargs) -> None:
        if chunk_overlap is None:
            # Default to 10% overlap if not specified
            chunk_overlap = int(chunk_size / 10)

        super().__init__(**kwargs)
        self.files = files
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def __iter__(self) -> Iterator[CodeChunk]:
        with self.files as files:
            for file in files:
                yield from self.split_file(self.splitter, file)

    def split_file(self, splitter: TextSplitter, file: File) -> Iterator[CodeChunk]:
        line_starts = [0] + [match.start() + 1 for match in re.finditer("\n", file.body)]
        for doc in splitter.create_documents([file.body]):
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

    @property
    @abstractmethod
    def splitter(self) -> TextSplitter:
        pass


class FixedCharChunker(FixedBaseChunker):
    @property
    def splitter(self) -> CharacterTextSplitter:
        return CharacterTextSplitter(
            separator="\n",
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap,
            strip_whitespace=False,
            add_start_index=True,
        )


class FixedTokenChunker(FixedBaseChunker):
    @property
    def splitter(self) -> RecursiveCharacterTextSplitter:
        return RecursiveCharacterTextSplitter.from_tiktoken_encoder(
            separators=["\n"],
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap,
            strip_whitespace=False,
            add_start_index=True,
        )
