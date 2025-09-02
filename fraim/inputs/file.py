# SPDX-License-Identifier: MIT
# Copyright (c) 2025 Resourcely Inc.
from typing import ContextManager, Dict, Iterator, Protocol, runtime_checkable

from fraim.core.contextuals import CodeChunk

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

# SPDX-License-Identifier: MIT
# Copyright (c) 2025 Resourcely Inc.
from pathlib import Path


class BufferedFile(CodeChunk):
    def __init__(self, path: str, body: str):
        super().__init__(file_path=path, content=body, line_number_start_inclusive=1, line_number_end_inclusive=len(body))
        self.path = path
        self.body = body

    @property
    def language(self) -> str | None:
        return LANGUAGE_EXTENSIONS.get(str(Path(self.path).suffix), None)

    def __str__(self) -> str:
        return f'<file path="{self.file_path}">\n{self.content}\n</file>'

# @runtime_checkable
# class Files(Protocol, ContextManager):
#     def __iter__(self) -> Iterator[BufferedFile]: ...
#
#     # The absolute file path that these files are relative to.
#     def root_path(self) -> str: ...
