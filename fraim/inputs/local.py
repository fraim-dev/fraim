# SPDX-License-Identifier: MIT
# Copyright (c) 2025 Resourcely Inc.
import logging
import os.path
from collections.abc import Iterator
from pathlib import Path
from types import TracebackType
from typing import Self

from fraim.core.contextuals import CodeChunk
from fraim.inputs.chunks import chunk_input
from fraim.inputs.file import BufferedFile
from fraim.inputs.input import Input


class Local(Input):
    def __init__(self, logger: logging.Logger, path: str, globs: list[str] | None = None, limit: int | None = None):
        self.path = path
        self.logger = logger
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
        self.logger.info(f"Scanning local files: {self.path}, with globs: {self.globs}")

        seen = set()
        for glob_pattern in self.globs:
            for path in Path(self.path).rglob(glob_pattern):
                # Skip file if not a file
                if not path.is_file():
                    continue
                # Skip file if already seen
                if path in seen:
                    continue
                try:
                    self.logger.info(f"Reading file: {path}")
                    # TODO: Avoid reading files that are too large?
                    file = BufferedFile(os.path.relpath(path, self.root_path()), path.read_text(encoding="utf-8"))

                    # TODO: configure file chunking in the config
                    for chunk in chunk_input(file, 100):
                        yield chunk

                    # Add file to set of seen files, exit early if maximum reached.
                    seen.add(path)
                    if self.limit is not None and len(seen) == self.limit:
                        return

                except Exception as e:
                    if isinstance(e, UnicodeDecodeError):
                        self.logger.warning(f"Skipping file with encoding issues: {path}")
                        continue
                    self.logger.error(f"Error reading file: {path} - {e}")
                    raise e

    def __enter__(self) -> Self:
        return self

    def __exit__(
        self, exc_type: type[BaseException] | None, exc_val: BaseException | None, exc_tb: TracebackType | None
    ) -> None:
        pass
