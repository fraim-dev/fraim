# SPDX-License-Identifier: MIT
# Copyright (c) 2025 Resourcely Inc.

from collections.abc import Callable, Iterator
from textwrap import dedent
from typing import Any, ClassVar, Optional, Self

from mcp_server_tree_sitter.api import (  # type: ignore[import-untyped]
    get_language_registry,
    get_project_registry,
    get_tree_cache,
    register_project,
)
from mcp_server_tree_sitter.exceptions import (  # type: ignore[import-untyped]
    FileAccessError,
    ProjectError,
    QueryError,
)
from mcp_server_tree_sitter.models.ast import (  # type: ignore[import-untyped]
    find_node_at_position,
    node_to_dict,
)
from mcp_server_tree_sitter.models.project import Project  # type: ignore[import-untyped]
from mcp_server_tree_sitter.tools.ast_operations import (  # type: ignore[import-untyped]
    get_file_ast,
    parse_file,
)
from mcp_server_tree_sitter.tools.file_operations import (  # type: ignore[import-untyped]
    get_file_content,
    list_project_files,
)
from mcp_server_tree_sitter.tools.search import (  # type: ignore[import-untyped]
    query_code,
    search_text,
)
from pydantic import BaseModel, Field, create_model

from fraim.core.tools import BaseTool, ToolError


class TreeSitterTools:
    """
    Direct interface to tree-sitter code analysis tools for project exploration and parsing.

    This class provides fraim-compatible tools that use the tree-sitter library to:
    - List and filter project files
    - Read file contents with optional line ranges
    - Generate Abstract Syntax Trees (ASTs) for code analysis

    Why direct integration instead of MCP server?
    - Custom tool descriptions and parameter handling for LLM agents
    - Automatic project registration eliminates manual setup steps
    - No external server process or binary dependencies required
    - Simplified deployment and configuration

    The tools automatically register the project with tree-sitter on initialization
    and provide a clean interface for AI agents to explore codebases.
    """

    def __init__(self, project_path: str, project_name: str | None = None):
        self.project_path = project_path
        self.project_name = project_name or project_path.split("/")[-1]

        try:
            self.project = get_project_registry().get_project(self.project_name)
        except ProjectError:
            # `register_project` returns a dict, not a Project instance
            register_project(
                path=self.project_path,
                name=self.project_name,
            )
            self.project = get_project_registry().get_project(self.project_name)

        self.tools: list[TreeSitterBaseTool] = [
            ListFilesTool.create(self.project),
            GetFileContentTool.create(self.project),
            GetFileAstTool.create(self.project),
            GetAstNodeAtPositionTool.create(self.project),
            FindSymbolUsageTool.create(self.project),
            FindFunctionDefinitionTool.create(self.project),
            QueryCodeTool.create(self.project),
            SearchTextTool.create(self.project),
        ]

    def __iter__(self) -> Iterator[BaseTool]:
        return iter(self.tools)


class TreeSitterBaseTool(BaseTool):
    """
    Base class for all tree-sitter tools.

    Automatically passes the project to the tool function.
    """

    tool_func: ClassVar[Callable[..., Any] | None] = None
    project: Project = Field(exclude=True)

    @classmethod
    def create(cls, project: Project, **kwargs: Any) -> Self:
        """
        Create a new instance of the tool.

        Args:
            project: The project object as registered with the mcp_server_tree_sitter library.
        """
        # Create instance with project stored in field
        instance = cls(project=project, **kwargs)

        # Use the tool function's docstring as the default description if not provided
        if hasattr(cls, "tool_func") and cls.tool_func and instance.description is None:
            instance.description = dedent(cls.tool_func.__doc__).strip()

        return instance

    async def _run(self, **kwargs: Any) -> Any:
        """
        Run the tool, passing the project to the tool function.
        """
        # Access tool_func from the class to avoid method binding
        tool_func = self.__class__.tool_func
        if tool_func is None:
            raise NotImplementedError("The `tool_func` attribute was not set.")

        try:
            return tool_func(self.project, **kwargs)
        except FileAccessError as e:
            raise ToolError(e) from e


