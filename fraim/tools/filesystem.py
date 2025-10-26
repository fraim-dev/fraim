# SPDX-License-Identifier: MIT
# Copyright (c) 2025 Resourcely Inc.

import inspect
from collections.abc import Callable, Iterator
from textwrap import dedent
from typing import Any, ClassVar, Optional, Self

from pydantic import BaseModel, Field, create_model

from fraim.core.tools import BaseTool, ToolError
from fraim.util.files.basepath import BasePathFS
from fraim.util.files.grep import grep
from fraim.util.files.list_dir import list_dir
from fraim.util.files.read_file import read_file


class FilesystemTools:
    """
    Direct interface to filesystem utilities for project exploration and file operations.

    This class provides fraim-compatible tools that use the filesystem utilities to:
    - Search text patterns across files with ripgrep
    - List directory contents recursively
    - Read file contents with optional line ranges

    The tools automatically use BasePathFS for path sandboxing and provide a clean
    interface for AI agents to explore file systems safely.
    """

    def __init__(self, project_path: str):
        self.project_path = project_path
        self.fs = BasePathFS(project_path)

        self.tools: list[BaseTool] = [
            GrepTool.create(self.fs),
            ListDirTool.create(self.fs),
            ReadFileTool.create(self.fs),
        ]

    def __iter__(self) -> Iterator[BaseTool]:
        return iter(self.tools)


class FilesystemBaseTool(BaseTool):
    """
    Base class for all filesystem tools.

    Automatically passes the BasePathFS to the tool function.
    """

    tool_func: ClassVar[Callable[..., Any] | None] = None
    fs: BasePathFS = Field(exclude=True)

    @classmethod
    def create(cls, fs: BasePathFS, **kwargs: Any) -> Self:
        """
        Create a new instance of the tool.

        Args:
            fs: The BasePathFS instance for sandboxed file operations.
        """
        # Create instance with fs stored in field
        instance = cls(fs=fs, **kwargs)
        return instance

    async def _run(self, **kwargs: Any) -> Any:
        """
        Run the tool, passing the fs to the tool function.
        """
        # Access tool_func from the class to avoid method binding
        tool_func = self.__class__.tool_func
        if tool_func is None:
            raise NotImplementedError("The `tool_func` attribute was not set.")

        try:
            # Check if the function is async or sync
            if inspect.iscoroutinefunction(tool_func):
                return await tool_func(self.fs, **kwargs)
            return tool_func(self.fs, **kwargs)
        except (FileNotFoundError, PermissionError, NotADirectoryError, IsADirectoryError, ValueError) as e:
            raise ToolError(str(e)) from e


class GrepTool(FilesystemBaseTool):
    name: str = "grep"
    tool_func = grep
    description: str = dedent("""A file searching tool based on ripgrep.

                              Usage:

                              - Supports full regex syntax (e.g., `class\\s+.*Error`)
                              - Filter the files searched using the glob parameter (e.g., `**/*.py`) or the type parameter (e.g., `py`)
                              - Supports multiple output modes:
                                 - `context` - show the matching lines
                                 - `files_with_matches` - show the file paths with matches
                                 - `count` - show the number of matches in each file
                              - By default patterns are matched against single lines. Use the multiline parameter to match across multiple lines.
                              """)
    args_schema: type[BaseModel] = create_model(
        "GrepArgs",
        pattern=(
            str,
            Field(description="The regular expression pattern to search for (maps to `rg --regexp PATTERN`)"),
        ),
        path=(str, Field(description="File or directory to search in. Use '.' for the root directory.")),
        head_limit=(
            Optional[int],
            Field(default=None, description="Limit output to first N lines/entries. (optional) (maps to `| head -N`)"),
        ),
        glob=(
            Optional[str],
            Field(
                default=None,
                description="Glob pattern to filter files (e.g. '*.js', '*.{ts,tsx}'). (optional) (maps to `rg --glob GLOB`)",
            ),
        ),
        output_mode=(
            Optional[str],
            Field(
                default="content",
                description="Output format: 'content' outputs matches with `-A/-B/-C` context and line numbers, 'files_with_matches' outputs file paths, or 'count' outputs the matching line count. (optional)",
            ),
        ),
        file_type=(
            Optional[str],
            Field(
                default=None,
                description="File type to search (e.g. 'js', 'py', 'rust'). (optional) (maps to `rg --type TYPE`)",
            ),
        ),
        context_before=(
            Optional[int],
            Field(
                default=None, description="Number of lines to show before each match. (optional) (maps to `rg -B N`)"
            ),
        ),
        context_after=(
            Optional[int],
            Field(default=None, description="Number of lines to show after each match. (optional) (maps to `rg -A N`)"),
        ),
        context_around=(
            Optional[int],
            Field(
                default=None,
                description="Number of lines to show before and after each match. (optional) (maps to `rg -C N`)",
            ),
        ),
        case_insensitive=(
            bool,
            Field(default=False, description="Enable case insensitive search. (optional) (maps to `rg -i`)"),
        ),
        multiline=(
            bool,
            Field(
                default=False,
                description="Enable multiline mode where . matches newlines. (optional) (maps to `rg -U --multiline-dotall`)",
            ),
        ),
    )

    def display_message(self, *args: Any, **kwargs: Any) -> str:
        return f"Grepping for {kwargs['pattern']} in {kwargs['path']}"


class ListDirTool(FilesystemBaseTool):
    name: str = "list_dir"
    tool_func = list_dir
    description: str = dedent("""
                              List directories.
                              

                              Use this tool to understand project structure, explore directory contents, find files by 
                              location, or verifythe existence of paths.
                              
                              Returns a hierarchical listing in breadth-first order with proper indentation and directory markers.
                              """)
    args_schema: type[BaseModel] = create_model(
        "ListDirArgs",
        target_path=(str, Field(description="Path to the directory to list. Use '.' for the root directory.")),
        ignore_globs=(
            Optional[list[str]],
            Field(
                default=[], description="List of glob patterns to ignore (e.g. ['*.log', 'node_modules']). (optional)"
            ),
        ),
        show_hidden=(
            bool,
            Field(default=False, description="Whether to show hidden files (starting with '.'). (optional)"),
        ),
    )

    def display_message(self, *args: Any, **kwargs: Any) -> str:
        return f"Listing {kwargs['target_path']}"


class ReadFileTool(FilesystemBaseTool):
    name: str = "read_file"
    tool_func = read_file
    description: str = dedent("""
                              Read file contents with optional line-based offset and limit.

                              Use this tool to examine file contents, either entirely or specific sections.
                              Supports line-based slicing for large files where you need specific ranges.

                              Returns file content as string, optionally limited by offset and limit.
                              """)
    args_schema: type[BaseModel] = create_model(
        "ReadFileArgs",
        target_path=(str, Field(description="Path to the file to read")),
        offset=(
            Optional[int],
            Field(
                default=None, description="Starting line number (1-based). If None, start from beginning. (optional)"
            ),
        ),
        limit=(
            Optional[int],
            Field(default=None, description="Maximum number of lines to read. If None, read all lines. (optional)"),
        ),
    )

    def display_message(self, *args: Any, **kwargs: Any) -> str:
        return f"Reading {kwargs['target_path']}"
