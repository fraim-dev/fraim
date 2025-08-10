from contextlib import contextmanager
from typing import Iterator

from fraim.inputs.chunkers.file import FileChunker
from fraim.inputs.files import File, Files


@contextmanager
def mock_files(*files: File) -> Iterator[Files]:
    yield files