class ListFilesTool(TreeSitterBaseTool):
    name: str = "list_files"
    tool_func = list_project_files
    description: str = dedent("""
                              List files and directories in the project to understand codebase structure.

                              Use this tool to as the first step in any code analysis to map out the project layout.
                              Use it to find files by location or type, explore specific directories, or verify existence of file.

                              Outputs a list of file paths relative to the project root.
                              """)
    args_schema: type[BaseModel] = create_model(
        "ListFilesArgs",
        pattern=(
            Optional[str],
            Field(
                default=None,
                description="A glob pattern for files to match. Use this to examine specific directories (e.g., 'src/**' or 'src/foo/*'). (optional)",
            ),
        ),
        max_depth=(
            Optional[int],
            Field(
                default=None,
                description="Returns files only up to this directory depth. 0 means root directory only. (optional)",
            ),
        ),
        filter_extensions=(
            Optional[list[str]],
            Field(
                default=None,
                description="Filter the files to those with these extensions (do not include the dot, e.g., ['py', 'js']). (optional)",
            ),
        ),
    )


class GetFileContentTool(TreeSitterBaseTool):
    name: str = "get_file_content"
    tool_func = get_file_content
    # TODO: Might be more useful to take an end_line argument instead of max_lines. The LLM may know the end line, but can't do the subtraction to convert.
    description: str = dedent("""
                              Read file contents to analyze code.

                              Use this tool after location files with the list_files tool. Read entire files unless
                              you know the exact lines needed. For large files, use start_line and max_lines to
                              read specific sections.

                              Outputs the contents of the file.
                              """)
    args_schema: type[BaseModel] = create_model(
        "GetFileArgs",
        path=(str, Field(description="The path to the file to read, relative to the project root.")),
        max_lines=(
            Optional[int],
            Field(default=None, description="The maximum number of lines to read. Defaults to all lines. (optional)"),
        ),
        start_line=(
            int,
            Field(default=0, description="The zero-indexed line number to start reading from (inclusive). (optional)"),
        ),
    )


class GetFileAstTool(TreeSitterBaseTool):
    name: str = "get_file_ast"
    tool_func = get_file_ast
    description: str = dedent("""
                              Generate Abstract Syntax Tree (AST) to analyze code structure and patterns.

                              Use this tool to understand function definitions, class hierarchies, imports, and code organization.
                              Essential for security analysis, refactoring, or understanding complex codebases.

                              Outputs structured tree data showing syntax elements, types, and relationships.
                              """)
    args_schema: type[BaseModel] = create_model(
        "GetFileAstArgs",
        path=(str, Field(description="The path to the file to parse, relative to the project root.")),
        max_depth=(
            Optional[int],
            Field(
                default=None, description="The maximum depth of the AST to return. 0 means root node only. (optional)"
            ),
        ),
    )

    async def _run(self, **kwargs: Any) -> Any:
        return get_file_ast(
            self.project, language_registry=get_language_registry(), tree_cache=get_tree_cache(), **kwargs
        )


class GetAstNodeAtPositionTool(TreeSitterBaseTool):
    name: str = "get_ast_node_at_position"
    description: str = dedent("""
                              Get the AST node at a specific line and column.

                              Use this tool to find the most specific AST node at a specific line and column in the file.

                              Outputs structured tree data for the most specific node at the position.
                              """)
    args_schema: type[BaseModel] = create_model(
        "GetAstNodeAtPositionArgs",
        path=(str, Field(description="The path to the file to parse, relative to the project root.")),
        row=(int, Field(description="The zero-indexed line number to start reading from (inclusive).")),
        column=(int, Field(description="The zero-indexed column number to start reading from (inclusive).")),
        max_depth=(
            Optional[int],
            Field(default=2, description="The maximum depth of the AST to return. 0 means root node only. (optional)"),
        ),
    )

    async def _run(self, **kwargs: Any) -> Any:
        path = kwargs["path"]
        row = kwargs["row"]
        column = kwargs["column"]
        max_depth = kwargs.get("max_depth", 2)

        file_path = self.project.get_file_path(path)

        language_registry = get_language_registry()
        language = language_registry.language_for_file(path)
        if not language:
            raise ToolError(f"No language found for file {path}")

        tree_cache = get_tree_cache()

        tree, source_bytes = parse_file(file_path, language, language_registry, tree_cache)

        node = find_node_at_position(tree.root_node, row, column)
        if not node:
            raise ToolError(f"No node found at position {row}:{column} in file {path}")

        return node_to_dict(node, source_bytes, max_depth)


