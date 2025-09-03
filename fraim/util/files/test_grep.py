# SPDX-License-Identifier: MIT
# Copyright (c) 2025 Resourcely Inc.

"""Tests for grep module"""

import tempfile
from collections.abc import Generator
from pathlib import Path

import pytest

from .basepath import BasePathFS
from .grep import grep


@pytest.fixture
def test_fs() -> Generator[BasePathFS, None, None]:
    """Create a temporary directory structure for testing grep functionality."""
    temp_dir = tempfile.mkdtemp()
    temp_path = Path(temp_dir)

    # Create test files with different content for grep testing
    # Simple text file
    (temp_path / "simple.txt").write_text("Hello, World!\nThis is a test.\nAnother line here.")

    # Python file
    python_content = """def hello_world():
    print("Hello, World!")
    return "success"

class TestClass:
    def __init__(self):
        self.value = "test"
    
    def get_value(self):
        return self.value
"""
    (temp_path / "test.py").write_text(python_content)

    # JavaScript file
    js_content = """function greetUser(name) {
    console.log("Hello, " + name);
    return true;
}

const userData = {
    name: "test",
    age: 25
};
"""
    (temp_path / "test.js").write_text(js_content)

    # Multi-line patterns file
    multiline_content = """Start of block
This is inside a block
End of block

Another block starts here
More content in block
Block ends here
"""
    (temp_path / "multiline.txt").write_text(multiline_content)

    # Case sensitivity test file
    case_content = """lowercase text here
UPPERCASE TEXT HERE
MixedCase Text Here
"""
    (temp_path / "case_test.txt").write_text(case_content)

    # Empty file
    (temp_path / "empty.txt").write_text("")

    # Large file for testing limits
    large_lines = [f"Line {i} with some content and numbers {i * 2}" for i in range(1, 201)]
    (temp_path / "large.txt").write_text("\n".join(large_lines))

    # Create subdirectory with files
    (temp_path / "subdir").mkdir()
    (temp_path / "subdir" / "nested.txt").write_text("Nested file content\nMore nested content")
    (temp_path / "subdir" / "other.py").write_text("print('nested python')\ndef nested_func(): pass")

    fs = BasePathFS(temp_path)

    yield fs

    # Clean up
    import shutil

    shutil.rmtree(temp_dir)


class TestGrepBasicFunctionality:
    """Test basic grep functionality and pattern matching."""

    @pytest.mark.asyncio
    async def test_simple_pattern_match(self, test_fs: BasePathFS) -> None:
        """Test basic pattern matching in a single file."""
        result = await grep(test_fs, "Hello", "simple.txt")
        assert "Hello, World!" in result
        assert result.count("Hello") == 1

    @pytest.mark.asyncio
    async def test_no_matches_returns_empty(self, test_fs: BasePathFS) -> None:
        """Test that no matches returns empty string."""
        result = await grep(test_fs, "nonexistent_pattern", "simple.txt")
        assert result == ""

    @pytest.mark.asyncio
    async def test_multiple_matches(self, test_fs: BasePathFS) -> None:
        """Test pattern that matches multiple lines."""
        result = await grep(test_fs, "test", "test.py")
        assert "test" in result.lower()
        # Should find matches - at least one should be present
        assert len(result) > 0

    @pytest.mark.asyncio
    async def test_regex_pattern(self, test_fs: BasePathFS) -> None:
        """Test regex pattern matching."""
        result = await grep(test_fs, r"def \w+", "test.py")
        assert "def hello_world" in result
        assert "def get_value" in result

    @pytest.mark.asyncio
    async def test_directory_search(self, test_fs: BasePathFS) -> None:
        """Test searching in a directory (recursive)."""
        result = await grep(test_fs, "Hello", ".")
        # Should find matches in multiple files
        assert "simple.txt" in result
        assert "Hello" in result

    @pytest.mark.asyncio
    async def test_subdirectory_search(self, test_fs: BasePathFS) -> None:
        """Test searching in a subdirectory."""
        result = await grep(test_fs, "nested", "subdir")
        assert "nested" in result.lower()
        assert result != ""


