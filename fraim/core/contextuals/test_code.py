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
            )
        ],
    )

    assert len(code_chunks) == 14
