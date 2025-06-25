# SPDX-License-Identifier: MIT
# Copyright (c) 2025 Resourcely Inc.

import logging
import uuid
from pathlib import Path

import pytest

from fraim.tools.tree_sitter import TreeSitterTools

# Configure logging for tests
logger = logging.getLogger(__name__)

test_dir_path = Path(__file__).parent / "test_data"


@pytest.fixture
def tree_sitter_tools() -> TreeSitterTools:
    """Create a TreeSitterTools instance using the test_data directory."""

    # Generate unique project name to avoid conflicts in global registry
    unique_project_name = f"test_project_{uuid.uuid4().hex[:8]}"

    project_path = str(test_dir_path.absolute())

    return TreeSitterTools(project_path=project_path, project_name=unique_project_name)


class TestTreeSitterTools:
    """Test suite for TreeSitterTools functionality.

    This class tests the core TreeSitter tools including:
    - Project initialization and setup
    - File listing and discovery
    - File content reading
    - AST (Abstract Syntax Tree) generation
    - Function definition finding
    - Text searching
    - Code querying with TreeSitter patterns

    Note: Tests can fail if TreeSitterTools are not initialized with a correctly scoped project path.
    This scaffolding demonstrates the proper structure and usage patterns that will not error.
    """

    def test_initialization(self) -> None:
        """Test that TreeSitterTools initializes correctly with proper attributes."""
        # Test with a simple path
        tools = TreeSitterTools(project_path=str(test_dir_path), project_name=f"init_test_{uuid.uuid4().hex[:8]}")

        assert tools.project_path is not None
        assert tools.project_name.startswith("init_test_")
        assert tools.project is not None
        assert len(tools.tools) > 0

        # Verify all expected tools are present
        tool_names = {tool.name for tool in tools.tools}
        expected_tools = {
            "list_files",
            "get_file_content",
            "get_file_ast",
            "get_ast_node_at_position",
            "find_symbol_usage",
            "find_function_definition",
            "query_code",
            "search_text",
        }
        assert expected_tools.issubset(tool_names)

    @pytest.mark.asyncio
    async def test_list_files_tool(self, tree_sitter_tools: TreeSitterTools) -> None:
        """Test the list_files tool for project file discovery."""
        list_files_tool = next(tool for tool in tree_sitter_tools.tools if tool.name == "list_files")

        # Test basic file listing with total number of files
        result = await list_files_tool._run()
        assert isinstance(result, list)
        assert len(result) == 5

        # Test with file extension filtering to get only python files
        result_py = await list_files_tool._run(filter_extensions=["py"])
        assert isinstance(result_py, list)
        assert len(result_py) == 2

    @pytest.mark.asyncio
    async def test_get_file_content_tool_basic(self, tree_sitter_tools: TreeSitterTools) -> None:
        """Test basic functionality of get_file_content tool."""
        get_content_tool = next(tool for tool in tree_sitter_tools.tools if tool.name == "get_file_content")

        # Test that the tool exists and can be called
        assert get_content_tool is not None
        assert hasattr(get_content_tool, "_run")

        # Test that the tool can get the content of a file
        result = await get_content_tool._run(path=str(test_dir_path / "python/simple.py"))
        assert isinstance(result, str)
        assert len(result) > 0

    @pytest.mark.asyncio
    async def test_search_text_tool(self, tree_sitter_tools: TreeSitterTools) -> None:
        """Test the search_text tool for finding text patterns."""
        search_tool = next(tool for tool in tree_sitter_tools.tools if tool.name == "search_text")

        # Test basic search functionality
        assert search_tool is not None
        assert hasattr(search_tool, "_run")

        # Test search for a common pattern
        try:
            result = await search_tool._run(pattern="def")
            assert isinstance(result, list)
            assert len(result) == 35
        except Exception as e:
            pytest.fail(f"test_search_text_tool failed due to exception: {e}")

    @pytest.mark.asyncio
    async def test_query_code_tool_structure(self, tree_sitter_tools: TreeSitterTools) -> None:
        """Test the query_code tool structure and basic functionality."""
        query_tool = next(tool for tool in tree_sitter_tools.tools if tool.name == "query_code")

        assert query_tool is not None
        assert hasattr(query_tool, "_run")

        # Test with a basic TreeSitter query
        function_query = """
        (function_definition
          name: (identifier) @function.name
        )
        """

        try:
            result = await query_tool._run(
                query=function_query, path=str(test_dir_path / "python/simple.py"), language="python"
            )
            assert isinstance(result, list)
            # 9 functions in ./test_data/python/simple.py
            assert len(result) == 9
        except Exception as e:
            pytest.fail(f"test_query_code_tool_structure failed due to exception: {e}")


