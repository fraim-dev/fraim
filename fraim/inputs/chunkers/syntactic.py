# SPDX-License-Identifier: MIT
# Copyright (c) 2025 Resourcely Inc.
import re
from bisect import bisect_right
from typing import Iterator

from langchain_text_splitters import Language, RecursiveCharacterTextSplitter

from fraim.core.contextuals.code import CodeChunk
from fraim.inputs.chunkers import FixedChunker


class SyntacticChunker(FixedChunker):
    """
    Uses the language aware langchain text splitter to split code files.

    It does not parse the code syntax, but rather uses the language-specific rules to split the text.
    """

    def __iter__(self) -> Iterator[CodeChunk]:
        with self.files as files:
            for file in files:
                if file.language is None:
                    self.logger.warning(f"File {file.path} has no detected language, falling back to FixedChunker")
                    yield from super().split_file(file)
                else:
                    yield from self.split_file(file)

    def split_file(self, file):
        line_starts = [0] + [match.start() + 1 for match in re.finditer("\n", file.body)]
        splitter = RecursiveCharacterTextSplitter.from_language(Language(file.language))

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
