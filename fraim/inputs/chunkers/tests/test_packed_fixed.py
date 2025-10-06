# SPDX-License-Identifier: MIT
# Copyright (c) 2025 Resourcely Inc.
import logging
from pathlib import Path

import pytest

from fraim.core.contextuals import CodeChunk
from fraim.inputs.chunkers.packed_fixed import PackingSyntacticChunker
from fraim.inputs.chunkers.tests.lib import InMemory

# from fraim.inputs.file import File

log = logging.getLogger(__name__)


@pytest.fixture
def project_path(tmp_path: Path) -> str:
    return str(tmp_path)


def test_pack_multiple_small_files_into_one_chunk(project_path: str) -> None:
    # Two small files that should be packed into a single chunk.
    file_1 = CodeChunk("file1.py", "print('hello')", line_number_start_inclusive=1, line_number_end_inclusive=1)
    file_2 = CodeChunk("file2.py", "print('world')", line_number_start_inclusive=1, line_number_end_inclusive=1)
    _input = InMemory(file_1, file_2, root_path=project_path)

    # Set chunk_size large enough to hold both files.
    chunks = list(PackingSyntacticChunker(_input, chunk_size=1000, logger=log).chunks())

    assert len(chunks) == 1
    assert len(chunks[0]) == 8
    assert chunks[0][0].file_path == "file1.py"
    assert chunks[0][1].file_path == "file2.py"


def test_pack_files_into_multiple_chunks(project_path: str) -> None:
    # Three files, first two fit in one chunk, the third in a new one.
    file_1 = CodeChunk("file1.py", "print('file1')", line_number_start_inclusive=1, line_number_end_inclusive=1)
    file_2 = CodeChunk("file2.py", "print('file2')", line_number_start_inclusive=1, line_number_end_inclusive=1)
    file_3 = CodeChunk("file3.py", "print('file3')", line_number_start_inclusive=1, line_number_end_inclusive=1)
    _input = InMemory(file_1, file_2, file_3, root_path=project_path)

    # Set chunk_size so that first two files fit, but adding the third exceeds it.
    chunks = list(PackingSyntacticChunker(_input, chunk_size=10, chunk_overlap=0, logger=log).chunks())

    assert len(chunks) == 2
    assert len(chunks[0]) == 10  # First two files
    assert chunks[0][0].file_path == "file1.py"
    assert chunks[0][1].file_path == "file2.py"
    assert len(chunks[1]) == 5  # Third file
    assert chunks[1][0].file_path == "file3.py"


def test_small_files_are_packed(project_path: str) -> None:
    # A single file larger than the line limit of PackingFixedChunker, which gets split
    # into multiple CodeChunks, which are then packed.
    chunk_size = 500
    num_of_small_files = 3
    large_content = "a\n" * 20
    chunk = CodeChunk("small_file.py", large_content, line_number_start_inclusive=1, line_number_end_inclusive=1)
    _input = InMemory(*[chunk] * num_of_small_files, root_path=project_path)

    # chunk_size for PackingFixedChunker (bytes) is 500, so packed chunks should be small.
    chunks = list(PackingSyntacticChunker(_input, chunk_size=chunk_size, logger=log).chunks())

    # PackingFixedChunker with byte chunk_size=500 will receive these two CodeChunk.
    # The first CodeChunk is added. The second one is checked.
    # len(str(CodeChunks(chunk1, chunk2))) will be checked against 500.
    # str(CodeChunk) is roughly 130 + content_len. Content is 10 lines of "line\n" + line numbers.
    # So each CodeChunk is well under 500. The two combined should also be under 500.
    # So they should be packed into one CodeChunks.
    assert len(chunks) == 1
    assert len(chunks[0]) == 117 # Measured in tokens
    assert chunks[0][0].file_path == "small_file.py"
    assert chunks[0][1].file_path == "small_file.py"
    assert chunks[0][0].line_number_start_inclusive == 1
    assert chunks[0][1].line_number_end_inclusive > 1


def test_single_large_file_violates_chunk_size(project_path: str) -> None:
    # A single file chunk that is larger than the packing chunk_size.
    # The chunker should yield it by itself.
    content = "a" * 500
    chunk = CodeChunk("very_large_file.py", content, line_number_start_inclusive=1, line_number_end_inclusive=1)
    _input = InMemory(chunk, root_path=project_path)

    # Set chunk_size for PackingFixedChunker (bytes) smaller than the file content.
    chunks = list(PackingSyntacticChunker(_input, chunk_size=400, chunk_lines=1000, logger=log).chunks())

    assert len(chunks) == 1
    assert len(chunks[0]) == 125 # Measured in tokens
    assert len(str(chunks[0])) > 400


def test_empty_input(project_path: str) -> None:
    _input = InMemory(root_path=project_path)
    chunks = list(PackingSyntacticChunker(input=_input, chunk_size=1000, logger=log).chunks())
    assert len(chunks) == 0


def test_single_small_file(project_path: str) -> None:
    chunk = CodeChunk("single.py", "print('single')", line_number_start_inclusive=1, line_number_end_inclusive=1)
    _input = InMemory(chunk, root_path=project_path)
    chunks = list(PackingSyntacticChunker(input=_input, chunk_size=1000, logger=log).chunks())

    assert len(chunks) == 1
    assert len(chunks[0]) == 4 # Measured in tokens
    assert chunks[0][0].file_path == "single.py"
