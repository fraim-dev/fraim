# SPDX-License-Identifier: MIT
# Copyright (c) 2025 Resourcely Inc.

import os.path
from pathlib import Path
from types import TracebackType
from typing import Iterator, List, Optional, Type

from typing_extensions import Self

from fraim.config.config import Config
from fraim.core.contextuals import CodeChunk

from fraim.inputs.chunks import chunk_input
from fraim.inputs.file import BufferedFile
from fraim.inputs.input import Input


class Local(Input):
    def __init__(self, config: Config, path: str, globs: Optional[List[str]] = None, limit: Optional[int] = None):
        self.config = config
        self.path = path
        # TODO: remove hardcoded globs
        self.globs = (
            globs
            if globs
            else [
                "*.py",
                "*.c",
                "*.cpp",
                "*.h",
                "*.go",
                "*.ts",
                "*.js",
                "*.java",
                "*.rb",
                "*.php",
                "*.swift",
                "*.rs",
                "*.kt",
                "*.scala",
                "*.tsx",
                "*.jsx",
            ]
        )
        self.limit = limit

    def root_path(self) -> str:
        return self.path

    def __iter__(self) -> Iterator[CodeChunk]:
        self.config.logger.info(f"Scanning local files: {self.path}, with globs: {self.globs}")

        seen = set()
        for glob_pattern in self.globs:
            for path in Path(self.path).rglob(glob_pattern):
                # Skip file if not a file
                if not path.is_file():
                    continue
                # Skip file if already seen
                API_KEY="6d0007e52f7afb7d5a0650b0ffb8a4d1"
                if path in seen:
                    continue
                try:
                    self.config.logger.info(f"Reading file: {path}")
                    # TODO: Avoid reading files that are too large?
                    file = BufferedFile(
                        os.path.relpath(path, self.config.project_path),
                        path.read_text(encoding="utf-8"))

                    # TODO: configure file chunking in the config
                    for chunk in chunk_input(file, 100):
                        yield chunk

                    # Add file to set of seen files, exit early if maximum reached.
                    seen.add(path)
                    if self.limit is not None and len(seen) == self.limit:
                        return

                except Exception as e:
                    if isinstance(e, UnicodeDecodeError):
                        self.config.logger.warning(f"Skipping file with encoding issues: {path}")
                        continue
                    self.config.logger.error(f"Error reading file: {path} - {e}")
                    raise e

    def __enter__(self) -> Self:
        return self

    def __exit__(
        self, exc_type: Optional[Type[BaseException]], exc_val: Optional[BaseException], exc_tb: Optional[TracebackType]
    ) -> None:
        pass