class FindSymbolUsageTool(TreeSitterBaseTool):
    name: str = "find_symbol_usage"
    description: str = dedent("""
                              Find all usages of a symbol in the project.

                              Use this tool to determine where a function is called, where a variable is assigned etc.
                              Use as part of a series of tool calls to trace the flow data through a program
                              or to construct a call graph.

                              Outputs a list of locations where the symbol is used.
                              """)
    args_schema: type[BaseModel] = create_model(
        "FindSymbolUsageArgs",
        symbol=(str, Field(description="The symbol to find usages of.")),
        path=(
            Optional[str],
            Field(
                default=None, description="Restrict the search to a specific file. Useful for local symbols (optional)"
            ),
        ),
        language=(
            Optional[str],
            Field(
                default=None,
                description="Restrict the search to a specific language. If the project has multiple languages, you MUST specify the language. (optional)",
            ),
        ),
        max_results=(
            Optional[int],
            Field(default=100, description="The maximum number of results to return. (optional, default = 100)"),
        ),
    )

    async def _run(self, **kwargs: Any) -> Any:
        symbol = kwargs["symbol"]
        path = kwargs.get("path")
        language = kwargs.get("language")
        max_results = kwargs.get("max_results", 100)

        language_registry = get_language_registry()

        if not language:
            if path:
                language = language_registry.language_for_file(path)
            else:
                # Use the first language in the project as the default
                language = get_most_common_language(self.project)

        tree_cache = get_tree_cache()

        query = f"""
        (
          (identifier) @reference
          (#eq? @reference "{symbol}")
        )
        """

        try:
            return query_code(self.project, query, language_registry, tree_cache, path, language, max_results)
        except QueryError as e:
            raise ToolError(e) from e


class FindFunctionDefinitionTool(TreeSitterBaseTool):
    name: str = "find_function_definition"
    description: str = dedent("""
                              Find the definition of a function in the project.

                              Use this tool to find the definition of a function in the project.
                              This is useful for understanding the internal operation of a function.
                              Currently supports Python, TypeScript, and JavaScript. Other languages
                              may not work correctly.

                              Outputs the definition of the function with code snippets, including:
                              - Docstrings
                              - Parameters
                              - Full function body

                              Results include:
                              - File path
                              - Start and end positions (row/column)
                              - Full text of the function definition
                              - Capture information

                              Example output:
                              [
                                {
                                  "file": "python/complex.py",
                                  "start": {"row": 66, "column": 0},
                                  "end": {"row": 70, "column": 18},
                                  "text": "async def process_multiple_urls(urls: List[str]) -> List[Dict]:\n    \"\"\"Process multiple URLs concurrently\"\"\"\n    tasks = [fetch_data(url) for url in urls]\n    results = await asyncio.gather(*tasks)\n    return results",
                                  "capture": "function_definition"
                                }
                              ]
                              """)
    args_schema: type[BaseModel] = create_model(
        "FindFunctionDefinitionArgs",
        name=(str, Field(description="The name of the function to find.")),
        path=(
            Optional[str],
            Field(
                default=None, description="Restrict the search to a specific file. Useful for local symbols (optional)"
            ),
        ),
        language=(
            Optional[str],
            Field(
                default=None,
                description="Restrict the search to a specific language. If the project has multiple languages, you MUST specify the language. (optional)",
            ),
        ),
    )

    async def _run(self, **kwargs: Any) -> Any:
        name = kwargs["name"]
        path = kwargs.get("path")
        language = kwargs.get("language")

        language_registry = get_language_registry()
        if not language:
            if path:
                language = language_registry.language_for_file(path)
            else:
                # Use the first language in the project as the default
                language = get_most_common_language(self.project)
                print(f"Warning: Language not detected. Using {language} as the default.")

        tree_cache = get_tree_cache()

        # Typescript and JavaScript use function_declaration instead of function_definition
        function_token = "function_declaration" if language in ["typescript", "javascript"] else "function_definition"

        query = f"""
            ({function_token}
                name: (identifier) @func-name
                (#eq? @func-name "{name}")
            ) @function_definition
        """

        try:
            results = query_code(self.project, query, language_registry, tree_cache, path, language)
        except QueryError as e:
            raise ToolError(e) from e

        filtered_results = [r for r in results if r["capture"] == "function_definition"]

        # Tree sitter uses 0-based row indexing which is contrary to convention
        # Convert to 1-based indexing for the output
        for result in filtered_results:
            for key in ["start", "end"]:
                if "row" in result[key]:
                    result[key]["row"] += 1
        return filtered_results


