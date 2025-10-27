# SPDX-License-Identifier: MIT
from pathlib import Path
from typing import cast

import pytest

from fraim.core.contextuals import CodeChunk
from fraim.inputs.chunkers.fixed import FixedTokenChunker
from fraim.inputs.chunkers.tests.lib import InMemory


@pytest.fixture
def sequential_code_chunk() -> CodeChunk:
    content = "\n".join(f"line {i}" for i in range(1, 121))
    return CodeChunk("file.java", content, line_number_start_inclusive=1, line_number_end_inclusive=120)


def test_fixed_token_chunker_preserves_line_numbers(sequential_code_chunk: CodeChunk, tmp_path: Path) -> None:
    input_source = InMemory(sequential_code_chunk, root_path=str(tmp_path))
    chunker = FixedTokenChunker(input_source, chunk_size=50, chunk_overlap=10)
    chunks = [cast(CodeChunk, chunk) for chunk in chunker.chunks()]

    assert len(chunks) >= 3
    assert chunks[0].line_number_start_inclusive == 1
    assert chunks[-1].line_number_end_inclusive == 120

    previous_start = 0
    for chunk in chunks:
        assert chunk.line_number_start_inclusive > previous_start
        assert chunk.line_number_end_inclusive >= chunk.line_number_start_inclusive
        previous_start = chunk.line_number_start_inclusive


def test_fixed_token_chunker_line_numbers_from_missing_metadata(tmp_path: Path) -> None:
    chunk = CodeChunk(
        file_path="example.py",
        content="line1\nline2\nline3",
        line_number_start_inclusive=1,
        line_number_end_inclusive=3,
    )

    class StubDoc:
        def __init__(self, text: str, start_index: int) -> None:
            self.page_content = text
            self.metadata = {"start_index": start_index}

    class StubSplitter:
        def __init__(self, docs: list[StubDoc]) -> None:
            self._docs = docs

        def create_documents(self, texts: list[str]):
            assert texts == [chunk.content]
            return self._docs

    docs = [
        StubDoc("line1\n", 0),
        StubDoc("line2\n", -1),
        StubDoc("line3", -1),
    ]

    chunker = FixedTokenChunker(InMemory(chunk, root_path=str(tmp_path)), chunk_size=10, chunk_overlap=0)
    splits = list(chunker.split_file(StubSplitter(docs), chunk))

    assert len(splits) == 3
    assert [(s.line_number_start_inclusive, s.line_number_end_inclusive) for s in splits] == [(1, 1), (2, 2), (3, 3)]
