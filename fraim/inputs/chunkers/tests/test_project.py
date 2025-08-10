import contextlib
from typing import Iterator

import pytest

from fraim.inputs.chunkers.file import FileChunker
from fraim.inputs.chunkers.project import ProjectChunker
from fraim.inputs.chunkers.tests.lib import mock_files
from fraim.inputs.files import File


def test_project_chunker():
    """Test that NoneChunker yields the whole project as a single chunk."""
    files = mock_files(
        File(path="file1.py", body="print('Hello, from file1!')"),
        File(path="file2.py", body="print('Hello, from file2!')"),
    )

    chunker = ProjectChunker(files=files, project_path="/project", chunk_size=100, logger=None)

    chunks = list(chunker)

    assert len(chunks) == 1
    assert len(chunks[0]) == 2
    assert chunks[0][0].content == "print('Hello, from file1!')"
    assert chunks[0][0].file_path == "file1.py"
    assert chunks[0][0].line_number_start_inclusive == 1
    assert chunks[0][0].line_number_end_inclusive == 1

    assert chunks[0][1].content == "print('Hello, from file2!')"
    assert chunks[0][1].file_path == "file2.py"
    assert chunks[0][1].line_number_start_inclusive == 1
    assert chunks[0][1].line_number_end_inclusive == 1
