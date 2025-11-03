# SPDX-License-Identifier: MIT
from pathlib import Path
from typing import Any, cast

import pytest
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

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


@pytest.mark.parametrize(
    ("content", "chunk_size", "chunk_overlap", "expected_contents", "expected_lines"),
    [
        ("1\n2\n3\n", 2, 0, ["1", "2", "3"], [(1, 1), (2, 2), (3, 3)]),
        ("1\n2\n3", 2, 0, ["1", "2", "3"], [(1, 1), (2, 2), (3, 3)]),
        ("x\nx\nx\nx\n", 2, 0, ["x", "x", "x", "x"], [(1, 1), (2, 2), (3, 3), (4, 4)]),
        ("alpha\nbeta\ngamma\n", 500, 0, ["alpha\nbeta\ngamma"], [(1, 3)]),
    ],
)
def test_fixed_token_chunker_line_numbers_2(
    tmp_path: Path,
    content: str,
    chunk_size: int,
    chunk_overlap: int,
    expected_contents: list[str],
    expected_lines: list[tuple[int, int]],
) -> None:
    line_count = len(content.splitlines())
    file = CodeChunk(
        file_path="example.py",
        content=content,
        line_number_start_inclusive=1,
        line_number_end_inclusive=line_count,
    )

    chunker = FixedTokenChunker(
        InMemory(file, root_path=str(tmp_path)), chunk_size=chunk_size, chunk_overlap=chunk_overlap
    )
    splits = list(chunker.split_file(chunker.splitter, file))

    assert [s.content for s in splits] == expected_contents
    assert [(s.line_number_start_inclusive, s.line_number_end_inclusive) for s in splits] == expected_lines


class StubSplitter:
    def __init__(self, documents: list[str]) -> None:
        self._documents = documents

    def create_documents(self, texts: list[str], metadatas: list[dict[str, Any]] | None = None) -> list[Document]:
        return [Document(page_content=doc) for doc in self._documents]


def test_fixed_token_chunker_line_numbers_with_overlap(tmp_path: Path) -> None:
    file = CodeChunk(
        file_path="example.py",
        content="a\nb\nc\nd\n",
        line_number_start_inclusive=1,
        line_number_end_inclusive=3,
    )

    # splitter = StubSplitter(["aa\nbb", "bb\ncc"])
    chunker = FixedTokenChunker(InMemory(file, root_path=str(tmp_path)), chunk_size=5, chunk_overlap=2)

    splits = list(chunker.split_file(chunker.splitter, file))

    assert [s.content for s in splits] == ["a\nb\nc", "c\nd"]
    assert [(s.line_number_start_inclusive, s.line_number_end_inclusive) for s in splits] == [(1, 3), (3, 4)]


def test_fixed_token_chunker_skips_empty_documents(tmp_path: Path) -> None:
    file = CodeChunk(
        file_path="example.py",
        content="",
        line_number_start_inclusive=1,
        line_number_end_inclusive=3,
    )

    chunker = FixedTokenChunker(InMemory(file, root_path=str(tmp_path)), chunk_size=10, chunk_overlap=5)

    splits = list(chunker.split_file(chunker.splitter, file))

    assert [s.content for s in splits] == []
    assert [(s.line_number_start_inclusive, s.line_number_end_inclusive) for s in splits] == []
