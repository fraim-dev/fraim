# SPDX-License-Identifier: MIT
# Copyright (c) 2025 Resourcely Inc.
import math
from pathlib import Path

import pytest

from fraim.inputs.chunkers.fixed import FixedCharChunker
from fraim.inputs.chunkers.tests.lib import InMemory
from fraim.inputs.files import File


@pytest.fixture
def project_path(tmp_path: Path) -> str:
    return str(tmp_path)


def test_single_large_file_is_split(project_path: str):
    # A single file larger than the line limit of FixedCharChunker, which gets split
    # into multiple CodeChunks, which are then packed.
    large_content = "\n".join([str(i) for i in range(1, 25)])  # 25 lines
    files = InMemory(File(Path("large_file.py"), large_content), root_path=project_path)

    original_size = len(large_content)

    chunk_size = 10
    expected_chunks = math.ceil(original_size / chunk_size)

    # chunk_size for FixedCharChunker (lines) is 10, so it should be split.
    # chunk_size for PackingFixedChunker (bytes) is 500, so packed chunks should be small.
    chunks = list(FixedCharChunker(files=files, chunk_size=chunk_size, chunk_overlap=0))
    assert len(chunks) == expected_chunks
    assert chunks[0].content == "1\n2\n3\n4\n5"
    assert chunks[0].line_number_start_inclusive == 1
    assert chunks[0].line_number_end_inclusive == 5
    assert chunks[0].file_path == "large_file.py"

    assert chunks[3].content == "14\n15\n16"
    assert chunks[3].line_number_start_inclusive == 14
    assert chunks[3].line_number_end_inclusive == 16


def test_single_large_file_is_split_with_overlap(project_path: str):
    # A single file larger than the line limit of FixedCharChunker, which gets split
    # into multiple CodeChunks, which are then packed.
    large_content = "\n".join([f"{i + 1}" for i in range(25)])  # 25 lines
    files = InMemory(File(Path("large_file.py"), large_content), root_path=project_path)

    original_size = len(large_content)

    chunk_overlap = 2
    chunk_size = 10
    expected_chunks = int(original_size / (chunk_size - chunk_overlap * 2))

    chunks = list(FixedCharChunker(files=files, chunk_size=chunk_size, chunk_overlap=chunk_overlap))
    assert len(chunks) == expected_chunks

    assert chunks[0].content == "1\n2\n3\n4\n5"
    assert chunks[0].line_number_start_inclusive == 1
    assert chunks[0].line_number_end_inclusive == 5
    assert chunks[0].content == large_content[: chunk_size - 1]

    assert chunks[1].content == "5\n6\n7\n8\n9"
    assert chunks[1].line_number_start_inclusive == 5
    assert chunks[1].line_number_end_inclusive == 9

    assert chunks[3].content == "12\n13\n14"
    assert chunks[3].line_number_start_inclusive == 12
    assert chunks[3].line_number_end_inclusive == 14

    assert chunks[0].file_path == "large_file.py"
    assert chunks[1].file_path == "large_file.py"
    assert chunks[0].line_number_start_inclusive == 1
    assert chunks[1].line_number_start_inclusive > 1
