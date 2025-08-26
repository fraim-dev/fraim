from pathlib import Path

from fraim.core.contextuals import CodeChunk
from fraim.inputs.chunkers.file import FileChunker
from fraim.inputs.chunkers.tests.lib import InMemory
import logging

from fraim.inputs.file import File

log = logging.getLogger(__name__)


def test_file_chunker():
    """Test that NoneChunker yields the whole project as a single chunk."""
    files = InMemory(File(path="file1.py", body="print('Hello, World!')"), root_path="/project")

    chunker = FileChunker(files=files, chunk_size=100, logger=log)

    chunks = list(chunker)

    assert len(chunks) == 1
    assert chunks[0].content == "print('Hello, World!')"
    assert chunks[0].file_path == "file1.py"
    assert chunks[0].line_number_start_inclusive == 1
    assert chunks[0].line_number_end_inclusive == 1
