# SPDX-License-Identifier: MIT
# Copyright (c) 2025 Resourcely Inc.
import dataclasses
from pathlib import Path
from typing import Collection, Literal, AbstractSet, Set

import tiktoken

from fraim.core.contextuals.contextual import Contextual, Location, Locations

LANGUAGE_EXTENSIONS: dict[str, str] = {
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


# TODO: Consider CodeDiff, other types of Contextuals
class CodeChunk(Contextual[str]):
    """Concrete implementation of Contextual for code snippets"""

    def __init__(self, file_path: str, content: str, line_number_start_inclusive: int, line_number_end_inclusive: int):
        self.content = content
        self.file_path = file_path
        self.line_number_start_inclusive = line_number_start_inclusive
        self.line_number_end_inclusive = line_number_end_inclusive

    @property
    def description(self) -> str:
        return f"Code chunk from {self.file_path}:{self.line_number_start_inclusive}-{self.line_number_end_inclusive}"

    @description.setter
    def description(self, _: str) -> None:
        raise AttributeError("description is read-only")

    @property
    def locations(self) -> Locations:
        return Locations(
            Location(
                file_path=self.file_path,
                line_number_start_inclusive=self.line_number_start_inclusive,
                line_number_end_inclusive=self.line_number_end_inclusive,
            ),
        )

    @property
    def language(self) -> str | None:
        suffix = Path(self.file_path).suffix
        if not suffix:
            return None

        sanitized = suffix.lstrip(".").lower()
        if not sanitized:
            return None

        return LANGUAGE_EXTENSIONS.get(sanitized, None)

    def __str__(self) -> str:
        return f'<code_chunk file_path="{self.file_path}" line_number_start_inclusive="{self.line_number_start_inclusive}" line_number_end_inclusive="{self.line_number_end_inclusive}">\n{self.content}\n</code_chunk>'

    def __repr__(self) -> str:
        return str(self)

    def __len__(self) -> int:
        """Return the length of the combined content of all code chunks in tokens."""

        # Let's just use gpt2 encoding for now, we could get the actual model name, but I worry that this will break
        # things randomly, and really we only care if the size is approximately correct. Being consistent is more important.
        enc = tiktoken.get_encoding("gpt2")

        return len(
            enc.encode(
                str(self.content),
                allowed_special=set(),
                disallowed_special="all",
            ),
        )


class CodeChunks(list[CodeChunk], Contextual[str]):
    def __init__(self, all_files: list[CodeChunk] | None = None):
        all_files = all_files or []
        super().__init__(all_files)

    @property
    def file_paths(self) -> list[str]:
        return list(set([c.file_path for c in self]))

    @property
    def content(self) -> str:  # type: ignore[override]
        return "\n\n".join([c.content for c in self])

    @property
    def description(self) -> str:  # type: ignore[override]
        return f"Code chunks from: {self.file_paths}"

    @property
    def locations(self) -> Locations:
        locations: list[Location] = []
        for chunk in self:
            locations = locations + chunk.locations
        return Locations(*locations)

    def __str__(self) -> str:
        return f"<code_chunks>{'\n'.join(str(chunk) for chunk in self)}</code_chunks>"

    def __repr__(self) -> str:
        return str(self)

    def __len__(self) -> int:
        """Return the length of the combined content of all code chunks in tokens."""
        return sum(len(chunk) for chunk in self)



@dataclasses.dataclass
class CodeChunkFailure:
    """Used to represent a failure to process a code chunk."""

    chunk: Contextual[str]
    """The code chunk that failed to be processed."""

    reason: str
    """The reason why the failure occurred."""