class TestTreeSitterToolsIntegration:
    """Integration tests for TreeSitterTools workflows.

    These tests demonstrate typical usage patterns and workflows
    that combine multiple TreeSitter tools together.
    """

    @pytest.mark.asyncio
    async def test_code_analysis_workflow(self, tree_sitter_tools: TreeSitterTools) -> None:
        """Test a complete code analysis workflow using multiple tools."""
        # Step 1: Discover available tools
        tool_names = [tool.name for tool in tree_sitter_tools.tools]
        assert "list_files" in tool_names
        assert "search_text" in tool_names
        assert "query_code" in tool_names

        # Step 2: Get tools for workflow
        list_tool = next(t for t in tree_sitter_tools.tools if t.name == "list_files")
        search_tool = next(t for t in tree_sitter_tools.tools if t.name == "search_text")

        # Step 3: Execute workflow steps
        try:
            # List files in project
            files = await list_tool._run()
            assert isinstance(files, list)

            # Search for Python function definitions
            python_functions = await search_tool._run(pattern="def ")
            assert isinstance(python_functions, list)

        except Exception as e:
            pytest.fail(f"test_code_analysis_workflow failed due to exception: {e}")

    @pytest.mark.asyncio
    async def test_ast_analysis_workflow(self, tree_sitter_tools: TreeSitterTools) -> None:
        """Test AST-based code analysis workflow."""
        # Get AST-related tools
        ast_tools = {
            tool.name: tool
            for tool in tree_sitter_tools.tools
            if tool.name in ["get_file_ast", "get_ast_node_at_position", "query_code"]
        }

        # Verify all AST tools are available
        assert "get_file_ast" in ast_tools
        assert "get_ast_node_at_position" in ast_tools
        assert "query_code" in ast_tools

        # Test AST workflow structure
        ast_tool = ast_tools["get_file_ast"]
        query_tool = ast_tools["query_code"]

        assert hasattr(ast_tool, "_run")
        assert hasattr(query_tool, "_run")


class TestTreeSitterQueries:
    """Test TreeSitter query patterns and syntax.

    This class demonstrates various TreeSitter query patterns
    that can be used for code analysis and pattern matching.
    """

    @pytest.mark.asyncio
    async def test_function_query_patterns(self, tree_sitter_tools: TreeSitterTools) -> None:
        """Test various function definition query patterns and query_tool execution."""
        query_tool = next(tool for tool in tree_sitter_tools.tools if tool.name == "query_code")

        # Basic function definition query
        basic_function_query = """
        (function_definition
          name: (identifier) @function.name
        )
        """

        # Function with parameters query
        function_with_params_query = """
        (function_definition
          name: (identifier) @function.name
          parameters: (parameters) @function.params
        )
        """

        # Function with docstring query
        function_with_docstring_query = """
        (function_definition
          name: (identifier) @function.name
          body: (block
            (expression_statement
              (string) @function.docstring
            )*
          )
        )
        """

        queriesWithExpectedResults = [
            {"query": basic_function_query, "number_of_results": 20},
            {"query": function_with_params_query, "number_of_results": 40},
            {"query": function_with_docstring_query, "number_of_results": 32},
        ]
        for query in queriesWithExpectedResults:
            # Actually test the query_tool by running it on a Python file in the project
            # We'll use the first Python file found in the project for demonstration
            file_path = str(test_dir_path / "python/complex.py")
            result = await query_tool._run(query=query["query"], path=file_path, language="python", max_results=50)

            # The result should be a non-empty list
            assert isinstance(result, list)
            assert len(result) == query["number_of_results"]

    @pytest.mark.asyncio
    async def test_class_query_patterns(self, tree_sitter_tools: TreeSitterTools) -> None:
        """Test class definition query patterns."""
        query_tool = next(tool for tool in tree_sitter_tools.tools if tool.name == "query_code")

        # Basic class query
        class_query = """
        (class_definition
          name: (identifier) @class.name
        )
        """

        # Class with inheritance query
        class_inheritance_query = """
        (class_definition
          name: (identifier) @class.name
          superclasses: (argument_list) @class.bases
        )
        """

        file_path = str(test_dir_path / "python/complex.py")

        # Test basic class query
        result_basic = await query_tool._run(query=class_query, path=file_path, language="python", max_results=50)
        assert isinstance(result_basic, list)
        assert len(result_basic) == 3

        # Test class with inheritance query
        result_inheritance = await query_tool._run(
            query=class_inheritance_query, path=file_path, language="python", max_results=50
        )
        assert isinstance(result_inheritance, list)
        assert len(result_inheritance) == 2


