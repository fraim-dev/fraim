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
    def __init__(
        self,
        config: Config,
        root_path: Path,
        paths: Optional[list[str]] = None,
        globs: Optional[List[str]] = None,
        exclude_globs: Optional[List[str]] = None,
        limit: Optional[int] = None,
    ):
        self.config = config
        self.root_path = root_path

        if paths:
            self.paths = [self.root_path / p for p in paths]
        else:
            self.paths = [self.root_path]

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
        self.exclude_globs = exclude_globs if exclude_globs else ["*.min.js", "*.min.css"]
        self.limit = limit

    def root_path(self) -> str:
        return self.path

    def __iter__(self) -> Iterator[CodeChunk]:
        self.config.logger.info(f"Scanning local files: {self.path}, with globs: {self.globs}")

    def _files(self) -> Iterator[Input]:
        seen = set()
        for subpath in self.paths:
            self.config.logger.info(
                f"Scanning local files: {subpath}, with globs: {self.globs}, exclude globs: {self.exclude_globs}"
            )
            for glob_pattern in self.globs:
                if subpath.is_file():
                    paths = [subpath]
                else:
                    paths = subpath.rglob(glob_pattern)

                for path in paths:
                    if any(path.match(exclude) for exclude in self.exclude_globs):
                        self.config.logger.debug(f"Skipping excluded file: {path}")
                        yield Input(path.relative_to(self.root_path), path.read_text(encoding="utf-8"))
                    else:
                        # Skip file if not a file
                        if not path.is_file():
                            continue

                        if any(path.match(exclude) for exclude in self.exclude_globs):
                            self.config.logger.debug(f"Skipping excluded file: {path}")
                            continue

                        # Skip file if already seen
                        if path in seen:
                            continue
                        try:
                            self.config.logger.info(f"Reading file: {path}")
                            # TODO: Avoid reading files that are too large?
                            file = BufferedFile(
                                os.path.relpath(path, self.config.project_path), path.read_text(encoding="utf-8")
                            )

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
