# SPDX-License-Identifier: MIT
# Copyright (c) 2025 Resourcely Inc.
from typing import ContextManager, Iterator, Protocol, runtime_checkable, Dict

LANGUAGE_EXTENSIONS: Dict[str, str] = {
    "py": "python",
    "c": "c",
    "h": "c",
    "cpp": "cpp",
    "go": "go",
    "ts": "ts",
    "js": "js",
    "java": "java",
    "rb": "ruby",
    "php": "php",
    "rs": "rust",
    "kt": "kotlin",
    "scala": "scala",
    "tsx": "ts",

    # Not supported by langchain: *.jsx, *.swift
    # Not supported by fraim:
    "cobol": "cobol",
    "cs": "csharp",
    "lua": "lua",
    "pl": "perl",
    "ex": "elixir",
    "exs": "elixir",
    "sql": "sql",
}

import mcp_server_tree_sitter

# SPDX-License-Identifier: MIT
# Copyright (c) 2025 Resourcely Inc.

from pathlib import Path


class File:
    def __init__(self, path: str, body: str):
        self.path = path
        self.body = body

    @property
    def language(self) -> str | None:
        return LANGUAGE_EXTENSIONS.get(str(Path(self.path).suffix), None)


@runtime_checkable
class Files(Protocol, ContextManager):
    def __iter__(self) -> Iterator[File]: ...

    # The absolute file path that these files are relative to.
    def root_path(self) -> str: ...
