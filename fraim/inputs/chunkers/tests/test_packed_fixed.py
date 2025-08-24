# SPDX-License-Identifier: MIT
# Copyright (c) 2025 Resourcely Inc.
from pathlib import Path

import pytest

from fraim.inputs.chunkers.packed_fixed import PackingFixedChunker
from fraim.inputs.chunkers.tests.lib import InMemory
from fraim.inputs.files import File


@pytest.fixture
def project_path(tmp_path: Path) -> str:
    return str(tmp_path)


def test_pack_multiple_small_files_into_one_chunk(project_path: str):
    # Two small files that should be packed into a single chunk.
    files = InMemory(
        File(Path("file1.py"), "print('hello')"),
        File(Path("file2.py"), "print('world')"),
        root_path=project_path,
    )

    # Set chunk_size large enough to hold both files.
    chunker = PackingFixedChunker(files, chunk_size=1000)
    chunks = list(chunker)

    assert len(chunks) == 1
    assert len(chunks[0]) == 2
    assert chunks[0][0].file_path == "file1.py"
    assert chunks[0][1].file_path == "file2.py"


def test_pack_files_into_multiple_chunks(project_path: str):
    # Three files, first two fit in one chunk, the third in a new one.
    files = InMemory(
        File(Path("file1.py"), "print('file1')"),
        File(Path("file2.py"), "print('file2')"),
        File(Path("file3.py"), "print('file3')"),
        root_path=project_path,
    )

    # Set chunk_size so that first two files fit, but adding the third exceeds it.
    # A single chunk is ~150 chars. Let's set it to 350 to fit two.
    chunker = PackingFixedChunker(files, chunk_size=350, chunk_overlap=100)
    chunks = list(chunker)

    assert len(chunks) == 2
    assert len(chunks[0]) == 2  # First two files
    assert chunks[0][0].file_path == "file1.py"
    assert chunks[0][1].file_path == "file2.py"
    assert len(chunks[1]) == 1  # Third file
    assert chunks[1][0].file_path == "file3.py"


def test_small_files_are_packed(project_path: str):
    # A single file larger than the line limit of FixedCharChunker, which gets split
    # into multiple CodeChunks, which are then packed.
    chunk_size = 500
    num_of_small_files = 3
    large_content = "a\n" * 20
    files = InMemory(*[File(Path("small_file.py"), large_content)] * num_of_small_files, root_path=project_path)

    # chunk_size for FixedCharChunker (lines) is 10, so it should be split.
    # chunk_size for PackingFixedChunker (bytes) is 500, so packed chunks should be small.
    chunks = list(PackingFixedChunker(files, chunk_size=chunk_size))

    # FixedCharChunker with chunk_size=10 will split 20 lines into 2 chunks.
    # PackingFixedChunker with byte chunk_size=500 will receive these two CodeChunk.
    # The first CodeChunk is added. The second one is checked.
    # len(str(CodeChunks(chunk1, chunk2))) will be checked against 500.
    # str(CodeChunk) is roughly 130 + content_len. Content is 10 lines of "line\n" + line numbers.
    # So each CodeChunk is well under 500. The two combined should also be under 500.
    # So they should be packed into one CodeChunks.
    assert len(chunks) == 1
    assert len(chunks[0]) == num_of_small_files
    assert chunks[0][0].file_path == "small_file.py"
    assert chunks[0][1].file_path == "small_file.py"
    assert chunks[0][0].line_number_start_inclusive == 1
    assert chunks[0][1].line_number_end_inclusive > 1


def test_single_large_file_violates_chunk_size(project_path: str):
    # A single file chunk that is larger than the packing chunk_size.
    # The chunker should yield it by itself.
    content = "a" * 500
    files = InMemory(File(Path("very_large_file.py"), content), root_path=project_path)

    # Set chunk_size for PackingFixedChunker (bytes) smaller than the file content.
    chunker = PackingFixedChunker(files, chunk_size=400, chunk_lines=1000)
    chunks = list(chunker)

    assert len(chunks) == 1
    assert len(chunks[0]) == 1
    assert len(str(chunks[0])) > 400


def test_empty_input(project_path: str):
    files = InMemory(root_path=project_path)
    chunker = PackingFixedChunker(files=files, chunk_size=1000)
    chunks = list(chunker)
    assert len(chunks) == 0


def test_single_small_file(project_path: str):
    files = InMemory(File(Path("single.py"), "print('single')"), root_path=project_path)
    chunks = list(PackingFixedChunker(files=files, chunk_size=1000))

    assert len(chunks) == 1
    assert len(chunks[0]) == 1
    assert chunks[0][0].file_path == "single.py"