class TestGrepOutputModes:
    """Test different output modes for grep."""

    @pytest.mark.asyncio
    async def test_content_mode_default(self, test_fs: BasePathFS) -> None:
        """Test default content output mode includes line numbers."""
        result = await grep(test_fs, "Hello", "simple.txt", output_mode="content")
        # Content mode should include line numbers
        assert "1:" in result or ":" in result  # ripgrep line number format
        assert "Hello, World!" in result

    @pytest.mark.asyncio
    async def test_files_with_matches_mode(self, test_fs: BasePathFS) -> None:
        """Test files_with_matches output mode."""
        result = await grep(test_fs, "test", ".", output_mode="files_with_matches")
        # Should only show file paths, not content
        assert "test.py" in result
        assert "def" not in result  # No actual content
        assert "Hello" not in result  # No content from other files

    @pytest.mark.asyncio
    async def test_count_mode(self, test_fs: BasePathFS) -> None:
        """Test count output mode."""
        result = await grep(test_fs, "test", "test.py", output_mode="count")
        # Count mode should return numeric results
        assert result.strip().isdigit() or (":" in result and any(part.isdigit() for part in result.split(":")))


class TestGrepContextOptions:
    """Test context options (-A, -B, -C)."""

    @pytest.mark.asyncio
    async def test_context_after(self, test_fs: BasePathFS) -> None:
        """Test showing lines after match."""
        result = await grep(test_fs, "Hello, World", "simple.txt", context_after=1)
        assert "Hello, World!" in result
        assert "This is a test." in result  # Line after

    @pytest.mark.asyncio
    async def test_context_before(self, test_fs: BasePathFS) -> None:
        """Test showing lines before match."""
        result = await grep(test_fs, "Another line", "simple.txt", context_before=2)
        assert "Another line here." in result
        assert "Hello, World!" in result  # Line before
        assert "This is a test." in result  # Line before

    @pytest.mark.asyncio
    async def test_context_around(self, test_fs: BasePathFS) -> None:
        """Test showing lines around match."""
        result = await grep(test_fs, "This is a test", "simple.txt", context_around=1)
        assert "Hello, World!" in result  # Line before
        assert "This is a test." in result  # Matched line
        assert "Another line here." in result  # Line after

    @pytest.mark.asyncio
    async def test_context_options_only_with_content_mode(self, test_fs: BasePathFS) -> None:
        """Test that context options raise error with non-content output modes."""
        with pytest.raises(ValueError, match="Context options.*only supported.*content"):
            await grep(test_fs, "test", "test.py", output_mode="files_with_matches", context_after=1)

        with pytest.raises(ValueError, match="Context options.*only supported.*content"):
            await grep(test_fs, "test", "test.py", output_mode="count", context_before=1)


class TestGrepFilteringOptions:
    """Test file type and glob filtering options."""

    @pytest.mark.asyncio
    async def test_file_type_filter(self, test_fs: BasePathFS) -> None:
        """Test filtering by file type."""
        result = await grep(test_fs, "test", ".", file_type="py")
        # Should only search Python files
        assert "test.py" in result or "other.py" in result
        # Should not include results from .txt or .js files
        lines = result.split("\n")
        file_lines = [line for line in lines if ":" in line and not line.startswith("-")]
        py_files = [line for line in file_lines if ".py:" in line]
        non_py_files = [line for line in file_lines if ".py:" not in line and line.strip()]
        assert len(py_files) > 0
        assert len(non_py_files) == 0

    @pytest.mark.asyncio
    async def test_glob_filter(self, test_fs: BasePathFS) -> None:
        """Test filtering with glob patterns."""
        result = await grep(test_fs, "test", ".", glob="*.py")
        # Should only search files matching *.py
        assert "test.py" in result or "def" in result  # Python content
        # Verify we're not searching other file types
        assert "simple.txt" not in result


class TestGrepCaseAndMultiline:
    """Test case sensitivity and multiline options."""

    @pytest.mark.asyncio
    async def test_case_sensitive_default(self, test_fs: BasePathFS) -> None:
        """Test that search is case sensitive by default."""
        result_lower = await grep(test_fs, "uppercase", "case_test.txt")
        result_upper = await grep(test_fs, "UPPERCASE", "case_test.txt")

        assert result_lower == ""  # Should not match
        assert "UPPERCASE TEXT HERE" in result_upper  # Should match

    @pytest.mark.asyncio
    async def test_case_insensitive_search(self, test_fs: BasePathFS) -> None:
        """Test case insensitive search."""
        result = await grep(test_fs, "uppercase", "case_test.txt", case_insensitive=True)
        assert "UPPERCASE TEXT HERE" in result

    @pytest.mark.asyncio
    async def test_multiline_pattern(self, test_fs: BasePathFS) -> None:
        """Test multiline pattern matching."""
        # Pattern that spans multiple lines
        result = await grep(test_fs, r"Start.*?End", "multiline.txt", multiline=True)
        assert "Start of block" in result
        assert "End of block" in result


