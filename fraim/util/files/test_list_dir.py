# SPDX-License-Identifier: MIT
# Copyright (c) 2025 Resourcely Inc.

"""Tests for list_dir module"""

import tempfile
from collections.abc import Generator
from pathlib import Path

import pytest

from .basepath import BasePathFS
from .list_dir import list_dir


@pytest.fixture
def test_fs() -> Generator[BasePathFS, None, None]:
    """Create a temporary directory structure for testing.

    Creates a comprehensive test structure:
    temp_dir/
    ├── .hidden_file
    ├── .hidden_dir/
    │   └── hidden_content.txt
    ├── a_dir/
    │   ├── a_file.txt
    │   ├── a_subdir/
    │   │   ├── deep_file.txt
    │   │   └── another_deep.txt
    │   └── b_file.py
    ├── b_dir/
    │   ├── file1.txt
    │   ├── file2.txt
    │   ├── file3.py
    │   └── file4.md
    ├── c_empty_dir/
    ├── d_file.txt
    ├── e_file.py
    ├── f_file.md
    └── external_symlink -> /etc (points outside sandbox)
    """
    temp_dir = tempfile.mkdtemp()
    temp_path = Path(temp_dir)

    # Root level files
    (temp_path / "d_file.txt").write_text("content")
    (temp_path / "e_file.py").write_text("content")
    (temp_path / "f_file.md").write_text("content")

    # Hidden files and directories
    (temp_path / ".hidden_file").write_text("hidden")
    (temp_path / ".hidden_dir").mkdir()
    (temp_path / ".hidden_dir" / "hidden_content.txt").write_text("hidden")

    # a_dir with nested structure
    (temp_path / "a_dir").mkdir()
    (temp_path / "a_dir" / "a_file.txt").write_text("content")
    (temp_path / "a_dir" / "b_file.py").write_text("content")
    (temp_path / "a_dir" / "a_subdir").mkdir()
    (temp_path / "a_dir" / "a_subdir" / "deep_file.txt").write_text("content")
    (temp_path / "a_dir" / "a_subdir" / "another_deep.txt").write_text("content")

    # b_dir with multiple files of different types
    (temp_path / "b_dir").mkdir()
    (temp_path / "b_dir" / "file1.txt").write_text("content")
    (temp_path / "b_dir" / "file2.txt").write_text("content")
    (temp_path / "b_dir" / "file3.py").write_text("content")
    (temp_path / "b_dir" / "file4.md").write_text("content")

    # Empty directory
    (temp_path / "c_empty_dir").mkdir()

    # Symlink pointing outside the sandbox (to test security)
    symlink_temp_dir = tempfile.mkdtemp()
    symlink_temp_path = Path(symlink_temp_dir)
    try:
        (temp_path / "external_symlink").symlink_to(symlink_temp_path.relative_to(temp_path, walk_up=True))

        (symlink_temp_path / "external.txt").write_text("content")
    except (OSError, NotImplementedError):
        # Skip symlink creation if not supported (e.g., Windows without admin)
        pass

    fs = BasePathFS(temp_path)
    yield fs

    # Clean up
    import shutil

    shutil.rmtree(temp_dir)
    shutil.rmtree(symlink_temp_dir)


class TestListDir:
    """Snapshot-style tests for list_dir functionality.

    These tests focus on the exact output format to catch nesting and ordering issues.
    """

    def test_full_listing(self, test_fs: BasePathFS) -> None:
        """Test 1: Complete directory listing with depth-first ordering and proper nesting."""
        result = list_dir(test_fs, ".")

        expected = """- a_dir/
  - a_subdir/
    - another_deep.txt
    - deep_file.txt
  - a_file.txt
  - b_file.py
- b_dir/
  - file1.txt
  - file2.txt
  - file3.py
  - file4.md
- c_empty_dir/
- d_file.txt
- e_file.py
- f_file.md"""

        assert result == expected

    def test_truncated_listing(self, test_fs: BasePathFS) -> None:
        """Test 2: Truncated listing prioritizes breadth-first when hitting limits."""
        result = list_dir(test_fs, ".", max_entries=9)

        expected = """- a_dir/
  - a_subdir/
    ... 2 more entries not shown. Use 'list_dir a_dir/a_subdir' to see more.
  - a_file.txt
  ... 1 more entries not shown. Use 'list_dir a_dir' to see more.
- b_dir/
  - file1.txt
  ... 3 more entries not shown. Use 'list_dir b_dir' to see more.
- c_empty_dir/
- d_file.txt
- e_file.py
- f_file.md"""

        assert result == expected

    def test_ignore_globs_filtering(self, test_fs: BasePathFS) -> None:
        """Test 3: Directory listing with glob patterns excludes matching files."""
        result = list_dir(test_fs, ".", ignore_globs=["*.py"])

        expected = """- a_dir/
  - a_subdir/
    - another_deep.txt
    - deep_file.txt
  - a_file.txt
- b_dir/
  - file1.txt
  - file2.txt
  - file4.md
- c_empty_dir/
- d_file.txt
- f_file.md"""

        assert result == expected

    def test_show_hidden_files(self, test_fs: BasePathFS) -> None:
        """Test 4: Directory listing includes hidden files when show_hidden=True."""
        result = list_dir(test_fs, ".", show_hidden=True)

        expected = """- .hidden_dir/
  - hidden_content.txt
- a_dir/
  - a_subdir/
    - another_deep.txt
    - deep_file.txt
  - a_file.txt
  - b_file.py
- b_dir/
  - file1.txt
  - file2.txt
  - file3.py
  - file4.md
- c_empty_dir/
- .hidden_file
- d_file.txt
- e_file.py
- f_file.md"""

        assert result == expected

    def test_empty_directory(self, test_fs: BasePathFS) -> None:
        """Test empty directory returns empty string."""
        result = list_dir(test_fs, "c_empty_dir")
        assert result == ""

    def test_nonexistent_path_raises_error(self, test_fs: BasePathFS) -> None:
        """Test error handling for nonexistent paths."""
        with pytest.raises(FileNotFoundError):
            list_dir(test_fs, "nonexistent")

    def test_file_path_raises_error(self, test_fs: BasePathFS) -> None:
        """Test error handling when trying to list a file instead of directory."""
        with pytest.raises(NotADirectoryError):
            list_dir(test_fs, "d_file.txt")

    def test_cannot_escape_basepath_sandbox(self, test_fs: BasePathFS) -> None:
        """Test that list_dir cannot escape the BasePathFS sandbox using path traversal."""
        # Try various path traversal attempts that should be blocked by BasePathFS
        with pytest.raises((PermissionError, ValueError)):
            list_dir(test_fs, "../")

        with pytest.raises((PermissionError, ValueError)):
            list_dir(test_fs, "../../")

        with pytest.raises((PermissionError, ValueError)):
            list_dir(test_fs, "../../../etc")

        with pytest.raises((PermissionError, ValueError)):
            list_dir(test_fs, "/etc")

        with pytest.raises((PermissionError, ValueError)):
            list_dir(test_fs, "a_subdir/../../../etc")

    def test_symlink_does_not_escape_sandbox(self, test_fs: BasePathFS) -> None:
        """Test that symlinks pointing outside the sandbox are not followed."""

        result = list_dir(test_fs, ".", max_entries=100)
        assert "external" not in result
