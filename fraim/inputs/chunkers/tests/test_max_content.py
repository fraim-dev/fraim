import logging
from pathlib import Path
from unittest.mock import MagicMock, patch

from fraim.core.contextuals.code import CodeChunks
from fraim.inputs.chunkers.max_context import MaxContextChunker
from fraim.inputs.chunkers.tests.lib import InMemory
from fraim.inputs.file import File

log = logging.getLogger(__name__)

def test_max_content_chunker() -> None:
    """Test that NoneChunker yields the whole project as a single chunk."""

    fraction = 0.7

    file_1 = File(path=Path("file1.py"), body="print('Hello, from file1!')")
    file_2 = File(path=Path("file2.py"), body="print('Hello, from file2!')")
    files = InMemory(file_1, file_2, root_path="/project")

    chunker = MaxContextChunker(files=files, model='gemini/gemini-2.5-flash', fraction=fraction, logger=log)

    chunks = list(chunker)

    assert len(chunks) == 1
    assert len(chunks[0]) == 2
    assert chunks[0][0].content == file_1.body
    assert chunks[0][0].file_path == str(file_1.path)
    assert chunks[0][0].line_number_start_inclusive == 1
    assert chunks[0][0].line_number_end_inclusive == 1

    assert chunks[0][1].content == file_2.body
    assert chunks[0][1].file_path == str(file_2.path)
    assert chunks[0][1].line_number_start_inclusive == 1
    assert chunks[0][1].line_number_end_inclusive == 1


@patch('fraim.inputs.chunkers.max_context.get_max_tokens')
def test_max_content_chunker_overflow(mock_get_max_tokens: MagicMock) -> None:
    """Test that NoneChunker yields the whole project as a single chunk."""

    fraction = 0.7

    mock_get_max_tokens.return_value = 100 / fraction  # So that chunk_size becomes 100

    file_1 = File(path="file1.py", body="print('Hello, from file1!')")
    file_2 = File(path="file2.py", body="a " * 120)
    files = InMemory(file_1, file_2, root_path="/project")

    chunker = MaxContextChunker(files=files, model='test', fraction=fraction, logger=log)

    chunks = list(chunker)

    assert len(chunks) == 2
    assert isinstance(chunks[0], CodeChunks)
    assert len(chunks[0]) == 1
    assert chunks[0][0].content == file_1.body
    assert chunks[0][0].file_path == str(file_1.path)

    assert isinstance(chunks[1], CodeChunks)
    assert len(chunks[1]) == 1
    assert chunks[1][0].content == file_2.body
    assert chunks[1][0].file_path == str(file_2.path)