class TestSpecificFunctionality:
    """Test specific TreeSitter functionality and edge cases."""

    def _verify_expected_lines_in_order(self, result_lines: list[str], expected_lines: list[str]) -> None:
        """Helper method to verify that expected lines appear in order within result lines.

        Args:
            result_lines: List of lines from the result text
            expected_lines: List of expected lines that should appear in order
        """
        last_found = -1
        for expected in expected_lines:
            found = False
            for idx, line in enumerate(result_lines):
                if idx > last_found and expected.strip() in line.strip():
                    last_found = idx
                    found = True
                    break
            assert found, f"Expected line not found or out of order: {expected}"

    @pytest.mark.asyncio
    async def test_symbol_usage_patterns(self, tree_sitter_tools: TreeSitterTools) -> None:
        """Test finding symbol usage patterns."""
        find_symbol_tool = next(tool for tool in tree_sitter_tools.tools if tool.name == "find_symbol_usage")

        assert find_symbol_tool is not None
        assert hasattr(find_symbol_tool, "_run")

        # Test tool parameter structure
        try:
            result = await find_symbol_tool._run(
                symbol="hello_world", path=str(test_dir_path / "python/simple.py"), language="python", max_results=50
            )
            assert len(result) == 2
        except Exception as e:
            pytest.fail(f"test_symbol_usage_patterns failed due to exception: {e}")

    @pytest.mark.asyncio
    async def test_ast_node_positioning(self, tree_sitter_tools: TreeSitterTools) -> None:
        """Test AST node positioning functionality."""
        ast_position_tool = next(tool for tool in tree_sitter_tools.tools if tool.name == "get_ast_node_at_position")

        assert ast_position_tool is not None
        assert hasattr(ast_position_tool, "_run")

        # Test parameter structure for position-based queries
        try:
            result = await ast_position_tool._run(
                path=str(test_dir_path / "python/simple.py"), row=5, column=0, max_depth=3
            )
            assert isinstance(result, dict)
        except Exception as e:
            pytest.fail(f"test_ast_node_positioning failed due to exception: {e}")

    @pytest.mark.asyncio
    async def test_find_function_definition_with_snippets(self, tree_sitter_tools: TreeSitterTools) -> None:
        """Test that find_function_definition includes code snippets in results."""
        # Get the find_function_definition tool
        find_function_tool = next(tool for tool in tree_sitter_tools.tools if tool.name == "find_function_definition")

        assert find_function_tool is not None
        assert hasattr(find_function_tool, "_run")

        # Test with a simple function that has a docstring and body
        try:
            results = await find_function_tool._run(name="greet_person", language="python")

            assert len(results) == 1

            result = results[0]

            assert "file" in result, "Result missing 'file' field"
            assert "capture" in result, "Result missing 'capture' field"

            assert result["start"]["row"] == 18
            assert result["end"]["row"] == 20
            expected_lines = [
                'def greet_person(name, greeting="Hello"):',
                '    """Greet a person with optional greeting"""',
                '    return f"{greeting}, {name}!"',
            ]
            result_lines = result["text"].splitlines()
            self._verify_expected_lines_in_order(result_lines, expected_lines)

        except Exception as e:
            pytest.fail(f"test_find_function_definition_with_snippets failed due to exception: {e}")

    @pytest.mark.asyncio
    async def test_find_async_function_definition(self, tree_sitter_tools: TreeSitterTools) -> None:
        """Test finding an async function definition with type hints."""
        find_function_tool = next(tool for tool in tree_sitter_tools.tools if tool.name == "find_function_definition")

        assert find_function_tool is not None
        assert hasattr(find_function_tool, "_run")

        try:
            results = await find_function_tool._run(name="process_multiple_urls", language="python")

            assert len(results) == 1

            result = results[0]

            assert "file" in result, "Result missing 'file' field"
            assert "capture" in result, "Result missing 'capture' field"
            assert result["file"] == "python/complex.py"

            assert result["start"]["row"] == 75
            assert result["end"]["row"] == 79
            expected_lines = [
                "async def process_multiple_urls(urls: List[str]) -> List[Dict]:",
                '    """Process multiple URLs concurrently"""',
                "    tasks = [fetch_data(url) for url in urls]",
                "    results = await asyncio.gather(*tasks)",
                "    return results",
            ]
            result_lines = result["text"].splitlines()
            self._verify_expected_lines_in_order(result_lines, expected_lines)

        except Exception as e:
            pytest.fail(f"test_find_async_function_definition failed due to exception: {e}")

    @pytest.mark.asyncio
    async def test_find_typescript_function_definition(self, tree_sitter_tools: TreeSitterTools) -> None:
        """Test finding a TypeScript function definition with type annotations."""
        find_function_tool = next(tool for tool in tree_sitter_tools.tools if tool.name == "find_function_definition")

        assert find_function_tool is not None
        assert hasattr(find_function_tool, "_run")

        try:
            results = await find_function_tool._run(
                name="fetchUserById",
                language="typescript",
            )

            assert len(results) == 1

            result = results[0]

            assert "file" in result, "Result missing 'file' field"
            assert "capture" in result, "Result missing 'capture' field"
            assert result["file"] == "typescript/complex.ts"

            assert result["start"]["row"] == 19
            assert result["end"]["row"] == 26
            assert result["start"]["column"] == 0
            assert result["end"]["column"] == 1
            expected_lines = [
                "async function fetchUserById(id: number): Promise<User | null> {",
                "    // Simulate API call",
                "    return {",
                "        id,",
                '        name: "John Doe",',
                '        email: "john@example.com"',
                "    };",
                "}",
            ]
            result_lines = result["text"].splitlines()
            self._verify_expected_lines_in_order(result_lines, expected_lines)

        except Exception as e:
            pytest.fail(f"test_find_typescript_function_definition failed due to exception: {e}")

    @pytest.mark.asyncio
    async def test_find_javascript_function_definition(self, tree_sitter_tools: TreeSitterTools) -> None:
        """Test finding a JavaScript function definition."""
        find_function_tool = next(tool for tool in tree_sitter_tools.tools if tool.name == "find_function_definition")

        assert find_function_tool is not None
        assert hasattr(find_function_tool, "_run")

        try:
            results = await find_function_tool._run(
                name="fetchUserData",
                language="javascript",
            )

            assert len(results) == 1

            result = results[0]

            assert "file" in result, "Result missing 'file' field"
            assert "capture" in result, "Result missing 'capture' field"
            assert result["file"] == "javascript/complex.js"

            assert result["start"]["row"] == 20
            assert result["end"]["row"] == 31
            expected_lines = [
                "async function fetchUserData(userId) {",
                "    // Simulate API call",
                "    return {",
                "        id: userId,",
                '        name: "Jane Smith",',
                '        email: "jane@example.com",',
                "        preferences: {",
                '            theme: "dark",',
                "            notifications: true",
                "        }",
                "    };",
                "}",
            ]
            result_lines = result["text"].splitlines()
            self._verify_expected_lines_in_order(result_lines, expected_lines)

        except Exception as e:
            pytest.fail(f"test_find_javascript_function_definition failed due to exception: {e}")