class QueryCodeTool(TreeSitterBaseTool):
    name: str = "query_code"
    description: str = dedent("""
                              Evaluate a tree-sitter query against the codebase.

                              Use this tool to find functions, classes, variables, or security patterns across files.
                              More precise than text search, because it understands code structure and context.

                              Tree-sitter queries use S-expression syntax to match patterns in code.

                              Basic query syntax:
                              - `(node_type)` - Match nodes of a specific type
                              - `(node_type field: (child_type))` - Match nodes with specific field relationships
                              - `@name` - Capture a node with a name
                              - `#predicate` - Apply additional constraints

                              Example query for Python functions:
                              ```
                              (function_definition
                              name: (identifier) @function.name
                              parameters: (parameters) @function.params
                              body: (block) @function.body) @function.def
                              ```

                              Outputs matches with captured nodes and their locations in the code.
                              """)
    args_schema: type[BaseModel] = create_model(
        "QueryCodeArgs",
        query=(str, Field(description="The tree-sitter query to evaluate.")),
        path=(
            Optional[str],
            Field(
                default=None, description="Restrict the search to a specific file. Useful for local symbols (optional)"
            ),
        ),
        language=(
            Optional[str],
            Field(
                default=None,
                description="Restrict the search to a specific language. Useful in a project with multiple languages (optional)",
            ),
        ),
        max_results=(
            Optional[int],
            Field(default=100, description="The maximum number of results to return. (optional, default = 100)"),
        ),
    )

    async def _run(self, **kwargs: Any) -> Any:
        query = kwargs["query"]
        path = kwargs.get("path")
        language = kwargs.get("language")
        max_results = kwargs.get("max_results", 100)

        language_registry = get_language_registry()
        if not language:
            if path:
                language = language_registry.language_for_file(path)
            else:
                # Use the first language in the project as the default
                language = get_most_common_language(self.project)

        tree_cache = get_tree_cache()

        return query_code(self.project, query, language_registry, tree_cache, path, language, max_results)


class SearchTextTool(TreeSitterBaseTool):
    name: str = "search_text"
    description: str = dedent("""
                          Search for text patterns across the codebase using string matching.

                          Use this tool to find literal text occurrences like hardcoded values, API keys,
                          comments, or string literals. For code structure analysis, use query_code or
                          find_function_definition tools instead.

                          Features:
                          - Search for hardcoded values, comments, imports, TODOs, or error patterns
                          - Use literal strings or simple wildcards
                          - Case-sensitive by default
                          - Search project-wide or in specific files
                          - Returns file path, line number, match text, and context

                          Examples:
                          - pattern="TODO" → Find all TODO comments
                          - pattern="process.env" → Find environment variable usage
                          - pattern="password" → Find hardcoded passwords
                          - pattern="import axios", path="src/api.js" → Find axios imports
                          """)
    args_schema: type[BaseModel] = create_model(
        "SearchTextArgs",
        pattern=(str, Field(description="The text pattern to search for.")),
        path=(
            Optional[str],
            Field(
                default=None, description="Restrict the search to a specific file. Useful for local symbols (optional)"
            ),
        ),
    )

    async def _run(self, **kwargs: Any) -> Any:
        pattern = kwargs["pattern"]
        path = kwargs.get("path")

        """
        Run the search_text tool, mapping 'path' parameter to 'file_pattern'.
        """
        return search_text(self.project, pattern=pattern, file_pattern=path)


def get_most_common_language(project: Project) -> str:
    return max(project.languages.keys(), key=lambda x: project.languages[x])  # type: ignore[no-any-return]
