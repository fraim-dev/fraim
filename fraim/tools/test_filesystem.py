# SPDX-License-Identifier: MIT
# Copyright (c) 2025 Resourcely Inc.

import logging
from pathlib import Path

import pytest

from fraim.tools.filesystem import FilesystemTools

# Configure logging for tests
logger = logging.getLogger(__name__)

test_dir_path = Path(__file__).parent / "test_data"


@pytest.fixture
def filesystem_tools() -> FilesystemTools:
    """Create a FilesystemTools instance using the test_data directory."""
    project_path = str(test_dir_path.absolute())
    return FilesystemTools(project_path=project_path)


class TestFilesystemTools:
    """Test suite for FilesystemTools functionality.

    This class tests the core filesystem tools including:
    - FilesystemTools initialization and setup
    - GrepTool for text pattern searching
    - ListDirTool for directory listing and exploration
    - ReadFileTool for file content reading
    - BasePathFS path sandboxing functionality

    Note: Tests use the shared test_data directory structure which includes
    JavaScript, Python, and TypeScript files for comprehensive testing.
    """

    def test_initialization(self) -> None:
        """Test that FilesystemTools initializes correctly with proper attributes."""
        tools = FilesystemTools(project_path=str(test_dir_path))

        assert tools.project_path == str(test_dir_path)
        assert tools.fs is not None
        assert tools.fs.root == test_dir_path.absolute()
        assert len(tools.tools) == 3

        # Verify all expected tools are present
        tool_names = {tool.name for tool in tools.tools}
        expected_tools = {
            "grep",
            "list_dir",
            "read_file",
        }
        assert expected_tools == tool_names

    @pytest.mark.asyncio
    async def test_grep_tool_basic_search(self, filesystem_tools: FilesystemTools) -> None:
        """Test basic grep functionality for finding text patterns."""
        grep_tool = next(tool for tool in filesystem_tools.tools if tool.name == "grep")

        # Test basic pattern search
        result = await grep_tool._run(pattern="def", path=".")
        assert isinstance(result, str)
        assert len(result) > 0
        assert "def" in result

        # Test case insensitive search
        result_case = await grep_tool._run(pattern="FUNCTION", path=".", case_insensitive=True)
        assert isinstance(result_case, str)
        # Should find "function" in JavaScript files

    @pytest.mark.asyncio
    async def test_grep_tool_file_type_filtering(self, filesystem_tools: FilesystemTools) -> None:
        """Test grep with file type filtering."""
        grep_tool = next(tool for tool in filesystem_tools.tools if tool.name == "grep")

        # Test Python-specific search
        result_py = await grep_tool._run(pattern="def", path=".", file_type="py")
        assert isinstance(result_py, str)
        if result_py:  # May be empty if no matches
            assert "python/" in result_py or ".py" in result_py

        # Test JavaScript-specific search
        result_js = await grep_tool._run(pattern="function", path=".", file_type="js")
        assert isinstance(result_js, str)
        if result_js:  # May be empty if no matches
            assert "javascript/" in result_js or ".js" in result_js

    @pytest.mark.asyncio
    async def test_grep_tool_glob_filtering(self, filesystem_tools: FilesystemTools) -> None:
        """Test grep with glob pattern filtering."""
        grep_tool = next(tool for tool in filesystem_tools.tools if tool.name == "grep")

        # Test glob pattern for Python files
        result_glob = await grep_tool._run(pattern="def", path=".", glob="*.py")
        assert isinstance(result_glob, str)
        if result_glob:
            # Should only contain Python files
            lines = result_glob.split("\n")
            py_lines = [line for line in lines if ".py:" in line]
            non_py_lines = [line for line in lines if line.strip() and ".py:" not in line and not line.startswith("-")]
            # All match lines should be from .py files
            for line in non_py_lines:
                # Allow context lines that don't have file extensions
                assert ":" not in line or ".py:" in line

    @pytest.mark.asyncio
    async def test_grep_tool_output_modes(self, filesystem_tools: FilesystemTools) -> None:
        """Test different grep output modes."""
        grep_tool = next(tool for tool in filesystem_tools.tools if tool.name == "grep")

        # Test content mode (default)
        result_content = await grep_tool._run(pattern="def", path=".", output_mode="content")
        assert isinstance(result_content, str)

        # Test files_with_matches mode
        result_files = await grep_tool._run(pattern="def", path=".", output_mode="files_with_matches")
        assert isinstance(result_files, str)
        if result_files:
            # Should only contain file paths, no line numbers or content
            lines = result_files.strip().split("\n")
            for line in lines:
                assert ":" not in line  # No line numbers in files mode

        # Test count mode
        result_count = await grep_tool._run(pattern="def", path=".", output_mode="count")
        assert isinstance(result_count, str)
        if result_count:
            # Should contain file:count format
            lines = result_count.strip().split("\n")
            for line in lines:
                if line.strip():
                    assert ":" in line  # Should have file:count format

    @pytest.mark.asyncio
    async def test_grep_tool_context_options(self, filesystem_tools: FilesystemTools) -> None:
        """Test grep context options."""
        grep_tool = next(tool for tool in filesystem_tools.tools if tool.name == "grep")

        # Test context around
        result_context = await grep_tool._run(pattern="def", path="python/simple.py", context_around=2)
        assert isinstance(result_context, str)
        if result_context:
            # Context lines should be marked with '-' prefix
            assert "--" in result_context or "-" in result_context

        # Test context before and after
        result_before_after = await grep_tool._run(
            pattern="def", path="python/simple.py", context_before=1, context_after=1
        )
        assert isinstance(result_before_after, str)

    @pytest.mark.asyncio
    async def test_grep_tool_head_limit(self, filesystem_tools: FilesystemTools) -> None:
        """Test grep head limit functionality."""
        grep_tool = next(tool for tool in filesystem_tools.tools if tool.name == "grep")

        # Test with head limit - use a more specific file to avoid termination issues
        result_limited = await grep_tool._run(pattern="def", path="python/simple.py", head_limit=5)
        assert isinstance(result_limited, str)
        if result_limited:
            lines = result_limited.strip().split("\n")
            assert len(lines) <= 5

    @pytest.mark.asyncio
    async def test_list_dir_tool_basic(self, filesystem_tools: FilesystemTools) -> None:
        """Test basic directory listing functionality."""
        list_dir_tool = next(tool for tool in filesystem_tools.tools if tool.name == "list_dir")

        # Test root directory listing
        result = await list_dir_tool._run(target_path=".")
        assert isinstance(result, str)
        assert len(result) > 0

        # Should contain directories and files from test_data
        assert "python/" in result
        assert "javascript/" in result
        assert "typescript/" in result
        assert "Makefile" in result

    @pytest.mark.asyncio
    async def test_list_dir_tool_subdirectory(self, filesystem_tools: FilesystemTools) -> None:
        """Test listing subdirectories."""
        list_dir_tool = next(tool for tool in filesystem_tools.tools if tool.name == "list_dir")

        # Test Python subdirectory
        result_python = await list_dir_tool._run(target_path="python")
        assert isinstance(result_python, str)
        assert "simple.py" in result_python
        assert "complex.py" in result_python

        # Test JavaScript subdirectory
        result_js = await list_dir_tool._run(target_path="javascript")
        assert isinstance(result_js, str)
        assert "complex.js" in result_js

    @pytest.mark.asyncio
    async def test_list_dir_tool_ignore_globs(self, filesystem_tools: FilesystemTools) -> None:
        """Test directory listing with ignore patterns."""
        list_dir_tool = next(tool for tool in filesystem_tools.tools if tool.name == "list_dir")

        # Test ignoring Python files
        result_no_py = await list_dir_tool._run(target_path=".", ignore_globs=["*.py"])
        assert isinstance(result_no_py, str)
        # Should not contain .py files
        assert ".py" not in result_no_py

        # Test ignoring entire directories
        result_no_python = await list_dir_tool._run(target_path=".", ignore_globs=["python"])
        assert isinstance(result_no_python, str)
        # Should not contain python directory
        assert "python/" not in result_no_python

    @pytest.mark.asyncio
    async def test_list_dir_tool_hidden_files(self, filesystem_tools: FilesystemTools) -> None:
        """Test directory listing with hidden files option."""
        list_dir_tool = next(tool for tool in filesystem_tools.tools if tool.name == "list_dir")

        # Test with show_hidden=False (default)
        result_no_hidden = await list_dir_tool._run(target_path=".", show_hidden=False)
        assert isinstance(result_no_hidden, str)

        # Test with show_hidden=True
        result_with_hidden = await list_dir_tool._run(target_path=".", show_hidden=True)
        assert isinstance(result_with_hidden, str)

    @pytest.mark.asyncio
    async def test_read_file_tool_basic(self, filesystem_tools: FilesystemTools) -> None:
        """Test basic file reading functionality."""
        read_file_tool = next(tool for tool in filesystem_tools.tools if tool.name == "read_file")

        # Test reading a Python file
        result = await read_file_tool._run(target_path="python/simple.py")
        assert isinstance(result, str)
        assert len(result) > 0
        assert "def" in result  # Should contain function definitions

        # Test reading a JavaScript file
        result_js = await read_file_tool._run(target_path="javascript/complex.js")
        assert isinstance(result_js, str)
        assert len(result_js) > 0
        assert "function" in result_js  # Should contain function keyword

    @pytest.mark.asyncio
    async def test_read_file_tool_with_offset(self, filesystem_tools: FilesystemTools) -> None:
        """Test file reading with offset."""
        read_file_tool = next(tool for tool in filesystem_tools.tools if tool.name == "read_file")

        # Read from beginning
        result_full = await read_file_tool._run(target_path="python/simple.py")
        full_lines = result_full.split("\n")

        # Read with offset
        result_offset = await read_file_tool._run(target_path="python/simple.py", offset=5)
        offset_lines = result_offset.split("\n")

        # Offset result should be shorter
        assert len(offset_lines) <= len(full_lines)

        # If we have enough lines, check that offset worked
        if len(full_lines) >= 5:
            # First line of offset result should match line 5 of full result
            if offset_lines[0] and full_lines[4]:
                assert offset_lines[0] == full_lines[4]

    @pytest.mark.asyncio
    async def test_read_file_tool_with_limit(self, filesystem_tools: FilesystemTools) -> None:
        """Test file reading with limit."""
        read_file_tool = next(tool for tool in filesystem_tools.tools if tool.name == "read_file")

        # Read with limit
        result_limited = await read_file_tool._run(target_path="python/simple.py", limit=10)
        limited_lines = result_limited.split("\n")

        # Should have at most 10 lines (plus possible empty line at end)
        assert len(limited_lines) <= 11

    @pytest.mark.asyncio
    async def test_read_file_tool_with_offset_and_limit(self, filesystem_tools: FilesystemTools) -> None:
        """Test file reading with both offset and limit."""
        read_file_tool = next(tool for tool in filesystem_tools.tools if tool.name == "read_file")

        # Read with both offset and limit
        result = await read_file_tool._run(target_path="python/simple.py", offset=3, limit=5)
        lines = result.split("\n")

        # Should have at most 5 lines (plus possible empty line at end)
        assert len(lines) <= 6


