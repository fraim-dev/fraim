import pytest

from fraim.core.contextuals import CodeChunk
from fraim.core.contextuals.code import CodeChunks


def test_code_chunk():
    code_chunk = CodeChunk(
        file_path="example.py",
        content="print('Hello, world!')",
        line_number_start_inclusive=1,
        line_number_end_inclusive=1,
    )

    assert len(code_chunk) == 7


@pytest.mark.parametrize(
    ("file_path", "expected_language"),
    [
        ("module.py", "python"),
        ("script.js", "js"),
        ("component.ts", "ts"),
        ("Example.java", "java"),
    ],
)
def test_code_chunk_language_detection(file_path: str, expected_language: str) -> None:
    chunk = CodeChunk(
        file_path=file_path,
        content="",
        line_number_start_inclusive=1,
        line_number_end_inclusive=1,
    )

    assert chunk.language == expected_language


def test_code_chunks():
    code_chunks = CodeChunks(
        all_files=[
            CodeChunk(
                file_path="example.py",
                content="print('Hello, world!')",
                line_number_start_inclusive=1,
                line_number_end_inclusive=1,
            ),
            CodeChunk(
                file_path="example2.py",
                content="print('Hello, world!')",
                line_number_start_inclusive=1,
                line_number_end_inclusive=1,
            ),
        ],
    )

    assert len(code_chunks) == 14
