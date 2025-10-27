# SPDX-License-Identifier: MIT
# Copyright (c) 2025 Resourcely Inc.
import re
from typing import Iterator

from langchain_text_splitters import Language, RecursiveCharacterTextSplitter

from fraim.core.contextuals import Contextual
from fraim.core.contextuals.code import CodeChunk
from fraim.inputs.chunkers.fixed import FixedTokenChunker


class SyntacticChunker(FixedTokenChunker):
    """
    Uses the language aware langchain text splitter to split code files.

    It does not parse the code syntax, but rather uses the language-specific rules to split the text.
    """

    def __iter__(self) -> Iterator[Contextual[str]]:
        yield from self.chunks()

    # Chunks is kept separate from iterator so we have a type annotation that returns the concrete class
    def chunks(self) -> Iterator[CodeChunk]:
        with self.input as files:
            for file in files:
                if file.language is None:
                    yield from self.split_file(self.splitter, file)
                else:
                    splitter = RecursiveCharacterTextSplitter.from_language(
                        Language(file.language), add_start_index=True
                    )
                    yield from self.split_file(splitter, file)