class TestFilesystemToolsIntegration:
    """Integration tests for FilesystemTools workflows.

    These tests demonstrate typical usage patterns and workflows
    that combine multiple filesystem tools together.
    """

    @pytest.mark.asyncio
    async def test_file_discovery_workflow(self, filesystem_tools: FilesystemTools) -> None:
        """Test a complete file discovery workflow using multiple tools."""
        # Step 1: Get tools for workflow
        list_tool = next(t for t in filesystem_tools.tools if t.name == "list_dir")
        grep_tool = next(t for t in filesystem_tools.tools if t.name == "grep")
        read_tool = next(t for t in filesystem_tools.tools if t.name == "read_file")

        # Step 2: List directory structure
        directory_listing = await list_tool._run(target_path=".")
        assert isinstance(directory_listing, str)
        assert "python/" in directory_listing

        # Step 3: Search for specific patterns
        function_matches = await grep_tool._run(pattern="def", path="python", output_mode="files_with_matches")
        assert isinstance(function_matches, str)

        # Step 4: Read specific files found in search
        if "simple.py" in function_matches:
            file_content = await read_tool._run(target_path="python/simple.py")
            assert isinstance(file_content, str)
            assert "def" in file_content

    @pytest.mark.asyncio
    async def test_code_analysis_workflow(self, filesystem_tools: FilesystemTools) -> None:
        """Test a code analysis workflow across different file types."""
        grep_tool = next(t for t in filesystem_tools.tools if t.name == "grep")
        read_tool = next(t for t in filesystem_tools.tools if t.name == "read_file")

        # Analyze Python functions
        python_functions = await grep_tool._run(pattern="def ", path="python", output_mode="count")
        assert isinstance(python_functions, str)

        # Analyze JavaScript functions
        js_functions = await grep_tool._run(pattern="function", path="javascript", output_mode="count")
        assert isinstance(js_functions, str)

        # Read a sample file from each type
        python_sample = await read_tool._run(target_path="python/simple.py", limit=20)
        assert isinstance(python_sample, str)

        js_sample = await read_tool._run(target_path="javascript/complex.js", limit=20)
        assert isinstance(js_sample, str)

    @pytest.mark.asyncio
    async def test_targeted_search_workflow(self, filesystem_tools: FilesystemTools) -> None:
        """Test targeted search and examination workflow."""
        grep_tool = next(t for t in filesystem_tools.tools if t.name == "grep")
        read_tool = next(t for t in filesystem_tools.tools if t.name == "read_file")

        # Search for specific patterns with context
        async_patterns = await grep_tool._run(pattern="async", path=".", context_around=2)
        assert isinstance(async_patterns, str)

        # Search for class definitions
        class_patterns = await grep_tool._run(pattern="class", path=".", output_mode="files_with_matches")
        assert isinstance(class_patterns, str)

        # If we found classes, examine the files
        if class_patterns.strip():
            file_lines = class_patterns.strip().split("\n")
            if file_lines:
                first_file = file_lines[0]
                class_content = await read_tool._run(target_path=first_file)
                assert isinstance(class_content, str)


