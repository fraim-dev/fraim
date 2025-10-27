# SPDX-License-Identifier: MIT
from pathlib import Path

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
    chunks = list(chunker.chunks())

    assert len(chunks) >= 3
    assert chunks[0].line_number_start_inclusive == 1
    assert chunks[-1].line_number_end_inclusive == 120

    previous_start = 0
    for chunk in chunks:
        assert chunk.line_number_start_inclusive > previous_start
        assert chunk.line_number_end_inclusive >= chunk.line_number_start_inclusive
        previous_start = chunk.line_number_start_inclusive
