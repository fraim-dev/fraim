# SPDX-License-Identifier: MIT
# Copyright (c) 2025 Resourcely Inc.
import logging
import os.path
from collections.abc import Iterator
from pathlib import Path
from types import TracebackType
from typing import Self

import pathspec

from fraim.core.contextuals import CodeChunk
from fraim.inputs.chunks import chunk_input
from fraim.inputs.file import BufferedFile
from fraim.inputs.input import Input

logger = logging.getLogger(__name__)


class Local(Input):
    def __init__(self, path: str, globs: list[str] | None = None, limit: int | None = None):
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
        logger.info(f"Scanning local files: {self.path}, with globs: {self.globs}")

        # Load .gitignore patterns if present
        gitignore_spec = None
        gitignore_file = Path(self.path) / ".gitignore"
        if gitignore_file.exists():
            with gitignore_file.open() as f:
                gitignore_spec = pathspec.PathSpec.from_lines("gitwildmatch", f)

        seen = set()
        for glob_pattern in self.globs:
            for path in Path(self.path).rglob(glob_pattern):
                # Skip file if not a file
                if not path.is_file():
                    continue
                # Skip file if already seen
                if path in seen:
                    continue
                # Skip git-ignored file
                # TODO: skipping here still requires the `rglob` step to iterate every file. Replace with a
                #       custom walk function that can skip entire branches.
                if gitignore_spec and gitignore_spec.match_file(path.relative_to(self.path).as_posix()):
                    continue
                try:
                    logger.info(f"Reading file: {path}")
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
                        logger.warning(f"Skipping file with encoding issues: {path}")
                        continue
                    logger.error(f"Error reading file: {path} - {e}")
                    raise e

    def __enter__(self) -> Self:
        return self

    def __exit__(
        self, exc_type: type[BaseException] | None, exc_val: BaseException | None, exc_tb: TracebackType | None
    ) -> None:
        pass