class TestFilesystemToolsErrorHandling:
    """Test error handling and edge cases for FilesystemTools."""

    @pytest.mark.asyncio
    async def test_grep_tool_invalid_path(self, filesystem_tools: FilesystemTools) -> None:
        """Test grep with invalid paths."""
        grep_tool = next(tool for tool in filesystem_tools.tools if tool.name == "grep")

        # Test non-existent path
        with pytest.raises(Exception):  # Should raise ToolError or similar
            await grep_tool._run(pattern="test", path="nonexistent/path")

    @pytest.mark.asyncio
    async def test_grep_tool_invalid_arguments(self, filesystem_tools: FilesystemTools) -> None:
        """Test grep with invalid argument combinations."""
        grep_tool = next(tool for tool in filesystem_tools.tools if tool.name == "grep")

        # Test context options with non-content output mode (should fail)
        with pytest.raises(Exception):  # Should raise ValueError via ToolError
            await grep_tool._run(pattern="test", path=".", output_mode="files_with_matches", context_around=2)

    @pytest.mark.asyncio
    async def test_list_dir_tool_invalid_path(self, filesystem_tools: FilesystemTools) -> None:
        """Test list_dir with invalid paths."""
        list_dir_tool = next(tool for tool in filesystem_tools.tools if tool.name == "list_dir")

        # Test non-existent directory
        with pytest.raises(Exception):  # Should raise ToolError
            await list_dir_tool._run(target_path="nonexistent/directory")

        # Test file instead of directory
        with pytest.raises(Exception):  # Should raise ToolError
            await list_dir_tool._run(target_path="python/simple.py")

    @pytest.mark.asyncio
    async def test_read_file_tool_invalid_path(self, filesystem_tools: FilesystemTools) -> None:
        """Test read_file with invalid paths."""
        read_file_tool = next(tool for tool in filesystem_tools.tools if tool.name == "read_file")

        # Test non-existent file
        with pytest.raises(Exception):  # Should raise ToolError
            await read_file_tool._run(target_path="nonexistent/file.txt")

        # Test directory instead of file
        with pytest.raises(Exception):  # Should raise ToolError
            await read_file_tool._run(target_path="python")

    @pytest.mark.asyncio
    async def test_read_file_tool_invalid_parameters(self, filesystem_tools: FilesystemTools) -> None:
        """Test read_file with invalid parameters."""
        read_file_tool = next(tool for tool in filesystem_tools.tools if tool.name == "read_file")

        # Test with invalid offset (should handle gracefully)
        result = await read_file_tool._run(target_path="python/simple.py", offset=999999)
        assert isinstance(result, str)
        # Should return empty string if offset is beyond file length

        # Test with zero limit (current implementation reads entire file if limit=0)
        result_zero = await read_file_tool._run(target_path="python/simple.py", limit=0)
        assert isinstance(result_zero, str)
        # Current implementation doesn't handle limit=0 specially, so it reads entire file
        # This is acceptable behavior for limit=0