class TestGrepHeadLimit:
    """Test head limit functionality."""

    @pytest.mark.asyncio
    async def test_head_limit_restricts_output(self, test_fs: BasePathFS) -> None:
        """Test that head limit restricts the number of output lines."""
        # Search in large file with many matches
        result_unlimited = await grep(test_fs, "Line", "large.txt")
        result_limited = await grep(test_fs, "Line", "large.txt", head_limit=5)

        unlimited_lines = len([line for line in result_unlimited.split("\n") if line.strip()])
        limited_lines = len([line for line in result_limited.split("\n") if line.strip()])

        assert unlimited_lines > 5
        assert limited_lines <= 5

    @pytest.mark.asyncio
    async def test_head_limit_none_returns_all(self, test_fs: BasePathFS) -> None:
        """Test that head_limit=None returns all results."""
        result = await grep(test_fs, "Line", "large.txt", head_limit=None)
        lines = [line for line in result.split("\n") if line.strip()]
        assert len(lines) > 10  # Should get many results

    @pytest.mark.asyncio
    async def test_head_limit_terminates_subprocess_properly(self, test_fs: BasePathFS) -> None:
        """Test that subprocess is properly terminated when head_limit causes early return.

        This test verifies the bug fix where _head returning early due to head_limit
        would leave the subprocess running and potentially cause hangs.
        """
        import time

        # Search for a pattern that would produce many results in a large file
        start_time = time.time()
        result = await grep(test_fs, "Line", "large.txt", head_limit=3)
        end_time = time.time()

        # Should complete quickly (much less than if we read the entire large file)
        assert end_time - start_time < 1.0  # Should be very fast

        # Should have limited output
        lines = [line for line in result.split("\n") if line.strip()]
        assert len(lines) <= 3

        # Should still have found something
        assert len(lines) > 0


class TestGrepErrorHandling:
    """Test error handling and edge cases."""

    @pytest.mark.asyncio
    async def test_nonexistent_file_raises_error(self, test_fs: BasePathFS) -> None:
        """Test that searching nonexistent file raises FileNotFoundError."""
        with pytest.raises(FileNotFoundError):
            await grep(test_fs, "pattern", "nonexistent.txt")

    @pytest.mark.asyncio
    async def test_path_outside_sandbox_raises_error(self, test_fs: BasePathFS) -> None:
        """Test that paths outside sandbox raise PermissionError."""
        with pytest.raises(PermissionError):
            await grep(test_fs, "pattern", "/etc/passwd")

    @pytest.mark.asyncio
    async def test_empty_file_returns_empty(self, test_fs: BasePathFS) -> None:
        """Test that searching empty file returns empty string."""
        result = await grep(test_fs, "anything", "empty.txt")
        assert result == ""

    @pytest.mark.asyncio
    async def test_invalid_regex_raises_error(self, test_fs: BasePathFS) -> None:
        """Test that invalid regex patterns raise appropriate errors."""
        with pytest.raises(ValueError):
            # Invalid regex that should cause ripgrep to fail
            await grep(test_fs, "[", "simple.txt")


class TestGrepPathHandling:
    """Test path handling with Path objects and different path formats."""

    @pytest.mark.asyncio
    async def test_path_object_input(self, test_fs: BasePathFS) -> None:
        """Test using Path object instead of string."""
        result = await grep(test_fs, "Hello", Path("simple.txt"))
        assert "Hello, World!" in result

    @pytest.mark.asyncio
    async def test_relative_path_search(self, test_fs: BasePathFS) -> None:
        """Test searching with relative paths."""
        result = await grep(test_fs, "nested", "subdir/nested.txt")
        # Should find the word "nested" in the file
        assert "nested" in result.lower()

    @pytest.mark.asyncio
    async def test_current_directory_search(self, test_fs: BasePathFS) -> None:
        """Test searching current directory with '.' path."""
        result = await grep(test_fs, "Hello", ".")
        assert "Hello" in result
        assert len(result) > 0


class TestGrepIntegration:
    """Integration tests combining multiple features."""

    @pytest.mark.asyncio
    async def test_complex_search_with_multiple_options(self, test_fs: BasePathFS) -> None:
        """Test combining multiple grep options."""
        result = await grep(test_fs, "def", ".", file_type="py", context_after=1, case_insensitive=True)

        # Should find function definitions in Python files
        assert "def" in result
        # Should include context lines
        lines = result.split("\n")
        assert len(lines) > 2  # Should have context lines
