import logging
from typing import cast

from fraim.core.contextuals import CodeChunk
from fraim.inputs.chunkers.file import FileChunker
from fraim.inputs.chunkers.tests.lib import InMemory

log = logging.getLogger(__name__)


def test_file_chunker() -> None:
    """Test that NoneChunker yields the whole project as a single chunk."""
    _input = InMemory(
        CodeChunk(
            file_path="file1.py",
            content="print('Hello, World!')",
            line_number_start_inclusive=1,
            line_number_end_inclusive=1,
        ),
        root_path="/project",
    )

    chunks = [
        cast(CodeChunk, chunk)
        for chunk in FileChunker(input=_input, model="gemini/gemini-2.5-flash", chunk_size=100, logger=log)
    ]

    assert len(chunks) == 1
    assert chunks[0].content == "print('Hello, World!')"
    assert chunks[0].file_path == "file1.py"
    assert chunks[0].line_number_start_inclusive == 1
    assert chunks[0].line_number_end_inclusive == 1
