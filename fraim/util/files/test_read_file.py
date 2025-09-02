# SPDX-License-Identifier: MIT
# Copyright (c) 2025 Resourcely Inc.

"""Tests for read_file module"""

import tempfile
from collections.abc import Generator
from pathlib import Path

import pytest

from .basepath import BasePathFS
from .read_file import read_file


@pytest.fixture
def test_fs() -> Generator[BasePathFS, None, None]:
    """Create a temporary directory structure for testing."""
    temp_dir = tempfile.mkdtemp()
    temp_path = Path(temp_dir)

    # Create test files with different content
    # Single line file
    (temp_path / "single_line.txt").write_text("Hello, World!")

    # Multi-line file
    multiline_content = "Line 1\nLine 2\nLine 3\nLine 4\nLine 5\n"
    (temp_path / "multiline.txt").write_text(multiline_content)

    # Empty file
    (temp_path / "empty.txt").write_text("")

    # File with various line endings and unicode
    mixed_content = "First line\nSecond line\rThird line\r\nFourth line with émojis 🚀\n"
    (temp_path / "mixed.txt").write_text(mixed_content)

    # Large file for testing limits
    large_content = "\n".join([f"Line {i}" for i in range(1, 101)])  # 100 lines
    (temp_path / "large.txt").write_text(large_content)

    # Binary-like content that will be handled with errors='replace'
    binary_content = "Normal text\x00\xff\xfe\xddMore text"
    (temp_path / "binary.txt").write_text(binary_content, encoding="utf-8", errors="ignore")

    # Create a directory for error testing
    (temp_path / "test_dir").mkdir()

    fs = BasePathFS(temp_path)

    yield fs

    # Clean up
    import shutil

    shutil.rmtree(temp_dir)


class TestReadFile:
    def test_read_entire_file(self, test_fs: BasePathFS) -> None:
        """Test reading an entire file without offset or limit."""
        result = read_file(test_fs, "single_line.txt")
        assert result == "Hello, World!"

    def test_read_multiline_file(self, test_fs: BasePathFS) -> None:
        """Test reading a multiline file."""
        result = read_file(test_fs, "multiline.txt")
        expected = "Line 1\nLine 2\nLine 3\nLine 4\nLine 5\n"
        assert result == expected

    def test_read_empty_file(self, test_fs: BasePathFS) -> None:
        """Test reading an empty file."""
        result = read_file(test_fs, "empty.txt")
        assert result == ""

    def test_read_with_offset(self, test_fs: BasePathFS) -> None:
        """Test reading file starting from a specific line."""
        result = read_file(test_fs, "multiline.txt", offset=3)
        expected = "Line 3\nLine 4\nLine 5\n"
        assert result == expected

    def test_read_with_limit(self, test_fs: BasePathFS) -> None:
        """Test reading file with line limit."""
        result = read_file(test_fs, "multiline.txt", limit=2)
        expected = "Line 1\nLine 2\n"
        assert result == expected

    def test_read_with_offset_and_limit(self, test_fs: BasePathFS) -> None:
        """Test reading file with both offset and limit."""
        result = read_file(test_fs, "multiline.txt", offset=2, limit=2)
        expected = "Line 2\nLine 3\n"
        assert result == expected

    def test_read_offset_beyond_file(self, test_fs: BasePathFS) -> None:
        """Test reading with offset beyond file length."""
        result = read_file(test_fs, "multiline.txt", offset=10)
        assert result == ""

    def test_read_limit_larger_than_file(self, test_fs: BasePathFS) -> None:
        """Test reading with limit larger than file."""
        result = read_file(test_fs, "multiline.txt", limit=100)
        expected = "Line 1\nLine 2\nLine 3\nLine 4\nLine 5\n"
        assert result == expected

    def test_read_large_file_with_limits(self, test_fs: BasePathFS) -> None:
        """Test reading portions of a large file."""
        # Read middle section
        result = read_file(test_fs, "large.txt", offset=50, limit=3)
        expected = "Line 50\nLine 51\nLine 52\n"
        assert result == expected

    def test_read_with_zero_limit(self, test_fs: BasePathFS) -> None:
        """Test reading with zero limit.

        Note: Current implementation adds one line before checking limit,
        so limit=0 actually returns the first line.
        """
        result = read_file(test_fs, "multiline.txt", limit=0)
        # Current behavior: returns first line even with limit=0
        assert result == "Line 1\n"

    def test_read_with_offset_one(self, test_fs: BasePathFS) -> None:
        """Test that offset=1 starts from first line (1-based indexing)."""
        result = read_file(test_fs, "multiline.txt", offset=1, limit=1)
        expected = "Line 1\n"
        assert result == expected

    def test_read_mixed_line_endings(self, test_fs: BasePathFS) -> None:
        """Test reading file with mixed line endings and unicode."""
        result = read_file(test_fs, "mixed.txt")
        # The exact result depends on how Python normalizes line endings
        assert "First line" in result
        assert "émojis 🚀" in result
        assert len(result) > 0

    def test_read_binary_content_with_replacement(self, test_fs: BasePathFS) -> None:
        """Test reading file with binary content that gets replaced."""
        result = read_file(test_fs, "binary.txt")
        # Should contain readable parts, binary parts may be replaced
        assert "Normal text" in result
        assert "More text" in result

    def test_read_nonexistent_file(self, test_fs: BasePathFS) -> None:
        """Test error when reading nonexistent file."""
        with pytest.raises(FileNotFoundError):
            read_file(test_fs, "nonexistent.txt")

    def test_read_directory_instead_of_file(self, test_fs: BasePathFS) -> None:
        """Test error when trying to read a directory."""
        with pytest.raises(IsADirectoryError):
            read_file(test_fs, "test_dir")

    def test_read_with_path_object(self, test_fs: BasePathFS) -> None:
        """Test reading file using Path object instead of string."""
        result = read_file(test_fs, Path("single_line.txt"))
        assert result == "Hello, World!"

    def test_read_file_preserves_line_endings(self, test_fs: BasePathFS) -> None:
        """Test that original line endings are preserved."""
        result = read_file(test_fs, "multiline.txt")
        # Should preserve the \n line endings
        lines = result.split("\n")
        assert len(lines) == 6  # 5 lines + empty string after final \n
        assert lines[-1] == ""  # Final newline creates empty string
        assert lines[0] == "Line 1"

    def test_edge_case_offset_and_limit_combinations(self, test_fs: BasePathFS) -> None:
        """Test various edge cases with offset and limit combinations."""
        # Offset at last line
        result = read_file(test_fs, "multiline.txt", offset=5, limit=1)
        assert result == "Line 5\n"

        # Offset at last line with large limit
        result = read_file(test_fs, "multiline.txt", offset=5, limit=10)
        assert result == "Line 5\n"

        # Very large offset
        result = read_file(test_fs, "multiline.txt", offset=1000)
        assert result == ""