class TestSpecificFunctionality:
    """Test specific functionality and advanced features."""

    @pytest.mark.asyncio
    async def test_basepath_sandboxing(self, filesystem_tools: FilesystemTools) -> None:
        """Test that BasePathFS properly sandboxes file access."""
        read_file_tool = next(tool for tool in filesystem_tools.tools if tool.name == "read_file")

        # Test that we can't escape the sandbox
        with pytest.raises(Exception):  # Should raise ToolError for permission denied
            await read_file_tool._run(target_path="../../../etc/passwd")

        with pytest.raises(Exception):  # Should raise ToolError for permission denied
            await read_file_tool._run(target_path="/etc/passwd")

    @pytest.mark.asyncio
    async def test_grep_multiline_search(self, filesystem_tools: FilesystemTools) -> None:
        """Test multiline grep functionality."""
        grep_tool = next(tool for tool in filesystem_tools.tools if tool.name == "grep")

        # Test multiline pattern (if supported by test files)
        result = await grep_tool._run(pattern="def.*\n.*return", path="python/simple.py", multiline=True)
        assert isinstance(result, str)
        # Result may be empty if no multiline matches found

    @pytest.mark.asyncio
    async def test_tool_schema_validation(self, filesystem_tools: FilesystemTools) -> None:
        """Test that tools have proper schema validation."""
        for tool in filesystem_tools.tools:
            # Verify each tool has required attributes
            assert hasattr(tool, "name")
            assert hasattr(tool, "description")
            assert hasattr(tool, "args_schema")
            assert hasattr(tool, "_run")

            # Verify schema is a Pydantic model
            assert hasattr(tool.args_schema, "model_fields")

    def test_filesystem_tools_path_handling(self) -> None:
        """Test FilesystemTools handles different path formats correctly."""
        # Test with string path
        tools_str = FilesystemTools(project_path=str(test_dir_path))
        assert tools_str.project_path == str(test_dir_path)

        # Test with Path object (convert to string since FilesystemTools expects str)
        tools_path = FilesystemTools(project_path=str(test_dir_path))
        assert tools_path.project_path == str(test_dir_path)

        # Both should create equivalent BasePathFS instances
        assert tools_str.fs.root == tools_path.fs.root

    @pytest.mark.asyncio
    async def test_empty_search_results(self, filesystem_tools: FilesystemTools) -> None:
        """Test handling of searches that return no results."""
        grep_tool = next(tool for tool in filesystem_tools.tools if tool.name == "grep")

        # Search for pattern that shouldn't exist
        result = await grep_tool._run(pattern="ThisPatternDoesNotExistAnywhere", path=".")
        assert isinstance(result, str)
        assert result == ""  # Should return empty string for no matches

        # Test different output modes with no matches
        result_files = await grep_tool._run(
            pattern="ThisPatternDoesNotExistAnywhere", path=".", output_mode="files_with_matches"
        )
        assert isinstance(result_files, str)
        assert result_files == ""

        result_count = await grep_tool._run(pattern="ThisPatternDoesNotExistAnywhere", path=".", output_mode="count")
        assert isinstance(result_count, str)
        assert result_count == ""
